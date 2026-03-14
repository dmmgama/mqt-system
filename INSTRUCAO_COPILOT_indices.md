# INSTRUÇÃO COPILOT — Melhorar Índices
**Branch:** `mqt-zonasdinamicas`
**Ficheiros a alterar:** `validation/indices.py` · `dashboard/app.py`
**Ordem obrigatória:** Tarefa 1 → testar → Tarefa 2

---

## TAREFA 1 — `validation/indices.py`

### 1.1 Adicionar dicionário THRESHOLDS no topo do ficheiro (após os imports)

Adicionar após a linha `ELEMENTOS_LAJE_CONJUNTO = ...`:

```python
# Thresholds KB-05 por elemento_tipo: av_min, av_alvo, av_max
THRESHOLDS = {
    'FUNDACAO':    {'av_min': 80,  'av_alvo': 120, 'av_max': 150},
    'MACIÇO':      {'av_min': 90,  'av_alvo': 120, 'av_max': 160},
    'LAJE_FUNDO':  {'av_min': 110, 'av_alvo': 150, 'av_max': 180},
    'VIGA_FUND':   {'av_min': 120, 'av_alvo': 150, 'av_max': 180},
    'MASSAME':     {'av_min': 80,  'av_alvo': 125, 'av_max': 150},
    'CONTENCAO':   {'av_min': 120, 'av_alvo': 200, 'av_max': 250},
    'PILAR':       {'av_min': 220, 'av_alvo': 300, 'av_max': 350},
    'NUCLEO':      {'av_min': 150, 'av_alvo': 250, 'av_max': 300},
    'PAREDE':      {'av_min': 120, 'av_alvo': 200, 'av_max': 250},
    'PAREDE_PISC': {'av_min': 150, 'av_alvo': 200, 'av_max': 280},
    'PAREDE_RES':  {'av_min': 150, 'av_alvo': 200, 'av_max': 280},
    'MURETE':      {'av_min': 0,   'av_alvo': 0,   'av_max': 80},
    'VIGA':        {'av_min': 160, 'av_alvo': 200, 'av_max': 280},
    'LAJE_MACICA': {'av_min': 90,  'av_alvo': 130, 'av_max': 160},
    'LAJE_ALIG':   {'av_min': 110, 'av_alvo': 150, 'av_max': 180},
    'BANDA':       {'av_min': 120, 'av_alvo': 150, 'av_max': 200},
    'CAPITEL':     {'av_min': 120, 'av_alvo': 150, 'av_max': 200},
    'RAMPA':       {'av_min': 110, 'av_alvo': 120, 'av_max': 180},
    'ESCADA':      {'av_min': 90,  'av_alvo': 120, 'av_max': 150},
}
```

### 1.2 Adicionar função `_calc_flag` (após o dicionário THRESHOLDS)

```python
def _calc_flag(elemento_tipo: str, av) -> str:
    """
    Calcula flag de validação com base nos thresholds KB-05.
    Lógica:
      - av is None ou elemento sem threshold → 'sem_dados'
      - dentro de [av_min, av_max] → 'ok'
      - fora de [av_min, av_max] mas dentro de [av_min*0.7, av_max*1.3] → 'aviso'
      - fora da banda alargada → 'erro'
    Excepção MURETE: aco=0 com av_max=80 → 'ok' se av==0
    """
    if av is None:
        return 'sem_dados'
    t = THRESHOLDS.get(elemento_tipo)
    if t is None:
        return 'sem_dados'
    av_min = t['av_min']
    av_max = t['av_max']
    if av_min <= av <= av_max:
        return 'ok'
    if (av_min * 0.7) <= av <= (av_max * 1.3):
        return 'aviso'
    return 'erro'
```

### 1.3 Substituir `flag = 'ok'` por chamada a `_calc_flag`

**Sítio 1 — loop global** (linha ~`flag = 'ok'` dentro do `for elemento_tipo, qtys in sorted(agregados.items())`):
```python
flag = _calc_flag(elemento_tipo, av)
```

**Sítio 2 — loop por zona** (linha `'flag': 'ok'` dentro do dict `indices_zona.append({...})`):
```python
'flag': _calc_flag(elemento_tipo, av),
```

### 1.4 Adicionar `av_alvo` e `av_min`/`av_max` ao resultado e ao registo DB

No loop global, no dict `resultado` e no dict `indice_db`, adicionar:
```python
't_alvo': THRESHOLDS.get(elemento_tipo, {}).get('av_alvo'),
't_min':  THRESHOLDS.get(elemento_tipo, {}).get('av_min'),
't_max':  THRESHOLDS.get(elemento_tipo, {}).get('av_max'),
```
Nota: estes campos são apenas para retorno à app (dict `resultado`) — **não inserir na DB** (coluna não existe em `mqt_indices`).

### 1.5 Calcular `area_zona_m2` global e incluir no registo global

Após o loop de zonas (`if zona_config:`), antes de fazer `return resultados`, calcular:

```python
# Área total de cofragem de laje (soma de todas as zonas)
area_laje_global = None
if zona_config:
    areas = [
        float(z_row.get('area_zona_m2') or 0)
        for z_row in indices_zona  # reutilizar ultimo indices_zona não funciona — ver nota abaixo
    ]
```

**Atenção:** a forma mais simples é calcular directamente dos artigos, reutilizando a lógica já existente para `area_zona_m2` mas sem filtro de zona:

```python
SUFIXOS_LAJE_COF = {'11', '12', '13', '14', '16'}
area_laje_global = sum(
    float(a.get('quant_total') or 0)
    for a in artigos  # artigos já filtrados (sem 7.X.{12,14,16})
    if a.get('capitulo') == '6'
    and a.get('elemento_sufixo') in SUFIXOS_LAJE_COF
) or None
```

Adicionar `area_zona_m2: area_laje_global` ao dict de cada `indice_db` **global** (os que têm `zona_idx: None`), imediatamente antes do `supabase_client.table('mqt_indices').insert(indices_db).execute()`.

### 1.6 Calcular e retornar índices globais S/A, V/A, C/A

Após o bloco de cálculo de `c_area` (já existente), calcular:

```python
total_aco = sum(qtys['aco_kg'] for qtys in agregados.values())
total_betao = sum(qtys['betao_m3'] for qtys in agregados.values())

indices_globais = {
    'area_laje_global': area_laje_global,
    'c_area': c_area,
    's_a': round(total_aco / area_construcao, 2) if area_construcao and area_construcao > 0 else None,
    'v_a': round(total_betao / area_construcao, 3) if area_construcao and area_construcao > 0 else None,
    'c_a': round(total_cofragem / area_construcao, 3) if area_construcao and area_construcao > 0 else None,
}
print(f"📊 Índices globais: S/A={indices_globais['s_a']} kg/m² | V/A={indices_globais['v_a']} m³/m² | C/A={indices_globais['c_a']} m²/m²")
```

**Alterar o `return` da função** para retornar um tuple:
```python
return resultados, indices_globais
```

Actualizar todos os chamadores de `calcular_indices(...)` na app para desempacotar:
```python
indices, indices_globais = calcular_indices(snapshot_id, client, zona_config=zona_config)
```

---

## TAREFA 2 — `dashboard/app.py` — Tab Índices

### 2.1 Actualizar desempacotamento no botão de ingestão (Tab 1)

Localizar a linha:
```python
indices = calcular_indices(snapshot_id, client, zona_config=zona_config)
```
Substituir por:
```python
indices, indices_globais = calcular_indices(snapshot_id, client, zona_config=zona_config)
```

### 2.2 Métricas globais — acima da tabela de índices

Após o bloco do selector de snapshot e antes de `st.dataframe(...)`, adicionar:

```python
# --- Métricas globais ---
snap_meta = client.table('mqt_snapshots') \
    .select('area_construcao') \
    .eq('id', snapshot_id).single().execute()
area_construcao = (snap_meta.data or {}).get('area_construcao')

# Área de cofragem de laje (do primeiro registo global com area_zona_m2)
area_laje_row = client.table('mqt_indices') \
    .select('area_zona_m2') \
    .eq('snapshot_id', snapshot_id) \
    .is_('zona_idx', 'null') \
    .limit(1).execute()
area_laje = (area_laje_row.data[0].get('area_zona_m2') if area_laje_row.data else None)

if vista == 'Global':
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Área cofragem laje", f"{area_laje:,.0f} m²" if area_laje else "—")
    # S/A, V/A, C/A calculados a partir dos índices carregados
    total_aco = sum(r.get('aco_kg') or 0 for r in indices_resp.data)
    total_betao = sum(r.get('betao_m3') or 0 for r in indices_resp.data)
    total_cofr = sum(r.get('cofragem_m2') or 0 for r in indices_resp.data)
    ac_val = area_construcao or 0
    m2.metric("S/A — Aço/Área", f"{total_aco/ac_val:.1f} kg/m²" if ac_val else "—")
    m3.metric("V/A — Betão/Área", f"{total_betao/ac_val:.3f} m³/m²" if ac_val else "—")
    m4.metric("C/A — Cofr./Área", f"{total_cofr/ac_val:.3f} m²/m²" if ac_val else "—")
    m5.metric("Área construção", f"{ac_val:,.0f} m²" if ac_val else "—")
else:
    # Vista por zona: mostrar apenas área de cofragem de laje da zona
    if area_zona := (indices_resp.data[0].get('area_zona_m2') if indices_resp.data else None):
        st.metric("Área cofragem laje (zona)", f"{area_zona:,.1f} m²")
```

Remover o bloco existente:
```python
# Métrica de área por zona
if vista != 'Global':
    area_zona = indices_resp.data[0].get('area_zona_m2')
    if area_zona:
        st.metric("Área da zona (cofragem laje)", f"{area_zona:,.1f} m²")
```
(já está substituído pelo bloco acima)

### 2.3 Actualizar tabela `df_display` — adicionar A/C e Alvo A/V

Substituir o bloco `df_display = df[[...]].copy()` por:

```python
df_display = df[[
    "elemento_tipo", "betao_m3", "aco_kg", "cofragem_m2",
    "av", "vc", "ac", "flag"
]].copy()

df_display.columns = [
    "Elemento", "Betão m³", "Aço kg", "Cofragem m²",
    "A/V kg/m³", "V/C m³/m²", "A/C kg/m²", "Flag"
]

# Adicionar coluna Alvo A/V a partir de THRESHOLDS (importar ou replicar dict)
THRESHOLDS_ALVO = {
    'FUNDACAO': 120, 'MACIÇO': 120, 'LAJE_FUNDO': 150, 'VIGA_FUND': 150,
    'MASSAME': 125, 'CONTENCAO': 200, 'PILAR': 300, 'NUCLEO': 250,
    'PAREDE': 200, 'PAREDE_PISC': 200, 'PAREDE_RES': 200, 'MURETE': 0,
    'VIGA': 200, 'LAJE_MACICA': 130, 'LAJE_ALIG': 150, 'BANDA': 150,
    'CAPITEL': 150, 'RAMPA': 120, 'ESCADA': 120,
}
df_display.insert(
    df_display.columns.get_loc("A/V kg/m³") + 1,
    "Alvo A/V",
    df["elemento_tipo"].map(THRESHOLDS_ALVO)
)
```

### 2.4 Actualizar formatação de números

Adicionar após as formatações existentes:
```python
df_display["A/C kg/m²"] = df_display["A/C kg/m²"].fillna(0).round(1)
df_display["Alvo A/V"] = df_display["Alvo A/V"].fillna("—")
```

### 2.5 Actualizar `flag_map` para incluir todos os estados

Substituir:
```python
flag_map = {"ok": "🟢", "alerta": "🟡", "erro": "🔴"}
```
Por:
```python
flag_map = {"ok": "🟢", "aviso": "🟡", "erro": "🔴", "sem_dados": "⚪"}
```

### 2.6 Ordenar tabela por ordem estrutural lógica

Antes de `st.dataframe(...)`, adicionar:
```python
ORDEM_ELEMENTOS = [
    "Fundações", "Laje de fundo", "Vigas de fundação", "Massame", "Maciços e plintos",
    "Paredes de contenção", "Pilares", "Núcleos", "Paredes", "Paredes de piscinas",
    "Paredes de reservatórios", "Muretes e platibandas", "Vigas",
    "Lajes maciças e dobras", "Lajes aligeiradas", "Bandas", "Capitéis",
    "Lajes de rampas", "Escadas betonadas in situ", "Outros",
]
df_display["_ordem"] = df_display["Elemento"].map(
    {e: i for i, e in enumerate(ORDEM_ELEMENTOS)}
).fillna(99)
df_display = df_display.sort_values("_ordem").drop(columns=["_ordem"])
```

---

## ORDEM DE EXECUÇÃO

1. Aplicar Tarefa 1 completa em `validation/indices.py`
2. Verificar sem erros de sintaxe
3. Aplicar Tarefa 2 completa em `dashboard/app.py`
4. Reiniciar app: `streamlit run dashboard/app.py`
5. Re-ingerir Amorim EP (para recalcular índices com as novas flags)
6. Verificar tab Índices: flags 🟡/🔴/🟢, coluna A/C, métricas globais
7. Se tudo OK → "bem sucedida, actualiza readme"

---

## TAREFA 3 — `dashboard/app.py` — Caixa explicativa de índices (fundo da Tab Índices)

### Objectivo
Adicionar no final da Tab Índices (após o `st.dataframe` e a ordenação) uma secção expansível com a explicação de cada índice — o que mede, como é calculado, e como interpretar o valor face aos critérios do KB-05.

### Implementação

Adicionar **depois** do bloco `st.dataframe(df_display, ...)`:

```python
# ── Painel explicativo de índices ──────────────────────────────────────
with st.expander("ℹ️ Guia de interpretação dos índices", expanded=False):
    st.markdown("""
### A/V — Aço / Betão (kg/m³) · *Densidade de Armadura*

**Calcula:** `Σ Aço (kg) ÷ Σ Betão (m³)` por elemento estrutural.

**O que mede:** A quantidade de armadura por unidade de volume de betão.
É o indicador estrutural e económico mais importante — revela se um elemento
está sobredimensionado ou se há erros no modelo BIM
(duplicação de armaduras em cruzamentos pilar-viga, omissão de estribos).

**Como interpretar:**
- Taxa geométrica de armadura 1% ≈ 78 kg/m³ · 2% ≈ 157 kg/m³
- Valores baixos (< mín) → armadura em falta ou betão duplicado no modelo
- Valores altos (> máx) → sobredimensionamento ou aço contado em duplicado
- Sapatas são pouco armadas (< 150) · Pilares são densamente armados (> 220)

**Critério de avaliação:**
| Flag | Condição |
|---|---|
| 🟢 ok | Dentro de [A/V mín, A/V máx] do KB-05 |
| 🟡 aviso | Fora de [mín, máx] mas dentro de [mín×0.7, máx×1.3] |
| 🔴 erro | Fora da banda alargada |
| ⚪ sem dados | Elemento sem threshold definido ou sem aço |

---

### V/C — Betão / Cofragem (m³/m²) · *Espessura Equivalente*

**Calcula:** `Σ Betão (m³) ÷ Σ Cofragem (m²)` por elemento estrutural.

**O que mede:** Literalmente a espessura média do elemento em metros.
É o principal detector de erros de geometria e de regras de medição.

**Como interpretar:**
- Cofragem 1 face (ex: muro contra-terra): V/C = espessura real
- Cofragem 2 faces (ex: pilar, viga): V/C = metade da espessura real
- Ex: laje de 0.25m deve ter V/C ≈ 0.25 — se aparecer 1.50, a cofragem de fundo foi esquecida
- Ex: muro de 0.25m com V/C = 0.25 e duas faces → confirmar se ambas as faces estão medidas

**Valores de referência típicos:**
Sapatas 0.80–1.20 · Pilares 0.10–0.25 · Lajes 0.20–0.35 · Bandas 0.30–0.45

---

### A/C — Aço / Cofragem (kg/m²) · *Densidade Superficial*

**Calcula:** `Σ Aço (kg) ÷ Σ Cofragem (m²)` = A/V × V/C

**O que mede:** Quanto aço existe por cada m² de painel de cofragem fechado.
É um indicador derivado de validação cruzada — um erro agudo em A/C
significa quase sempre que A/V ou V/C estão errados.

**Relevância operacional:** Indica o rendimento esperado da subempreitada de
armação. Valores muito acima do normal significam que o empreiteiro vai
pedir trabalhos a mais por excesso de densidade de trabalho.

**Exemplo:** Parede com V/C = 0.15 e A/V = 200 → A/C esperado ≈ 30 kg/m².
Se apresentar 60 kg/m², há incoerência entre betão e aço que requer revisão.

---

### C/Area — Cofragem / Área de Construção (m²/m²) · *Intensidade de Forma*

**Calcula:** `Σ Cofragem (m²) ÷ Área de construção (m²)`

**O que mede:** A complexidade geométrica do edifício e a coerência de escala
das quantidades extraídas face à dimensão real do projecto.

**Referência obrigatória:** A laje principal deve ter C/Area ≈ 1.00
(a sua área de cofragem deve cobrir a área do piso).

**Como interpretar:**
- C/Area (laje) muito < 1.00 → cofragem de laje provavelmente incompleta
- C/Area (vigas) alto (> 0.50) → malha reticulada muito densa (alto custo de carpintaria)
- C/Area (paredes) alto (> 0.40) → caves profundas ou grande contenção periférica
- Área usada no denominador: derivada da cofragem de laje ingerida (proxy)

---

### Índices Globais de Projecto

| Índice | Fórmula | Referência |
|---|---|---|
| **S/A** — Aço/Área | kg aço total ÷ m² área construção | ~40 kg/m² BA · ~52 kg/m² BA+PE |
| **V/A** — Betão/Área | m³ betão total ÷ m² área construção | ~0.35–0.45 m³/m² |
| **C/A** — Cofragem/Área | m² cofragem total ÷ m² área construção | depende da tipologia |

Estes índices avaliam o projecto como um todo e permitem comparar
entre fases (EP → PB → PEX) e entre projectos do histórico JSJ.
Desvios significativos face à referência justificam revisão do MQT.
    """)
```

### Posicionamento
- Deve aparecer **depois** do `st.dataframe` e **depois** da ordenação da tabela
- O `expanded=False` mantém-no fechado por defeito — o utilizador abre quando precisa
- Não duplicar na vista por zona — mostrar apenas na vista Global e por zona (é igual em ambas)

---

## ORDEM DE EXECUÇÃO

1. Aplicar Tarefa 1 completa em `validation/indices.py`
2. Verificar sem erros de sintaxe
3. Aplicar Tarefa 2 completa em `dashboard/app.py`
4. Aplicar Tarefa 3 em `dashboard/app.py`
5. Reiniciar app: `streamlit run dashboard/app.py`
6. Re-ingerir Amorim EP (Tab Gestão → apagar snapshot → Tab Ingestão → processar)
7. Verificar tab Índices: flags 🟡/🔴/🟢, coluna A/C, métricas globais, caixa explicativa
8. Se tudo OK → "bem sucedida, actualiza readme"

## NOTAS

- `apagar snapshot` antes de re-ingerir (Tab Gestão) para limpar índices antigos
- A/V do Amorim para LAJE_MACICA+BANDA+CAPITEL era 116.9 → flag esperada: 🟡 aviso (abaixo de min=90? não — 116.9 > 90 → ok) — confirmar
- PILAR Amorim era A/V=250 → flag esperada: 🟡 aviso (abaixo de min=220? não — 250 > 220 → ok, abaixo de alvo=300 mas dentro de [220,350] → 🟢 ok)
- Não alterar lógica das Tabs 1, 3, 4
