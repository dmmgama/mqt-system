"""
Testes unitários para o parser de Excel MQT
"""
import pytest
from pipeline.parser_excel import extract_capitulo_info, validate_artigo_structure
import pandas as pd


def test_extract_capitulo_info_simple():
    """Testa parsing de código de artigo simples (3 segmentos)"""
    info = extract_capitulo_info("5.5.4")
    
    assert info['capitulo'] == 5
    assert info['subcapitulo'] == "5.5"
    assert info['sufixo'] == "4"


def test_extract_capitulo_info_complex():
    """Testa parsing de código de artigo complexo (4+ segmentos)"""
    info = extract_capitulo_info("6.2.4.1")
    
    assert info['capitulo'] == 6
    assert info['subcapitulo'] == "6.2"
    assert info['sufixo'] == "4.1"


def test_extract_capitulo_info_very_complex():
    """Testa parsing de código com muitos segmentos"""
    info = extract_capitulo_info("7.1.1.2")
    
    assert info['capitulo'] == 7
    assert info['subcapitulo'] == "7.1"
    assert info['sufixo'] == "1.2"


def test_extract_capitulo_info_invalid():
    """Testa parsing de código inválido"""
    info = extract_capitulo_info("5.5")
    
    assert info['capitulo'] is None
    assert info['subcapitulo'] is None
    assert info['sufixo'] is None


def test_validate_artigo_structure_valid():
    """Testa validação de DataFrame válido"""
    data = {
        'artigo_cod': ['5.5.4', '6.2.4'],
        'descricao': ['Betão C25/30 Pilares', 'Cofragem Pilares'],
        'unidade': ['m³', 'm²'],
        'quant_a': [10.0, 50.0],
        'quant_b': [5.0, 25.0],
        'quant_c': [15.0, 75.0],
        'quant_total': [30.0, 150.0]
    }
    
    df = pd.DataFrame(data)
    assert validate_artigo_structure(df) is True


def test_validate_artigo_structure_invalid_totals():
    """Testa validação com totais incorrectos"""
    data = {
        'artigo_cod': ['5.5.4'],
        'descricao': ['Betão C25/30 Pilares'],
        'unidade': ['m³'],
        'quant_a': [10.0],
        'quant_b': [5.0],
        'quant_c': [15.0],
        'quant_total': [25.0]  # Deveria ser 30.0
    }
    
    df = pd.DataFrame(data)
    assert validate_artigo_structure(df) is False


def test_validate_artigo_structure_missing_columns():
    """Testa validação com colunas em falta"""
    data = {
        'artigo_cod': ['5.5.4'],
        'descricao': ['Betão C25/30 Pilares'],
        'unidade': ['m³']
        # Faltam quant_a, quant_b, quant_c, quant_total
    }
    
    df = pd.DataFrame(data)
    assert validate_artigo_structure(df) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
