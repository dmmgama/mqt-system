"""
Cálculo de índices estruturais e flags de validação
Índices principais: kg/m³ (betão+aço), m²/m³ (cofragem)
"""
from typing import Dict, List, Optional
from supabase import Client


def calcular_indices_snapshot(snapshot_id: str, client: Client) -> Dict:
    """
    Calcula índices estruturais para um snapshot MQT completo
    
    Args:
        snapshot_id: ID do snapshot na tabela mqt_snapshots
        client: cliente Supabase
        
    Returns:
        Dict com índices calculados:
        - vol_betao_total: volume total de betão (m³)
        - peso_aco_total: peso total de aço (kg)
        - area_cofragem_total: área total de cofragem (m²)
        - indice_aco_betao: kg aço / m³ betão
        - indice_cofragem_betao: m² cofragem / m³ betão
        - flags: lista de flags de alerta
    """
    print(f"📐 A calcular índices para snapshot {snapshot_id}...")
    
    # 1. Obter todos os artigos deste snapshot
    artigos = client.table("mqt_artigos").select("*").eq(
        "snapshot_id", snapshot_id
    ).execute()
    
    if not artigos.data:
        print("⚠️  Nenhum artigo encontrado para este snapshot")
        return None
    
    # 2. Somar quantidades por tipo
    vol_betao_total = 0.0
    peso_aco_total = 0.0
    area_cofragem_total = 0.0
    
    for artigo in artigos.data:
        # TODO: Implementar lógica de soma baseada em capitulo_map
        # Se capitulo = 5 → betao (m³)
        # Se capitulo = 6 → cofragem (m²)
        # Se capitulo = 7,8 → aço (kg)
        pass
    
    # 3. Calcular índices
    indice_aco_betao = peso_aco_total / vol_betao_total if vol_betao_total > 0 else 0
    indice_cofragem_betao = area_cofragem_total / vol_betao_total if vol_betao_total > 0 else 0
    
    # 4. Gerar flags de alerta
    flags = gerar_flags_validacao(indice_aco_betao, indice_cofragem_betao)
    
    # 5. Inserir na tabela mqt_indices
    indices_data = {
        "snapshot_id": snapshot_id,
        "vol_betao_total": vol_betao_total,
        "peso_aco_total": peso_aco_total,
        "area_cofragem_total": area_cofragem_total,
        "indice_aco_betao": indice_aco_betao,
        "indice_cofragem_betao": indice_cofragem_betao,
        "flags": flags
    }
    
    try:
        result = client.table("mqt_indices").insert(indices_data).execute()
        print(f"✅ Índices calculados e guardados")
        return indices_data
    except Exception as e:
        print(f"❌ Erro ao guardar índices: {e}")
        return None


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
