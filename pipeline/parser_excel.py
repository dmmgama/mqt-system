"""
Parser de ficheiros Excel MQT
Lê e normaliza o formato Excel JSJ para um DataFrame pandas
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional


def parse_mqt_excel(excel_path: str) -> pd.DataFrame:
    """
    Faz parse de um ficheiro Excel MQT JSJ
    
    Args:
        excel_path: Caminho completo para o ficheiro Excel
        
    Returns:
        DataFrame com as colunas:
        - artigo_cod: código do artigo (ex: "5.5.4", "6.2.4.1")
        - descricao: descrição textual do artigo
        - unidade: unidade de medida
        - quant_a: quantidade fundações
        - quant_b: quantidade térreo
        - quant_c: quantidade elevados
        - quant_total: soma a+b+c
    """
    # TODO: Implementar lógica de parsing
    # O Excel MQT tem um formato específico:
    # - Cabeçalho está numa linha específica
    # - Artigos estão organizados por capítulo
    # - Algumas linhas são separadores ou subtotais (ignorar)
    
    print(f"📖 A ler ficheiro: {excel_path}")
    
    # Placeholder de implementação
    # df = pd.read_excel(excel_path, sheet_name=0)
    # ... processamento ...
    
    # Exemplo de estrutura esperada do retorno:
    data = {
        'artigo_cod': [],
        'descricao': [],
        'unidade': [],
        'quant_a': [],
        'quant_b': [],
        'quant_c': [],
        'quant_total': []
    }
    
    df = pd.DataFrame(data)
    
    print(f"   ✓ {len(df)} artigos parseados")
    
    return df


def extract_capitulo_info(artigo_cod: str) -> Dict[str, any]:
    """
    Extrai informação do código de artigo
    
    Args:
        artigo_cod: código do artigo (ex: "5.5.4", "6.2.4.1", "7.1.1.2")
        
    Returns:
        Dict com:
        - capitulo: 1º segmento (ex: 5, 6, 7)
        - subcapitulo: 1º + 2º segmento (ex: "5.5", "6.2", "7.1")
        - sufixo: restantes segmentos (ex: "4", "4.1", "1.2")
    """
    partes = artigo_cod.split('.')
    
    if len(partes) < 3:
        return {
            'capitulo': None,
            'subcapitulo': None,
            'sufixo': None
        }
    
    capitulo = int(partes[0])
    subcapitulo = f"{partes[0]}.{partes[1]}"
    sufixo = '.'.join(partes[2:])
    
    return {
        'capitulo': capitulo,
        'subcapitulo': subcapitulo,
        'sufixo': sufixo
    }


def validate_artigo_structure(df: pd.DataFrame) -> bool:
    """
    Valida se o DataFrame tem a estrutura esperada
    
    Args:
        df: DataFrame com artigos parseados
        
    Returns:
        True se válido, False caso contrário
    """
    required_columns = [
        'artigo_cod', 'descricao', 'unidade',
        'quant_a', 'quant_b', 'quant_c', 'quant_total'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            print(f"❌ Coluna obrigatória em falta: {col}")
            return False
    
    # Validar que quant_total = quant_a + quant_b + quant_c
    df['quant_check'] = df['quant_a'] + df['quant_b'] + df['quant_c']
    discrepancies = df[abs(df['quant_total'] - df['quant_check']) > 0.01]
    
    if len(discrepancies) > 0:
        print(f"⚠️  {len(discrepancies)} artigos com discrepâncias nas quantidades")
        return False
    
    return True
