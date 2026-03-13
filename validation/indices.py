"""
Cálculo de índices estruturais e flags de validação
Índices principais: A/V (kg/m³), A/C (kg/m²), V/C (m³/m²), C/Area (m²/m²)
"""
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
from supabase import Client

# Artigos de aço com regra 7.X.{12,14,16} - sempre zero, ignorar no cálculo
ARTIGOS_ACO_ZERO = {'12', '14', '16'}  # elemento_sufixo a ignorar no cap 7

# Elementos de laje para cálculo conjunto de A/V
ELEMENTOS_LAJE_CONJUNTO = {'LAJE_MACICA', 'BANDA', 'CAPITEL'}


def _filtrar_artigos_aco(artigos):
    """
    Filtra artigos de aço, removendo aqueles com regra 7.X.{12,14,16} que são sempre zero.
    
    Args:
        artigos: lista de artigos
        
    Returns:
        lista filtrada excluindo artigos de aço inválidos
    """
    return [
        a for a in artigos
        if not (a.get('capitulo') == '7' and a.get('elemento_sufixo') in ARTIGOS_ACO_ZERO)
    ]


def _calc_av_lajes_conjunto(artigos_betao, artigos_aco):
    """
    Calcula A/V para Lajes+Bandas+Capitéis com denominador conjunto.
    
    Args:
        artigos_betao: artigos do capítulo 5 (betão)
        artigos_aco: artigos do capítulo 7 (aço)
        
    Returns:
        A/V em kg/m³ ou None se denominador zero
    """
    # Agrupar aço de lajes (cap 7, sufixo 11)
    kg = sum(
        a.get('quant_total', 0) or 0
        for a in artigos_aco
        if a.get('capitulo') == '7' and a.get('elemento_sufixo') == '11'
    )
    # Agrupar betão de lajes (elementos no conjunto)
    m3 = sum(
        a.get('quant_total', 0) or 0
        for a in artigos_betao
        if a.get('elemento_tipo') in ELEMENTOS_LAJE_CONJUNTO
    )
    return round(kg / m3, 1) if m3 > 0 else None


def calcular_indices(snapshot_id: str, supabase_client: Client) -> list[dict]:
    """
    Calcula índices estruturais por elemento_tipo para um snapshot MQT
    
    Args:
        snapshot_id: UUID do snapshot na tabela mqt_snapshots
        supabase_client: cliente Supabase autenticado
        
    Returns:
        Lista de dicts com índices por elemento_tipo:
        - elemento_tipo, betao_m3, cofragem_m2, aco_kg, av, ac, vc, flag
    """
    print(f"\n{'='*70}")
    print(f"CÁLCULO DE ÍNDICES ESTRUTURAIS")
    print(f"{'='*70}\n")
    print(f"📊 Snapshot ID: {snapshot_id}\n")
    
    # 1. Ler snapshot para obter area_construcao
    print("📖 A ler snapshot...")
    snapshot_result = supabase_client.table('mqt_snapshots') \
        .select('area_construcao') \
        .eq('id', snapshot_id) \
        .single() \
        .execute()
    
    snapshot = snapshot_result.data if snapshot_result.data else {}
    area_construcao = snapshot.get('area_construcao')
    print(f"✅ Área de construção: {area_construcao} m²" if area_construcao else "⚠️  Área não definida\n")
    
    # 2. Ler todos os artigos do snapshot
    print("📖 A ler artigos do snapshot...")
    result = supabase_client.table('mqt_artigos') \
        .select('*') \
        .eq('snapshot_id', snapshot_id) \
        .execute()
    
    if not result.data:
        print("⚠️  Nenhum artigo encontrado para este snapshot")
        return []
    
    artigos = result.data
    print(f"✅ {len(artigos)} artigos carregados\n")
    
    # 3. Filtrar artigos de aço inválidos (7.X.{12,14,16})
    artigos_filtrados = _filtrar_artigos_aco(artigos)
    if len(artigos_filtrados) < len(artigos):
        print(f"ℹ  {len(artigos) - len(artigos_filtrados)} artigos de aço filtrados (regra 7.X.{{12,14,16}})\n")
    artigos = artigos_filtrados
    
    # 4. Agrupar por elemento_tipo e agregar quantidades
    print("📐 A agregar quantidades por elemento_tipo e capítulo...")
    
    # Estrutura: { elemento_tipo: { 'betao': valor, 'cofragem': valor, 'aco': valor } }
    agregados = defaultdict(lambda: {'betao_m3': 0.0, 'cofragem_m2': 0.0, 'aco_kg': 0.0})
    
    for artigo in artigos:
        elemento_tipo = artigo.get('elemento_tipo')
        capitulo = artigo.get('capitulo', '')
        nivel = artigo.get('nivel', 3)

        # Ignorar caps/subcaps-título (sem elemento_tipo ou nivel < 3 sem unidade)
        if elemento_tipo is None or elemento_tipo == '':
            continue
        
        # Calcular quant_total se não existir (soma de A+B+C)
        quant_total = artigo.get('quant_total')
        if quant_total is None:
            quant_a = artigo.get('quant_a', 0.0) or 0.0
            quant_b = artigo.get('quant_b', 0.0) or 0.0
            quant_c = artigo.get('quant_c', 0.0) or 0.0
            quant_total = quant_a + quant_b + quant_c
        else:
            quant_total = quant_total or 0.0
        
        # Agregar por tipo de capítulo
        if capitulo == '5':  # Betão
            agregados[elemento_tipo]['betao_m3'] += quant_total
        elif capitulo == '6':  # Cofragem
            agregados[elemento_tipo]['cofragem_m2'] += quant_total
        elif capitulo in ['7', '8']:  # Aço ordinário (7) + pré-esforço (8)
            agregados[elemento_tipo]['aco_kg'] += quant_total
    
    print(f"✅ {len(agregados)} elementos processados\n")
    
    # 3. Calcular índices para cada elemento_tipo
    print("🔢 A calcular índices...\n")
    
    resultados = []
    indices_db = []
    
    for elemento_tipo, qtys in sorted(agregados.items()):
        betao = qtys['betao_m3']
        cofragem = qtys['cofragem_m2']
        aco = qtys['aco_kg']
        
        # Calcular índices (só se denominador > 0, senão None)
        av = (aco / betao) if betao > 0 else None  # kg/m³ (aço/volume)
        ac = (aco / cofragem) if cofragem > 0 else None  # kg/m² (aço/cofragem)
        vc = (betao / cofragem) if cofragem > 0 else None  # m³/m² (volume/cofragem)
        
        # Atribuir flag (por defeito 'ok' - flags manuais por agora)
        flag = 'ok'
        
        # Resultado para retorno
        resultado = {
            'elemento_tipo': elemento_tipo,
            'betao_m3': betao,
            'cofragem_m2': cofragem,
            'aco_kg': aco,
            'av': av,
            'ac': ac,
            'vc': vc,
            'flag': flag
        }
        resultados.append(resultado)
        
        # Preparar para inserção na DB
        indice_db = {
            'snapshot_id': snapshot_id,
            'elemento_tipo': elemento_tipo,
            'betao_m3': betao,
            'aco_kg': aco,
            'cofragem_m2': cofragem,
            'av': av,
            'ac': ac,
            'vc': vc,
            'flag': flag,
            'calculado_em': datetime.utcnow().isoformat()
        }
        indices_db.append(indice_db)
        
        # Print linha da tabela
        print(f"{elemento_tipo:20s} | "
              f"betão={betao:8.1f} m³ | "
              f"aço={aco:9.1f} kg | "
              f"A/V={av or 0:6.1f} kg/m³ | "
              f"cofr={cofragem:8.1f} m² | "
              f"V/C={vc or 0:5.2f}")
    
    # Cálculo especial: A/V para Lajes+Bandas+Capitéis com denominador conjunto
    print(f"\n📊 A calcular A/V conjunto para Lajes+Bandas+Capitéis...")
    artigos_betao = [a for a in artigos if a.get('capitulo') == '5']
    artigos_aco = [a for a in artigos if a.get('capitulo') == '7']
    av_lajes_conjunto = _calc_av_lajes_conjunto(artigos_betao, artigos_aco)
    
    if av_lajes_conjunto is not None:
        print(f"✅ A/V Lajes+Bandas+Capitéis = {av_lajes_conjunto} kg/m³\n")
        # Atualizar índices para elementos do conjunto
        for resultado in resultados:
            if resultado['elemento_tipo'] in ELEMENTOS_LAJE_CONJUNTO:
                resultado['av'] = av_lajes_conjunto
        for indice_db in indices_db:
            if indice_db['elemento_tipo'] in ELEMENTOS_LAJE_CONJUNTO:
                indice_db['av'] = av_lajes_conjunto
    
    # Cálculo de índices globais
    print("📊 A calcular índices globais...")
    total_cofragem = sum(qtys['cofragem_m2'] for qtys in agregados.values())
    
    if area_construcao and area_construcao > 0:
        c_area = round(total_cofragem / area_construcao, 3)
        print(f"✅ C/Area = {c_area} m²/m² (cofragem total={total_cofragem:.1f} m², área={area_construcao:.1f} m²)\n")
    else:
        c_area = None
        print(f"⚠️  C/Area não calculado (área de construção não disponível)\n")
    
    # 4. Inserir resultados em mqt_indices
    print(f"\n💾 A inserir {len(indices_db)} índices em mqt_indices...")
    
    try:
        result = supabase_client.table('mqt_indices').insert(indices_db).execute()
        print(f"✅ {len(result.data)} índices inseridos\n")
    except Exception as e:
        print(f"❌ Erro ao inserir índices: {e}\n")
        # Não falhar - retornar resultados mesmo se inserção falhar
    
    print(f"{'='*70}")
    print(f"✅ CÁLCULO DE ÍNDICES COMPLETO")
    print(f"{'='*70}\n")
    
    return resultados


def gerar_flags_validacao(indice_aco_betao: float, 
                         indice_cofragem_betao: float) -> List[str]:
    """
    Gera flags de alerta baseadas em valores de referência
    
    Args:
        indice_aco_betao: kg/m³
        indice_cofragem_betao: m²/m³
        
    Returns:
        Lista de strings com flags (ex: ["ACO_ELEVADO", "COFRAGEM_BAIXA"])
    """
    flags = []
    
    # Valores de referência JSJ (aproximados)
    # TODO: Ajustar com base em KB-05_Indices_Referencia.md
    ACO_MIN = 80  # kg/m³
    ACO_MAX = 150  # kg/m³
    COFRAGEM_MIN = 4.5  # m²/m³
    COFRAGEM_MAX = 7.0  # m²/m³
    
    # Aço
    if indice_aco_betao < ACO_MIN:
        flags.append("ACO_BAIXO")
    elif indice_aco_betao > ACO_MAX:
        flags.append("ACO_ELEVADO")
    
    # Cofragem
    if indice_cofragem_betao < COFRAGEM_MIN:
        flags.append("COFRAGEM_BAIXA")
    elif indice_cofragem_betao > COFRAGEM_MAX:
        flags.append("COFRAGEM_ELEVADA")
    
    # Relação aço/cofragem
    # Estruturas com muito aço geralmente têm cofragem complexa
    if indice_aco_betao > ACO_MAX and indice_cofragem_betao < COFRAGEM_MIN:
        flags.append("INCOERENCIA_ACO_COFRAGEM")
    
    return flags


def calcular_indices_por_elemento(snapshot_id: str, client: Client) -> List[Dict]:
    """
    Calcula índices detalhados por elemento_tipo
    
    Args:
        snapshot_id: ID do snapshot
        client: cliente Supabase
        
    Returns:
        Lista de dicts com índices por elemento:
        - elemento_tipo
        - vol_betao
        - peso_aco
        - area_cofragem
        - indice_aco
        - indice_cofragem
    """
    # TODO: Implementar análise detalhada
    # Útil para identificar elementos com índices anómalos
    # Ex: pilares com aço muito elevado, lajes com cofragem baixa, etc.
    
    return []


def validar_consistencia_artigos(snapshot_id: str, client: Client) -> bool:
    """
    Valida consistência entre artigos de betão, cofragem e aço
    
    Regras de validação:
    - Cada elemento de betão deve ter cofragem correspondente
    - Cada elemento de betão deve ter aço correspondente
    - Volumes devem ser coerentes (ex: cofragem de PILAR com betão de PILAR)
    
    Args:
        snapshot_id: ID do snapshot
        client: cliente Supabase
        
    Returns:
        True se consistente, False com warnings caso contrário
    """
    # TODO: Implementar validações cruzadas
    # Esta função é importante para detetar erros de input no Excel
    
    return True
