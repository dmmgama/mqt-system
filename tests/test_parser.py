"""
Testes unitários para o parser de Excel MQT
"""
import pytest
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
    pytest.main([__file__, "-v"])
