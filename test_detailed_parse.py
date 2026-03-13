"""
Análise detalhada de alguns artigos do MQT_Amorim.xlsx
"""
from pipeline.parser_excel import parse_mqt

# Parse do ficheiro
artigos = parse_mqt("data/samples/MQT_Amorim.xlsx")

print("\n" + "=" * 80)
print("ANÁLISE DETALHADA - 10 PRIMEIROS ARTIGOS")
print("=" * 80)

for i, artigo in enumerate(artigos[:10], 1):
    print(f"\n#{i} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Artigo:       {artigo['artigo_cod']}")
    print(f"Descrição:    {artigo['descricao']}")
    print(f"Capitulo:     {artigo['capitulo']}")
    print(f"Subcapitulo:  {artigo['subcapitulo']}")
    print(f"Sufixo:       {artigo['sufixo']}")
    print(f"Unidade:      {artigo['unidade']}")
    print(f"Classe Mat:   {artigo['classe_material']}")
    print(f"Quant A:      {artigo['quant_a']}")
    print(f"Quant B:      {artigo['quant_b']}")
    print(f"Quant C:      {artigo['quant_c']}")
    print(f"Quant Total:  {artigo['quant_total']}")
    print(f"Preço Unit:   {artigo['preco_unit']}")
    print(f"Total EUR:    {artigo['total_eur']}")

# Resumo de artigos com dados
print("\n" + "=" * 80)
print("RESUMO DE DADOS")
print("=" * 80)

artigos_com_quant = [a for a in artigos if (a['quant_a'] or 0) + (a['quant_b'] or 0) + (a['quant_c'] or 0) > 0]
artigos_com_total = [a for a in artigos if a['quant_total'] is not None]
artigos_com_preco = [a for a in artigos if a['preco_unit'] is not None]
artigos_com_classe = [a for a in artigos if a['classe_material'] is not None]

print(f"\nArtigos com quantidades (A/B/C > 0): {len(artigos_com_quant)}/{len(artigos)}")
print(f"Artigos com quant_total preenchido:  {len(artigos_com_total)}/{len(artigos)}")
print(f"Artigos com preço unitário:          {len(artigos_com_preco)}/{len(artigos)}")
print(f"Artigos com classe material:         {len(artigos_com_classe)}/{len(artigos)}")

# Top 5 artigos por quantidade total
print("\n" + "=" * 80)
print("TOP 5 ARTIGOS POR QUANTIDADE")
print("=" * 80)

artigos_ordenados = sorted(
    artigos_com_quant,
    key=lambda x: (x['quant_a'] or 0) + (x['quant_b'] or 0) + (x['quant_c'] or 0),
    reverse=True
)[:5]

for i, artigo in enumerate(artigos_ordenados, 1):
    total = (artigo['quant_a'] or 0) + (artigo['quant_b'] or 0) + (artigo['quant_c'] or 0)
    print(f"\n{i}. {artigo['artigo_cod']} - {artigo['descricao'][:60]}")
    print(f"   Total: {total:.2f} {artigo['unidade']}")
    print(f"   (A={artigo['quant_a']}, B={artigo['quant_b']}, C={artigo['quant_c']})")
