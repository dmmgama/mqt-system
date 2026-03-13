"""
Mapeamento de códigos de artigo para elemento_tipo
Implementa a lógica (capitulo, sufixo) → elemento_tipo
"""
from typing import Optional, Dict
from supabase import Client


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
