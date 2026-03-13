"""
Parser de ficheiros Excel MQT
Lê ficheiros Excel JSJ formato MQT e extrai artigos
"""
import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from openpyxl import load_workbook


def _detect_layout(ws) -> dict:
    """
    Detecta layout de colunas lendo linha 14.
    Retorna dict com índices 0-based:
    {
        quant_cols: [6, 8, 10] ou [6, 8, 10, 12],  # índices 0-based das zonas
        quant_total: 13,   # 0-based
        preco_unit: 14,
        total_eur: 15
    }
    """
    header_row = ws[14]
    quant_cols = []
    quant_total_col = None
    preco_unit_col = None
    total_eur_col = None
    
    for i, cell in enumerate(header_row[:20]):
        val = str(cell.value or '').strip().upper()
        if val == 'QUANT.':
            quant_cols.append(i)
        elif 'QUANT. TOTAL' in val or 'QUANT.TOTAL' in val:
            quant_total_col = i
        elif 'P. UNIT' in val or 'P.UNIT' in val:
            preco_unit_col = i
        elif val == 'TOTAL €':
            total_eur_col = i
    
    return {
        'quant_cols': quant_cols,
        'quant_total': quant_total_col,
        'preco_unit': preco_unit_col,
        'total_eur': total_eur_col
    }


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
    
    # Detectar layout automaticamente
    layout = _detect_layout(ws)
    quant_cols = layout['quant_cols']
    col_quant_total = layout['quant_total']
    col_preco_unit = layout['preco_unit']
    col_total_eur = layout['total_eur']
    
    # Colunas fixas (0-based)
    COL_ARTIGO_COD = 3   # D (0-based)
    COL_DESCRICAO = 4    # E
    COL_UNIDADE = 5      # F
    
    artigos = []
    linhas_processadas = 0
    linhas_ignoradas = 0
    
    # Ler linhas de dados (15 a 153, 1-based)
    for row_num in range(15, 154):
        row = ws[row_num]
        
        # Obter valor da coluna D (artigo_cod)
        artigo_cod_value = row[COL_ARTIGO_COD].value
        
        # Ignorar se vazio
        if artigo_cod_value is None:
            linhas_ignoradas += 1
            continue
        
        # Ignorar se é float (cabeçalhos de capítulo como 5.0, 15.0)
        if isinstance(artigo_cod_value, (int, float)):
            linhas_ignoradas += 1
            continue
        
        # Converter para string e fazer strip (incluindo aspas)
        artigo_cod = str(artigo_cod_value).strip().strip("'\"")
        
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
        descricao = _get_cell_string(row[COL_DESCRICAO])
        unidade = _get_cell_string(row[COL_UNIDADE])
        
        # Extrair classe de material da descrição (ex: C30/37)
        classe_material = extract_classe_material(descricao)
        
        # Extrair quantidades (floats ou None) - detecção automática de zonas
        zonas = [_get_cell_float(row[c]) for c in quant_cols]
        quant_a = zonas[0] if len(zonas) > 0 else None
        quant_b = zonas[1] if len(zonas) > 1 else None
        quant_c = zonas[2] if len(zonas) > 2 else None
        
        # Se 4 zonas, agregar b+c (índices 1 e 2) em quant_b, zona 3 em quant_c
        if len(zonas) == 4:
            b2 = zonas[1] or 0
            b3 = zonas[2] or 0
            quant_b = round(b2 + b3, 4) if (b2 or b3) else None
            quant_c = zonas[3]
        
        quant_total = _get_cell_float(row[col_quant_total]) if col_quant_total is not None else None
        # Fallback: somar zonas se quant_total None
        if quant_total is None and zonas:
            soma = sum(z or 0 for z in zonas)
            quant_total = round(soma, 4) if soma else None
        
        preco_unit = _get_cell_float(row[col_preco_unit]) if col_preco_unit is not None else None
        total_eur = _get_cell_float(row[col_total_eur]) if col_total_eur is not None else None
        
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
