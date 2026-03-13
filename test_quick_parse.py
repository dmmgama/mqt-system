"""
Teste rápido do parser com ficheiro MQT_Amorim.xlsx
"""
from pipeline.parser_excel import parse_mqt, validate_artigos

# Caminho para o ficheiro de teste
excel_path = "data/samples/MQT_Amorim.xlsx"

print("=" * 60)
print("TESTE RÁPIDO DO PARSER MQT")
print("=" * 60)

# Parse do ficheiro
artigos = parse_mqt(excel_path)

print(f"\n📊 Total de artigos parseados: {len(artigos)}")

# Validar artigos
print("\n🔍 A validar artigos...")
validate_artigos(artigos)

# Mostrar primeiros 5 artigos
print(f"\n📋 Primeiros 5 artigos:\n")
for i, artigo in enumerate(artigos[:5], 1):
    print(f"{i}. {artigo['artigo_cod']} - {artigo['descricao'][:50]}...")
    print(f"   Cap: {artigo['capitulo']}, Subcap: {artigo['subcapitulo']}, Sufixo: {artigo['sufixo']}")
    print(f"   Classe: {artigo['classe_material']}, Unidade: {artigo['unidade']}")
    print(f"   Quant: A={artigo['quant_a']}, B={artigo['quant_b']}, C={artigo['quant_c']}, Total={artigo['quant_total']}")
    print()

# Estatísticas por capítulo
print("\n📈 Artigos por capítulo:")
capitulos = {}
for artigo in artigos:
    cap = artigo['capitulo']
    capitulos[cap] = capitulos.get(cap, 0) + 1

for cap in sorted(capitulos.keys()):
    print(f"   Capítulo {cap}: {capitulos[cap]} artigos")

# Mostrar classes de material encontradas
print("\n🏗️  Classes de material encontradas:")
classes = set()
for artigo in artigos:
    if artigo['classe_material']:
        classes.add(artigo['classe_material'])

for classe in sorted(classes):
    count = sum(1 for a in artigos if a['classe_material'] == classe)
    print(f"   {classe}: {count} artigos")

print("\n" + "=" * 60)
print("✅ TESTE CONCLUÍDO")
print("=" * 60)
