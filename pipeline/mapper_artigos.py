"""
Mapeamento de códigos de artigo para elemento_tipo
Implementa a lógica (capitulo, sufixo) → elemento_tipo
"""
from typing import Optional, Dict
from supabase import Client


def map_artigos(artigos: list[dict], supabase_client: Client) -> list[dict]:
    """
    Mapeia artigos MQT para elemento_tipo usando a tabela elemento_map do Supabase
    
    Args:
        artigos: lista de dicts retornada por parse_mqt()
        supabase_client: cliente Supabase autenticado
        
    Returns:
        lista de artigos com campo elemento_tipo adicionado
    """
    # Carregar elemento_map do Supabase UMA vez
    try:
        result = supabase_client.table("elemento_map") \
            .select("capitulo, sufixo, elemento_tipo") \
            .is_("projeto_id", "null") \
            .execute()
        
        if not result.data:
            print("⚠️  Tabela elemento_map está vazia ou não acessível")
            # Retornar artigos com OUTRO para todos
            for artigo in artigos:
                artigo['elemento_tipo'] = 'OUTRO'
            return artigos
            
    except Exception as e:
        print(f"❌ Erro ao carregar elemento_map: {e}")
        # Retornar artigos com OUTRO para todos
        for artigo in artigos:
            artigo['elemento_tipo'] = 'OUTRO'
        return artigos
    
    # Construir dict de lookup em memória: (capitulo, sufixo) → elemento_tipo
    lookup = {}
    for row in result.data:
        key = (row['capitulo'], row['sufixo'])
        lookup[key] = row['elemento_tipo']
    
    print(f"✅ Carregados {len(lookup)} mapeamentos de elemento_map")
    
    # Para cada artigo, fazer lookup e adicionar elemento_tipo
    for artigo in artigos:
        capitulo = artigo.get('capitulo')
        sufixo = artigo.get('sufixo')
        artigo_cod = artigo.get('artigo_cod', 'N/A')
        
        # Lookup por (capitulo, sufixo)
        key = (capitulo, sufixo)
        elemento_tipo = lookup.get(key)
        
        if elemento_tipo:
            artigo['elemento_tipo'] = elemento_tipo
        else:
            artigo['elemento_tipo'] = 'OUTRO'
            print(f"⚠️  Sem mapeamento: {artigo_cod} | cap={capitulo} suf={sufixo}")
    
    return artigos


def map_artigo_to_elemento(artigo_cod: str, capitulo: int, sufixo: str, 
                          client: Client) -> Optional[str]:
    """
    Mapeia um artigo MQT para o elemento_tipo correspondente
    
    Args:
        artigo_cod: código completo do artigo (para logging)
        capitulo: capítulo do artigo (1º segmento)
        sufixo: sufixo do artigo (segmentos após subcapitulo)
        client: cliente Supabase para consultar elemento_map
        
    Returns:
        elemento_tipo (ex: "PILAR", "VIGA", "LAJE_MACICA") ou None se não encontrado
    """
    # Consultar a tabela elemento_map
    try:
        result = client.table("elemento_map").select("elemento_tipo").eq(
            "capitulo", capitulo
        ).eq(
            "sufixo", sufixo
        ).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]["elemento_tipo"]
        else:
            print(f"⚠️  Mapeamento não encontrado: capitulo={capitulo}, sufixo={sufixo} (artigo {artigo_cod})")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao consultar elemento_map: {e}")
        return None


def get_capitulo_info(capitulo: int, client: Client) -> Optional[Dict]:
    """
    Obtém informação sobre um capítulo da tabela capitulo_map
    
    Args:
        capitulo: número do capítulo
        client: cliente Supabase
        
    Returns:
        Dict com tipo, unidade, descricao ou None se não encontrado
    """
    try:
        result = client.table("capitulo_map").select("*").eq(
            "capitulo", capitulo
        ).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            print(f"⚠️  Capítulo não encontrado: {capitulo}")
            return None
            
    except Exception as e:
        print(f"❌ Erro ao consultar capitulo_map: {e}")
        return None


# Lista de elemento_tipo válidos (para validação)
ELEMENTO_TIPOS_VALIDOS = [
    "FUNDACAO", "MACIÇO_ESTACAS", "LAJE_FUNDO", "VIGA_FUND",
    "PILAR", "NUCLEO", "PAREDE", "PAREDE_PISC", "PAREDE_RES",
    "CONTENCAO", "VIGA", "LAJE_MACICA", "LAJE_ALIG", "RAMPA",
    "LAJE_PISC", "BANDA", "CAPITEL", "MURETE", "ESCADA",
    "MASSAME", "MACIÇO", "FUND_INDIRETA", "PRE_ESFORCO",
    "MOLDE_ALIG", "OUTRO"
]


def validate_elemento_tipo(elemento_tipo: str) -> bool:
    """
    Valida se um elemento_tipo é válido
    
    Args:
        elemento_tipo: string a validar
        
    Returns:
        True se válido, False caso contrário
    """
    return elemento_tipo in ELEMENTO_TIPOS_VALIDOS
