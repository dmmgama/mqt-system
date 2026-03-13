# MQT-SYSTEM — README PARA AGENTE IDE
**Versão:** 3.0 · **Data:** 2026-03-13
**Para:** GitHub Copilot / Cursor / agente VS Code
**Contexto:** Branch 1 em curso (`fix-schema-mqt`) — fixes de UI + visual da tab Artigos

---

## ESTADO ACTUAL (v3.0)

### ✅ Concluído e funcional
- Schema Supabase: Fix E/F/G/H corridos — todas as colunas existem
- `pipeline/parser_excel.py` — hierarquia completa (caps + subcaps + artigos + specs)
- `pipeline/mapper_artigos.py` — lookup por (capitulo, sufixo) correcto
- `pipeline/ingest_mqt.py` — file-like, emissao, area_construcao, substituição de snapshots
- `validation/indices.py` — A/V lajes conjunto, filtro 7.X.{12,14,16}, C/Area nullable
- `dashboard/app.py` — 4 tabs funcionais, campos emissão e área na ingestão
- `elemento_map` seed — 64 linhas, sufixos 1-21+99 correctos por KB-07

### 🔴 Pendente nesta sessão (3 fixes + commit)
- FIX UI-1: Tab Artigos — visual hierárquico (caps bold/cinza, subcaps bold)
- FIX UI-2: Tab Artigos — filtro capítulo ordenado ascendente
- FIX UI-3: mapper — OUTRO só para caps 5/6/7 com sufixo desconhecido
- FIX UI-4: Tab Artigos e Índices — nomes de elemento legíveis (sem underscore)

### 🟡 Branch 2 (após commit desta branch)
- `apps/projetos_app.py` — ficha de projecto 4 níveis
- `apps/main_app.py` — st.navigation()
- Renomear `dashboard/app.py` → `apps/mqt_app.py`

---

## FIXES DESTA SESSÃO

### FIX UI-1 — dashboard/app.py: visual hierárquico na tab Artigos

A tab Artigos mostra todos os níveis numa tabela plana. Substituir o `st.dataframe`
por uma tabela HTML renderizada com `st.markdown(..., unsafe_allow_html=True)`.

**Lógica de estilo por nível:**
- `nivel == 1` (capítulo): fundo `#e8e8e8`, texto bold, font-size 13px
- `nivel == 2` (subcapítulo): fundo transparente, texto bold, font-size 13px
- `nivel >= 3` (artigo): fundo transparente, texto normal, font-size 12px

**Colunas a mostrar:** Código | Descrição | Unidade | Elemento | Quant A | Quant B | Quant C | Total

Substituir o bloco da tab Artigos desde `# Carregar artigos` até ao `st.dataframe` por:

```python
# Carregar artigos — incluir campo nivel
artigos_resp = client.table("mqt_artigos").select(
    "artigo_cod, descricao, unidade, elemento_tipo, capitulo, nivel, quant_a, quant_b, quant_c, quant_total"
).eq("snapshot_id", snapshot_id_art).order("id").execute()

if not artigos_resp.data:
    st.warning("⚠️ Nenhum artigo encontrado.")
else:
    df_artigos = pd.DataFrame(artigos_resp.data)

    with col1:
        # Filtro capítulo — ordenado numericamente ascendente
        caps_raw = [c for c in df_artigos["capitulo"].unique().tolist() if c is not None]
        try:
            caps_sorted = sorted(caps_raw, key=lambda x: int(x))
        except Exception:
            caps_sorted = sorted(caps_raw)
        capitulos = ["Todos"] + caps_sorted
        filtro_capitulo = st.selectbox("Capítulo", capitulos)

    with col2:
        elementos = ["Todos"] + sorted([e for e in df_artigos["elemento_tipo"].unique().tolist() if e is not None])
        filtro_elemento = st.selectbox("Elemento", elementos)

    df_filtered = df_artigos.copy()
    if filtro_capitulo != "Todos":
        df_filtered = df_filtered[df_filtered["capitulo"] == filtro_capitulo]
    if filtro_elemento != "Todos":
        df_filtered = df_filtered[df_filtered["elemento_tipo"] == filtro_elemento]

    # Mapa de nomes de elemento legíveis
    ELEMENTO_LABELS = {
        "FUNDACAO": "Fundações",
        "LAJE_FUNDO": "Laje de fundo",
        "VIGA_FUND": "Vigas de fundação",
        "PILAR": "Pilares",
        "NUCLEO": "Núcleos",
        "PAREDE": "Paredes",
        "PAREDE_PISC": "Paredes de piscinas",
        "PAREDE_RES": "Paredes de reservatórios",
        "CONTENCAO": "Paredes de contenção",
        "VIGA": "Vigas",
        "LAJE_MACICA": "Lajes maciças e dobras",
        "LAJE_ALIG": "Lajes aligeiradas",
        "RAMPA": "Lajes de rampas",
        "BANDA": "Bandas",
        "CAPITEL": "Capitéis",
        "MURETE": "Muretes e platibandas",
        "ESCADA": "Escadas betonadas in situ",
        "MASSAME": "Massame",
        "MACIÇO": "Maciços e plintos",
        "OUTRO": "Outros",
    }

    def _fmt_num(v):
        if v is None or (isinstance(v, float) and v == 0.0):
            return ""
        try:
            return f"{float(v):,.2f}".replace(",", " ")
        except Exception:
            return str(v)

    def _row_style(nivel):
        if nivel == 1:
            return 'background:#e8e8e8;font-weight:bold;font-size:13px;'
        elif nivel == 2:
            return 'font-weight:bold;font-size:13px;'
        else:
            return 'font-size:12px;'

    # Construir tabela HTML
    html = """
    <style>
    .mqt-table { width:100%; border-collapse:collapse; font-family:sans-serif; }
    .mqt-table th { background:#333; color:#fff; padding:6px 8px; text-align:left; font-size:12px; }
    .mqt-table td { padding:4px 8px; border-bottom:1px solid #e0e0e0; vertical-align:top; }
    .mqt-table tr:hover td { background:#f5f5f5; }
    </style>
    <table class="mqt-table">
    <tr>
      <th>Código</th><th>Descrição</th><th>Un</th><th>Elemento</th>
      <th style="text-align:right">Quant A</th>
      <th style="text-align:right">Quant B</th>
      <th style="text-align:right">Quant C</th>
      <th style="text-align:right">Total</th>
    </tr>
    """

    for _, row in df_filtered.iterrows():
        nivel = row.get("nivel") or 3
        style = _row_style(nivel)
        elem_raw = row.get("elemento_tipo") or ""
        elem_label = ELEMENTO_LABELS.get(elem_raw, elem_raw.replace("_", " ").title()) if elem_raw else ""
        html += f"""<tr style="{style}">
          <td>{row.get('artigo_cod','')}</td>
          <td>{row.get('descricao','') or ''}</td>
          <td>{row.get('unidade','') or ''}</td>
          <td>{elem_label}</td>
          <td style="text-align:right">{_fmt_num(row.get('quant_a'))}</td>
          <td style="text-align:right">{_fmt_num(row.get('quant_b'))}</td>
          <td style="text-align:right">{_fmt_num(row.get('quant_c'))}</td>
          <td style="text-align:right">{_fmt_num(row.get('quant_total'))}</td>
        </tr>"""

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)
    st.caption(f"📊 {len(df_filtered)} linhas")
```

---

### FIX UI-2 — mapper_artigos.py: OUTRO só para caps 5/6/7

Nos capítulos que não são 5, 6 ou 7, os artigos não têm `elemento_tipo` —
não devem ser mapeados como OUTRO, devem ficar `None`.

No loop principal de `map_artigos()`, substituir o bloco de lookup:

```python
# ANTES:
key = (capitulo, elemento_sufixo)
elemento_tipo = lookup.get(key)
if elemento_tipo:
    artigo['elemento_tipo'] = elemento_tipo
else:
    artigo['elemento_tipo'] = 'OUTRO'
    print(f"⚠️  Sem mapeamento: {artigo_cod} | cap={capitulo} elem_suf={elemento_sufixo}")

# DEPOIS:
CAPS_COM_MAPEAMENTO = {'5', '6', '7'}

key = (capitulo, elemento_sufixo)
elemento_tipo = lookup.get(key)

if elemento_tipo:
    artigo['elemento_tipo'] = elemento_tipo
elif capitulo in CAPS_COM_MAPEAMENTO:
    # Sufixo desconhecido dentro dos caps estruturais → OUTRO com aviso
    artigo['elemento_tipo'] = 'OUTRO'
    print(f"⚠️  Sem mapeamento: {artigo_cod} | cap={capitulo} elem_suf={elemento_sufixo}")
else:
    # Caps 1,2,3,4,8,9,10,11,12,13,15... → sem elemento_tipo (correcto)
    artigo['elemento_tipo'] = None
```

---

### FIX UI-3 — dashboard/app.py: nomes de elemento legíveis na tab Índices

Na tab Índices, a coluna "Elemento" mostra `LAJE_MACICA`, `PAREDE_RES`, etc.
Aplicar o mesmo `ELEMENTO_LABELS` dict para apresentação.

Após construir `df_display`, adicionar antes do `st.dataframe`:

```python
ELEMENTO_LABELS = {
    "FUNDACAO": "Fundações", "LAJE_FUNDO": "Laje de fundo",
    "VIGA_FUND": "Vigas de fundação", "PILAR": "Pilares",
    "NUCLEO": "Núcleos", "PAREDE": "Paredes",
    "PAREDE_PISC": "Paredes de piscinas", "PAREDE_RES": "Paredes de reservatórios",
    "CONTENCAO": "Paredes de contenção", "VIGA": "Vigas",
    "LAJE_MACICA": "Lajes maciças e dobras", "LAJE_ALIG": "Lajes aligeiradas",
    "RAMPA": "Lajes de rampas", "BANDA": "Bandas", "CAPITEL": "Capitéis",
    "MURETE": "Muretes e platibandas", "ESCADA": "Escadas betonadas in situ",
    "MASSAME": "Massame", "MACIÇO": "Maciços e plintos", "OUTRO": "Outros",
}
df_display["Elemento"] = df_display["Elemento"].map(
    lambda x: ELEMENTO_LABELS.get(x, x.replace("_"," ").title()) if x else x
)
```

Mover o dict `ELEMENTO_LABELS` para o topo do ficheiro `dashboard/app.py`
(fora das funções, após os imports) para ser reutilizado nas duas tabs.

---

### APÓS OS 3 FIXES

```
git add -A
git commit -m "feat: visual hierárquico tab artigos + elemento labels + OUTRO só caps 5/6/7"
```

Verificar:
- Tab Artigos: caps a cinza bold, subcaps bold, artigos normais
- Tab Artigos: filtro capítulo ordenado 3, 5, 6, 7, 8, 10, 11, 12, 15
- Tab Artigos: coluna Elemento mostra "Lajes maciças e dobras" em vez de "LAJE_MACICA"
- Tab Índices: coluna Elemento com nomes legíveis
- Re-ingerir Amorim: caps 8/10/11/15 ficam com elemento_tipo = None (não OUTRO)

---

## ESTADO DO SUPABASE (actual)

Todas as migrations já corridas. Não correr novamente.

### Tabelas e colunas relevantes

**mqt_artigos:**
- nivel (SMALLINT) — 1=cap, 2=subcap, 3=artigo, 4=nivel4
- artigo_cod, descricao, unidade, especificacao
- capitulo, subcapitulo, sufixo, elemento_sufixo
- classe_material, elemento_tipo, is_nivel4
- quant_a, quant_b, quant_c, quant_d, quant_total

**mqt_snapshots:**
- emissao, area_construcao, num_zonas, zona_labels (JSONB)

**projects:**
- fase, num_zonas, zona_config (JSONB), piso_config (JSONB)
- elem_verticais (JSONB), deleted_at

**elemento_map:**
- PK: (capitulo, sufixo) — sem projeto_id na PK
- 64 linhas globais (projeto_id IS NULL)
- Sufixos 1-21 + 99 para caps 5, 6, 7 — correctos por KB-07

---

## SEED elemento_map DEFINITIVO (KB-07)

Sufixo → elemento_tipo (igual para caps 5, 6, 7):

| sufixo | elemento_tipo      |
|--------|--------------------|
| 1      | FUNDACAO           |
| 2      | LAJE_FUNDO         |
| 3      | VIGA_FUND          |
| 4      | PILAR              |
| 5      | NUCLEO             |
| 6      | PAREDE             |
| 7      | PAREDE_PISC        |
| 8      | PAREDE_RES         |
| 9      | CONTENCAO          |
| 10     | VIGA               |
| 11     | LAJE_MACICA        |
| 12     | LAJE_ALIG          |
| 13     | RAMPA              |
| 14     | BANDA              |
| 15     | CAPITEL            |
| 16     | MURETE             |
| 17     | ESCADA             |
| 18     | MASSAME            |
| 19     | MACIÇO             |
| 20     | OUTRO              |
| 21     | OUTRO              |
| 99     | OUTRO              |

Cap 7 regra especial: `7.X.11` agrega lajes+bandas+capitéis.
`7.X.12`, `7.X.14`, `7.X.15` → sempre 0 (filtrados nos índices).

---

## LÓGICA CRÍTICA JSJ

### Parser (parser_excel.py)
- Header na linha 14 do sheet `02.MQT`
- Classificação por número de segmentos do código:
  - 1 segmento → CAP (nivel=1), sem quantidades
  - 2 segmentos → SUBCAP (nivel=2), com ou sem quantidades
  - 3 segmentos → ARTIGO (nivel=3)
  - 4+ segmentos → ARTIGO nivel4 (is_nivel4=True)
- Linha com cod=None e desc → SPEC, juntar ao artigo anterior em `especificacao`
- `elemento_sufixo` = sempre o 3º segmento (chave de mapeamento)
- Zonas detectadas por pares QUANT.+PARCIAL na linha 14 (nunca ler labels do Excel)

### Índices (indices.py)
- A/V Lajes+Bandas+Capitéis calculado em conjunto:
  `kg(7.X.11) ÷ m³(LAJE_MACICA + BANDA + CAPITEL)`
- Artigos `7.X.{12,14,15}` ignorados (sempre 0)
- C/Area só calculado se `area_construcao` disponível no snapshot

### Ingestão (ingest_mqt.py)
- Deduplicação: se (project_id, fase, emissao) existe → apagar e re-criar
- zona_labels herdado de `projects.zona_config`
- Validação cruzada num_zonas: warning se divergir (não bloqueia)

---

## ESTRUTURA DO REPO

```
mqt-system/
├── config/settings.py
├── pipeline/
│   ├── parser_excel.py
│   ├── mapper_artigos.py
│   └── ingest_mqt.py
├── validation/
│   └── indices.py
├── database/
│   ├── schema_mqt_d04.sql       ← base v1.0 (não alterar)
│   └── schema_migrations.sql   ← ALTER TABLE fixes E/F/G/H
├── dashboard/
│   └── app.py                   ← não renomear até branch/projetos-app
└── tests/
```

**Streamlit:** `streamlit run dashboard/app.py`
**Supabase key:** service_role — nunca expor ou commitar
**Excel:** nunca commitar — está em .gitignore
**venv:** já activo — nunca recriar