"""
Parser de ficheiros Excel MQT
Lê ficheiros Excel JSJ formato MQT e extrai artigos
"""
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from openpyxl import load_workbook


def parse_mqt(excel_path) -> List[Dict]:
    """
    Faz parse de um ficheiro Excel MQT JSJ
    
    Especificações:
    - Sheet: '02.MQT'
    - Header: linha 14
    - Dados: linhas 15 a 153
    - Artigos reais: col D é string formato 'X.Y.Z' (não float)
    
    Args:
        excel_path: Caminho para ficheiro Excel (str) ou file-like object (upload)
        
    Returns:
        Lista de dicts, um por artigo, com campos:
        {
            artigo_cod, capitulo, subcapitulo, sufixo,
            descricao, unidade, classe_material,
            quant_a, quant_b, quant_c, quant_total,
            preco_unit, total_eur
        }
    """
    if hasattr(excel_path, 'read'):
        # file-like object (Streamlit UploadedFile)
        excel_path.seek(0)
        wb = load_workbook(BytesIO(excel_path.read()), data_only=True)
    else:
        # path string
        wb = load_workbook(excel_path, data_only=True)
    
    # Verificar se sheet existe
    sheet_name = '02.MQT'
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' não encontrada. Sheets disponíveis: {wb.sheetnames}")
    
    ws = wb[sheet_name]
    
    # Mapear colunas (1-based index)
    COL_ARTIGO_COD = 4   # D
    COL_DESCRICAO = 5    # E
    COL_UNIDADE = 6      # F
    COL_QUANT_A = 7      # G (Fundações)
    COL_QUANT_B = 9      # I (Piso Térreo)
    COL_QUANT_C = 11     # K (Pisos Elevados)
    COL_QUANT_TOTAL = 14 # N
    COL_PRECO_UNIT = 15  # O
    COL_TOTAL_EUR = 16   # P
    
    artigos = []
    linhas_processadas = 0
    linhas_ignoradas = 0
    
    # Ler linhas de dados (15 a 153, 1-based)
    for row_num in range(15, 154):
        row = ws[row_num]
        
        # Obter valor da coluna D (artigo_cod)
        artigo_cod_value = row[COL_ARTIGO_COD - 1].value
        
        # Ignorar se vazio
        if artigo_cod_value is None:
            linhas_ignoradas += 1
            continue
        
        # Ignorar se é float (cabeçalhos de capítulo como 5.0, 15.0)
        if isinstance(artigo_cod_value, (int, float)):
            linhas_ignoradas += 1
            continue
        
        # Converter para string e fazer strip
        artigo_cod = str(artigo_cod_value).strip()
        
        # Verificar se tem formato de artigo (contém pontos)
        if '.' not in artigo_cod:
            linhas_ignoradas += 1
            continue
        
        # Parse do código de artigo
        parsed_cod = extract_capitulo_info(artigo_cod)
        if parsed_cod['capitulo'] is None:
            linhas_ignoradas += 1
            continue
        
        # Extrair outros campos
        descricao = _get_cell_string(row[COL_DESCRICAO - 1])
        unidade = _get_cell_string(row[COL_UNIDADE - 1])
        
        # Extrair classe de material da descrição (ex: C30/37)
        classe_material = extract_classe_material(descricao)
        
        # Extrair quantidades (floats ou None)
        quant_a = _get_cell_float(row[COL_QUANT_A - 1])
        quant_b = _get_cell_float(row[COL_QUANT_B - 1])
        quant_c = _get_cell_float(row[COL_QUANT_C - 1])
        quant_total = _get_cell_float(row[COL_QUANT_TOTAL - 1])
        preco_unit = _get_cell_float(row[COL_PRECO_UNIT - 1])
        total_eur = _get_cell_float(row[COL_TOTAL_EUR - 1])
        
        # Criar dict do artigo
        artigo = {
            'artigo_cod': artigo_cod,
            'capitulo': parsed_cod['capitulo'],
            'subcapitulo': parsed_cod['subcapitulo'],
            'sufixo': parsed_cod['sufixo'],
            'descricao': descricao,
            'unidade': unidade,
            'classe_material': classe_material,
            'quant_a': quant_a,
            'quant_b': quant_b,
            'quant_c': quant_c,
            'quant_total': quant_total,
            'preco_unit': preco_unit,
            'total_eur': total_eur
        }
        
        artigos.append(artigo)
        linhas_processadas += 1
    
    wb.close()
    
    print(f"   ✓ {linhas_processadas} artigos parseados")
    print(f"   ℹ {linhas_ignoradas} linhas ignoradas (cabeçalhos/vazias)")
    
    return artigos


def extract_capitulo_info(artigo_cod: str) -> Dict[str, Optional[str]]:
    """
    Extrai informação do código de artigo
    
    Regras:
    - capitulo   = 1º segmento         ex: '5.5.1'   → '5'
    - subcapitulo = 1º+2º segmento     ex: '5.5.1'   → '5.5'
    - sufixo     = restantes segmentos ex: '5.5.1'   → '1'
                                        ex: '6.2.4.1' → '4.1'
                                        ex: '15.3.1'  → '3.1'
    
    Args:
        artigo_cod: código do artigo (ex: "5.5.4", "6.2.4.1", "15.3.1")
        
    Returns:
        Dict com capitulo, subcapitulo, sufixo (strings ou None se inválido)
    """
    partes = artigo_cod.split('.')
    
    # Mínimo 3 segmentos para ser artigo válido
    if len(partes) < 3:
        return {
            'capitulo': None,
            'subcapitulo': None,
            'sufixo': None
        }
    
    try:
        capitulo = partes[0]  # '5' ou '15'
        subcapitulo = f"{partes[0]}.{partes[1]}"  # '5.5' ou '15.3'
        sufixo = '.'.join(partes[2:])  # '1' ou '4.1' ou '3.1'
        
        return {
            'capitulo': capitulo,
            'subcapitulo': subcapitulo,
            'sufixo': sufixo
        }
    except Exception:
        return {
            'capitulo': None,
            'subcapitulo': None,
            'sufixo': None
        }


def extract_classe_material(descricao: str) -> Optional[str]:
    """
    Extrai classe de material da descrição (ex: C30/37, C20/25)
    
    Args:
        descricao: texto da descrição do artigo
        
    Returns:
        String com classe (ex: 'C30/37') ou None se não encontrado
    """
    if not descricao:
        return None
    
    # Regex para capturar padrão CXX/XX
    pattern = r'C\d+/\d+'
    match = re.search(pattern, descricao)
    
    if match:
        return match.group(0)
    
    return None


def _get_cell_string(cell) -> str:
    """
    Obtém valor de célula como string (stripped)
    
    Args:
        cell: objeto Cell do openpyxl
        
    Returns:
        String (vazia se None)
    """
    value = cell.value
    if value is None:
        return ""
    return str(value).strip()


def _get_cell_float(cell) -> Optional[float]:
    """
    Obtém valor de célula como float
    
    Args:
        cell: objeto Cell do openpyxl
        
    Returns:
        Float ou None se vazio/inválido
    """
    value = cell.value
    if value is None or value == "":
        return None
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def validate_artigos(artigos: List[Dict]) -> bool:
    """
    Valida lista de artigos parseados
    
    Args:
        artigos: lista de dicts com artigos
        
    Returns:
        True se válido, False com warnings caso contrário
    """
    if not artigos:
        print("⚠️  Nenhum artigo encontrado")
        return False
    
    issues = 0
    
    for i, artigo in enumerate(artigos):
        # Validar campos obrigatórios
        if not artigo.get('artigo_cod'):
            print(f"⚠️  Linha {i+1}: artigo_cod vazio")
            issues += 1
        
        if not artigo.get('descricao'):
            print(f"⚠️  Linha {i+1}: descricao vazia para {artigo.get('artigo_cod')}")
            issues += 1
        
        # Validar quant_total = quant_a + quant_b + quant_c (se todos definidos)
        qa = artigo.get('quant_a') or 0
        qb = artigo.get('quant_b') or 0
        qc = artigo.get('quant_c') or 0
        qt = artigo.get('quant_total') or 0
        
        soma = qa + qb + qc
        if abs(qt - soma) > 0.01 and qt != 0:
            print(f"⚠️  {artigo['artigo_cod']}: quant_total ({qt}) ≠ soma ({soma})")
            issues += 1
    
    if issues > 0:
        print(f"⚠️  {issues} problemas encontrados na validação")
        return False
    
    print(f"✅ Validação OK: {len(artigos)} artigos válidos")
    return True
