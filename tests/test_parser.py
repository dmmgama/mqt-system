"""
Testes unitários para o parser de Excel MQT
"""
# import pytest
from pipeline.parser_excel import (
    extract_capitulo_info,
    extract_classe_material,
    _get_cell_string,
    _get_cell_float,
    validate_artigos
)


def test_extract_capitulo_info_simple():
    """Testa parsing de código de artigo simples (3 segmentos)"""
    info = extract_capitulo_info("5.5.4")
    
    assert info['capitulo'] == "5"
    assert info['subcapitulo'] == "5.5"
    assert info['sufixo'] == "4"


def test_extract_capitulo_info_complex():
    """Testa parsing de código de artigo complexo (4 segmentos)"""
    info = extract_capitulo_info("6.2.4.1")
    
    assert info['capitulo'] == "6"
    assert info['subcapitulo'] == "6.2"
    assert info['sufixo'] == "4.1"


def test_extract_capitulo_info_very_complex():
    """Testa parsing de código com muitos segmentos"""
    info = extract_capitulo_info("7.1.1.2")
    
    assert info['capitulo'] == "7"
    assert info['subcapitulo'] == "7.1"
    assert info['sufixo'] == "1.2"


def test_extract_capitulo_info_dois_digitos():
    """Testa parsing de capítulo com 2 dígitos (ex: 15)"""
    info = extract_capitulo_info("15.3.1")
    
    assert info['capitulo'] == "15"
    assert info['subcapitulo'] == "15.3"
    assert info['sufixo'] == "1"


def test_extract_capitulo_info_invalid():
    """Testa parsing de código inválido"""
    info = extract_capitulo_info("5.5")
    
    assert info['capitulo'] is None
    assert info['subcapitulo'] is None
    assert info['sufixo'] is None


def test_extract_classe_material_c30():
    """Testa extração de classe de betão C30/37"""
    classe = extract_classe_material("Betão C30/37 em Pilares")
    assert classe == "C30/37"


def test_extract_classe_material_c25():
    """Testa extração de classe de betão C25/30"""
    classe = extract_classe_material("C25/30 - Fundações")
    assert classe == "C25/30"


def test_extract_classe_material_c20():
    """Testa extração de classe de betão C20/25"""
    classe = extract_classe_material("Laje Fundo C20/25")
    assert classe == "C20/25"


def test_extract_classe_material_none():
    """Testa que retorna None quando não há classe"""
    classe = extract_classe_material("Cofragem de Pilares")
    assert classe is None


def test_extract_classe_material_empty():
    """Testa com string vazia"""
    classe = extract_classe_material("")
    assert classe is None


def test_extract_classe_material_none_input():
    """Testa com None"""
    classe = extract_classe_material(None)
    assert classe is None


def test_validate_artigos_empty():
    """Testa validação com lista vazia"""
    assert validate_artigos([]) is False


def test_validate_artigos_valid():
    """Testa validação com artigos válidos"""
    artigos = [
        {
            'artigo_cod': '5.5.4',
            'descricao': 'Betão C30/37',
            'quant_a': 10.0,
            'quant_b': 5.0,
            'quant_c': 15.0,
            'quant_total': 30.0
        }
    ]
    assert validate_artigos(artigos) is True


def test_validate_artigos_invalid_total():
    """Testa validação com total incorreto"""
    artigos = [
        {
            'artigo_cod': '5.5.4',
            'descricao': 'Betão C30/37',
            'quant_a': 10.0,
            'quant_b': 5.0,
            'quant_c': 15.0,
            'quant_total': 25.0  # Deveria ser 30.0
        }
    ]
    assert validate_artigos(artigos) is False


if __name__ == "__main__":
    # Testes unitários pytest
    # pytest.main([__file__, "-v"])
    
    # Teste de integração com parser + mapper
    from pipeline.parser_excel import parse_mqt
    from pipeline.mapper_artigos import map_artigos
    from supabase import create_client
    from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
    
    print("\n" + "="*70)
    print("TESTE DE INTEGRAÇÃO: Parser + Mapper")
    print("="*70 + "\n")
    
    # Parse do Excel
    print("📂 Parsing Excel...")
    artigos = parse_mqt('data/samples/MQT_Amorim.xlsx')
    print(f"✅ Parsed {len(artigos)} artigos\n")
    
    # Criar cliente Supabase
    print("🔌 Conectando ao Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✅ Conectado\n")
    
    # Mapear artigos
    print("🗺️  Mapeando artigos...\n")
    artigos_mapped = map_artigos(artigos, client)
    
    # Verificar alguns artigos conhecidos
    print("\n" + "="*70)
    print("AMOSTRA DE ARTIGOS MAPEADOS")
    print("="*70 + "\n")
    
    for a in artigos_mapped[:10]:  # Primeiros 10
        print(f"{a['artigo_cod']:8s} → {a['elemento_tipo']:15s} | {a['descricao'][:50]}")
    
    # Listar artigos sem mapeamento (OUTRO)
    print("\n" + "="*70)
    print("ARTIGOS SEM MAPEAMENTO (elemento_tipo='OUTRO')")
    print("="*70 + "\n")
    
    outros = [a for a in artigos_mapped if a['elemento_tipo'] == 'OUTRO']
    print(f"Total sem mapeamento: {len(outros)} de {len(artigos_mapped)}\n")
    
    for a in outros:
        desc_curta = a['descricao'][:60] if a['descricao'] else "N/A"
        print(f"  {a['artigo_cod']:8s} | cap={a['capitulo']:2s} suf={a['sufixo']:5s} | {desc_curta}")
    
    # Estatísticas por elemento_tipo
    print("\n" + "="*70)
    print("ESTATÍSTICAS POR ELEMENTO_TIPO")
    print("="*70 + "\n")
    
    from collections import Counter
    elemento_counts = Counter(a['elemento_tipo'] for a in artigos_mapped)
    
    for elemento_tipo, count in sorted(elemento_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(artigos_mapped)) * 100
        print(f"  {elemento_tipo:15s}: {count:3d} ({pct:5.1f}%)")
    
    print("\n" + "="*70)
