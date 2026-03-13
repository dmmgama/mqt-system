"""
Teste do parser com detecção automática de layout
Usar com ficheiro CUFMQT.xlsx
"""
import sys
from pathlib import Path
from collections import Counter
from pipeline.parser_excel import parse_mqt

def test_parser_cuf():
    """Testa parser com CUFMQT.xlsx"""
    
    # Usar ficheiro do utilizador (deve passar path como argumento)
    if len(sys.argv) < 2:
        print("❌ Uso: python test_parser_cuf.py <path_to_CUFMQT.xlsx>")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    
    if not Path(excel_path).exists():
        print(f"❌ Ficheiro não encontrado: {excel_path}")
        sys.exit(1)
    
    print(f"📖 A fazer parse de: {excel_path}\n")
    
    # Parse
    artigos = parse_mqt(excel_path)
    
    # Estatísticas
    print(f"\n{'='*70}")
    print(f"ESTATÍSTICAS")
    print(f"{'='*70}\n")
    
    print(f"📊 Total de artigos: {len(artigos)}")
    
    # Distribuição por elemento_tipo
    elementos = Counter(a.get('elemento_tipo', 'N/D') for a in artigos)
    
    print(f"\n📋 Distribuição por elemento_tipo:")
    for elemento, count in sorted(elementos.items()):
        print(f"   {elemento:20} → {count:3} artigos")
    
    # Lista de OUTRO
    outros = [a for a in artigos if a.get('elemento_tipo') == 'OUTRO']
    if outros:
        print(f"\n⚠️  Artigos mapeados como OUTRO ({len(outros)}):")
        for a in outros:
            print(f"   • {a['artigo_cod']:12} | cap={a['capitulo']:2} suf={a['sufixo']:6} | {a['descricao'][:50]}")
    
    # Artigos sem elemento_tipo
    sem_tipo = [a for a in artigos if not a.get('elemento_tipo')]
    if sem_tipo:
        print(f"\n❌ Artigos sem elemento_tipo ({len(sem_tipo)}):")
        for a in sem_tipo:
            print(f"   • {a['artigo_cod']:12} | {a['descricao'][:50]}")
    
    print(f"\n{'='*70}")
    print(f"✅ Parse completo")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    test_parser_cuf()
