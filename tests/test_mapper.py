"""
Testes unitários para o mapeamento de artigos
"""
import pytest
from pipeline.mapper_artigos import validate_elemento_tipo, ELEMENTO_TIPOS_VALIDOS


def test_validate_elemento_tipo_valid():
    """Testa validação de elementos válidos"""
    assert validate_elemento_tipo("PILAR") is True
    assert validate_elemento_tipo("VIGA") is True
    assert validate_elemento_tipo("LAJE_MACICA") is True
    assert validate_elemento_tipo("FUNDACAO") is True


def test_validate_elemento_tipo_invalid():
    """Testa validação de elementos inválidos"""
    assert validate_elemento_tipo("INVALIDO") is False
    assert validate_elemento_tipo("pilar") is False  # case-sensitive
    assert validate_elemento_tipo("") is False


def test_elemento_tipos_unique():
    """Verifica que não há duplicados na lista de tipos válidos"""
    assert len(ELEMENTO_TIPOS_VALIDOS) == len(set(ELEMENTO_TIPOS_VALIDOS))


def test_elemento_tipos_uppercase():
    """Verifica que todos os tipos estão em uppercase"""
    for tipo in ELEMENTO_TIPOS_VALIDOS:
        assert tipo == tipo.upper(), f"{tipo} não está em uppercase"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
