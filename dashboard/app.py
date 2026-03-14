"""
MQT-SYSTEM — Dashboard Streamlit
Validação de Mapas de Quantidades (Estruturas)
"""

import streamlit as st
import pandas as pd
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from pipeline.ingest_mqt import ingest_mqt
from validation.indices import calcular_indices

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


@st.cache_resource
def init_supabase() -> Client:
    """Inicializa cliente Supabase (singleton)"""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    st.set_page_config(
        page_title="MQT System",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 MQT System — Validação de Mapas de Quantidades")
    
    client = init_supabase()
    
    # Tabs principais
    tab1, tab2, tab3, tab4 = st.tabs(["🔄 Ingestão", "📈 Índices", "📋 Artigos", "⚙️ Gestão"])
    
    # ============================================================
    # TAB 1 — INGESTÃO
    # ============================================================
    with tab1:
        st.header("Ingestão de MQT")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            ficheiro = st.file_uploader(
                "Seleccionar ficheiro MQT",
                type=["xlsx", "xls"]
            )
        
        with col2:
            project_name = st.text_input(
                "Nome do Projecto",
                placeholder="Ex: AMORIM_TESTE"
            )
        
        with col3:
            fase = st.selectbox(
                "Fase",
                options=["EP", "Anteprojeto", "CE", "Execucao"]
            )

        with col4:
            emissao = st.selectbox("Emissão", ["E01", "E02", "E03", "E04", "E05"])
            area_construcao = st.number_input(
                "Área (m²)", min_value=0.0, step=10.0,
                help="Área estrutural total. Necessária para índice C/Area."
            )
            if area_construcao == 0:
                st.caption("⚠️ Sem área — C/Area não calculado")

        # ——— Configurar Zonas ———
        st.subheader("Zonas")
        num_zonas = st.number_input("Nº de zonas", min_value=1, max_value=4, value=3, step=1)

        TIPOS_ZONA = ['Fundacoes', 'Piso_Terreo', 'Pisos_Elevados', 'Cobertura', 'Outra']
        COLS_EXCEL = ['A', 'B', 'C', 'D']
        DEFAULTS = [
            ('A - Fundações',      'Fundacoes',      'A'),
            ('B - Piso Térreo',    'Piso_Terreo',    'B'),
            ('C - Pisos Elevados', 'Pisos_Elevados', 'C'),
            ('D - Cobertura',      'Cobertura',      'D'),
        ]

        zona_config = []
        for i in range(int(num_zonas)):
            d_label, d_tipo, d_col = DEFAULTS[i] if i < len(DEFAULTS) else (f'Zona {i+1}', 'Outra', COLS_EXCEL[i])
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                label = st.text_input(f"Label zona {i+1}", value=d_label, key=f"zlabel_{i}")
            with c2:
                if int(num_zonas) == 1:
                    tipo = 'Geral'
                    st.text_input("Tipo", value='Geral', disabled=True, key=f"ztipo_{i}")
                else:
                    tipo = st.selectbox("Tipo", TIPOS_ZONA, index=TIPOS_ZONA.index(d_tipo), key=f"ztipo_{i}")
            with c3:
                col = st.text_input("Quant", value=d_col, key=f"zcol_{i}")
            zona_config.append({'idx': i, 'col': col, 'label': label, 'tipo': tipo})

        if st.button("🚀 Processar MQT", type="primary"):
            if ficheiro is None or not project_name:
                st.error("❌ Seleccione um ficheiro Excel e indique o nome do projecto")
            else:
                with st.spinner("A processar..."):
                    try:
                        # 1. Criar ou obter projecto
                        response = client.table("projects").select("id").eq("nome", project_name).execute()
                        
                        if response.data:
                            project_id = response.data[0]["id"]
                            st.info(f"ℹ️ Projecto existente: {project_name} (ID: {project_id})")
                        else:
                            insert_resp = client.table("projects").insert({
                                "nome": project_name
                            }).execute()
                            project_id = insert_resp.data[0]["id"]
                            st.success(f"✅ Projecto criado: {project_name} (ID: {project_id})")
                        
                        # 2. Ingestão
                        snapshot_id = ingest_mqt(
                            ficheiro, project_id, fase, client,
                            emissao=emissao,
                            area_construcao=area_construcao if area_construcao > 0 else None,
                            zona_config=zona_config
                        )
                        
                        # 3. Calcular índices
                        indices, indices_globais = calcular_indices(snapshot_id, client, zona_config=zona_config)
                        
                        # 4. Estatísticas
                        artigos_resp = client.table("mqt_artigos").select("elemento_tipo").eq("snapshot_id", snapshot_id).execute()
                        artigos = artigos_resp.data
                        
                        total = len(artigos)
                        outro = [a for a in artigos if a["elemento_tipo"] == "OUTRO"]
                        mapeados = total - len(outro)
                        
                        st.success(f"✅ **{total} artigos ingeridos** | {mapeados} mapeados | {len(outro)} OUTRO")
                        st.info(f"📊 **{len(indices)} índices** calculados")
                        
                        # 5. Mostrar artigos OUTRO
                        if outro:
                            st.warning(f"⚠️ **{len(outro)} artigos** precisam de revisão (mapeados como OUTRO)")
                            
                            outro_full = client.table("mqt_artigos").select("artigo_cod, descricao, capitulo, unidade").eq("snapshot_id", snapshot_id).eq("elemento_tipo", "OUTRO").execute()
                            
                            df_outro = pd.DataFrame(outro_full.data)
                            st.dataframe(df_outro, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"❌ Erro durante processamento: {str(e)}")
    
    # ============================================================
    # TAB 2 — ÍNDICES
    # ============================================================
    with tab2:
        st.header("Índices de Validação")
        
        # Selectbox projecto
        projects_resp = client.table("projects").select("id, nome").execute()
        projects = {p["nome"]: p["id"] for p in projects_resp.data}
        
        if not projects:
            st.warning("ℹ️ Nenhum projecto encontrado. Use a tab Ingestão para carregar dados.")
        else:
            selected_project = st.selectbox("Projecto", options=list(projects.keys()))
            project_id = projects[selected_project]
            
            # Selectbox snapshot
            snapshots_resp = client.table("mqt_snapshots").select("id, fase, data_upload, status").eq("project_id", project_id).order("data_upload", desc=True).execute()
            
            if not snapshots_resp.data:
                st.info("ℹ️ Nenhum snapshot encontrado para este projecto.")
            else:
                snapshot_options = {
                    f"{s['fase']} — {s['data_upload'][:10]} ({s['status']})": s["id"]
                    for s in snapshots_resp.data
                }
                
                selected_snapshot = st.selectbox("Snapshot", options=list(snapshot_options.keys()))
                snapshot_id = snapshot_options[selected_snapshot]

                # Ler zona_config do snapshot
                snap_detail = client.table('mqt_snapshots') \
                    .select('zona_config') \
                    .eq('id', snapshot_id).single().execute()
                zona_config_idx = (snap_detail.data.get('zona_config') or []) if snap_detail.data else []

                # Seletor de vista
                vista_opts = ['Global'] + [z['label'] for z in zona_config_idx]
                vista = st.selectbox("Vista", vista_opts, key="vista_indices")

                # Carregar índices filtrados por zona
                q = client.table("mqt_indices").select("*").eq("snapshot_id", snapshot_id)
                if vista == 'Global':
                    indices_resp = q.is_("zona_idx", "null").execute()
                else:
                    z_idx = next(z['idx'] for z in zona_config_idx if z['label'] == vista)
                    indices_resp = q.eq("zona_idx", z_idx).execute()
                
                if not indices_resp.data:
                    st.warning("⚠️ Nenhum índice calculado para este snapshot.")
                else:
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

                    # Eliminar elementos sem quantidades na vista actual (betao=0, aco=0, cofragem=0)
                    indices_data = [
                        r for r in indices_resp.data
                        if (r.get('betao_m3') or 0) + (r.get('aco_kg') or 0) + (r.get('cofragem_m2') or 0) > 0
                    ]
                    df = pd.DataFrame(indices_data)
                    
                    # Formatar colunas
                    df_display = df[[
                        "elemento_tipo", "betao_m3", "aco_kg", "cofragem_m2",
                        "av", "vc", "ac", "flag"
                    ]].copy()
                    
                    df_display.columns = [
                        "Elemento", "Betão m³", "Aço kg", "Cofragem m²",
                        "A/V kg/m³", "V/C m³/m²", "A/C kg/m²", "Flag"
                    ]

                    # Adicionar coluna Alvo A/V a partir de THRESHOLDS
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
                    
                    # Formatar números
                    df_display["Betão m³"] = df_display["Betão m³"].fillna(0).round(2)
                    df_display["Aço kg"] = df_display["Aço kg"].fillna(0).round(0)
                    df_display["A/V kg/m³"] = df_display["A/V kg/m³"].fillna(0).round(1)
                    df_display["Cofragem m²"] = df_display["Cofragem m²"].fillna(0).round(2)
                    df_display["V/C m³/m²"] = df_display["V/C m³/m²"].fillna(0).round(3)
                    df_display["A/C kg/m²"] = df_display["A/C kg/m²"].fillna(0).round(1)
                    df_display["Alvo A/V"] = df_display["Alvo A/V"].fillna("—")

                    # C/Area por elemento: cofragem do elemento / área de cofragem de laje da zona
                    area_ref = df["area_zona_m2"].iloc[0] if "area_zona_m2" in df.columns and not df["area_zona_m2"].isna().all() else None
                    if area_ref and area_ref > 0:
                        df_display.insert(
                            df_display.columns.get_loc("A/C kg/m²") + 1,
                            "C/Area m²/m²",
                            (df["cofragem_m2"] / area_ref).round(3)
                        )
                    
                    # Emoji por flag
                    flag_map = {"ok": "🟢", "aviso": "🟡", "erro": "🔴", "sem_dados": "⚪"}
                    df_display["Flag"] = df_display["Flag"].map(lambda x: f"{flag_map.get(x, '⚪')} {x}")

                    # Nomes de elemento legíveis
                    df_display["Elemento"] = df_display["Elemento"].map(
                        lambda x: ELEMENTO_LABELS.get(x, x.replace("_", " ").title()) if x else x
                    )

                    # Ordenar por ordem estrutural lógica
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

                    st.dataframe(df_display, use_container_width=True, hide_index=True)

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
    
    # ============================================================
    # TAB 3 — ARTIGOS
    # ============================================================
    with tab3:
        st.header("Artigos do MQT")
        
        # Reutilizar selectbox de projecto/snapshot
        projects_resp = client.table("projects").select("id, nome").execute()
        projects = {p["nome"]: p["id"] for p in projects_resp.data}
        
        if not projects:
            st.warning("ℹ️ Nenhum projecto encontrado.")
        else:
            selected_project_art = st.selectbox("Projecto", options=list(projects.keys()), key="art_project")
            project_id_art = projects[selected_project_art]
            
            snapshots_resp = client.table("mqt_snapshots").select("id, fase, data_upload").eq("project_id", project_id_art).order("data_upload", desc=True).execute()
            
            if not snapshots_resp.data:
                st.info("ℹ️ Nenhum snapshot encontrado.")
            else:
                snapshot_options_art = {
                    f"{s['fase']} — {s['data_upload'][:10]}": s["id"]
                    for s in snapshots_resp.data
                }
                
                selected_snapshot_art = st.selectbox("Snapshot", options=list(snapshot_options_art.keys()), key="art_snapshot")
                snapshot_id_art = snapshot_options_art[selected_snapshot_art]

                # Ler zona_config do snapshot para colunas dinâmicas
                _snap_art = client.table('mqt_snapshots').select('zona_config').eq('id', snapshot_id_art).single().execute()
                _zc_art = (_snap_art.data.get('zona_config') or []) if _snap_art.data else []
                # Mapear zona idx → (label, col_field)
                _COL_MAP = {'A': 'quant_a', 'B': 'quant_b', 'C': 'quant_c', 'D': 'quant_d'}
                _IDX_MAP = {0: 'quant_a', 1: 'quant_b', 2: 'quant_c', 3: 'quant_d'}
                _quant_cols = [
                    (z['label'], _COL_MAP.get(z['col'].upper(), _IDX_MAP.get(z['idx'], 'quant_a')))
                    for z in _zc_art
                ] if _zc_art else [('Total', 'quant_total')]
                
                # Filtros
                col1, col2 = st.columns(2)

                # Carregar artigos — incluir campo nivel
                artigos_resp = client.table("mqt_artigos").select(
                    "artigo_cod, descricao, unidade, elemento_tipo, capitulo, nivel, quant_a, quant_b, quant_c, quant_total"
                ).eq("snapshot_id", snapshot_id_art).order("ordem").execute()

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
                        filtro_capitulo = st.selectbox("Capítulo", ["Todos"] + caps_sorted)

                    with col2:
                        elementos = ["Todos"] + sorted([
                            e for e in df_artigos["elemento_tipo"].unique().tolist() if e is not None
                        ])
                        filtro_elemento = st.selectbox("Elemento", elementos)

                    df_filtered = df_artigos.copy()
                    if filtro_capitulo != "Todos":
                        df_filtered = df_filtered[df_filtered["capitulo"] == filtro_capitulo]
                    if filtro_elemento != "Todos":
                        df_filtered = df_filtered[df_filtered["elemento_tipo"] == filtro_elemento]

                    def _fmt_num(v):
                        if v is None:
                            return ""
                        try:
                            f = float(v)
                            if f != f:  # NaN check
                                return ""
                            if f == 0.0:
                                return ""
                            return f"{f:,.2f}".replace(",", "\u00a0")
                        except Exception:
                            return ""

                    def _row_style(nivel):
                        if nivel == 1:
                            return "background:#e8e8e8;font-weight:bold;font-size:13px;"
                        elif nivel == 2:
                            return "font-weight:bold;font-size:13px;"
                        return "font-size:12px;"

                    # Cabeçalhos dinâmicos de quantidades por zona
                    _quant_headers = "".join(
                        f"<th style='text-align:right'>{label}</th>"
                        for label, _ in _quant_cols
                    )
                    html = f"""
<style>
.mqt-table{{width:100%;border-collapse:collapse;font-family:sans-serif;}}
.mqt-table th{{background:#444;color:#fff;padding:6px 8px;text-align:left;font-size:12px;}}
.mqt-table td{{padding:4px 8px;border-bottom:1px solid #e0e0e0;vertical-align:top;}}
.mqt-table tr:hover td{{background:#f0f4ff;}}
</style>
<table class='mqt-table'><thead><tr>
<th>Código</th><th>Descrição</th><th>Un</th><th>Elemento</th>
{_quant_headers}
<th style='text-align:right'>Total</th>
</tr></thead><tbody>"""
                    for _, row in df_filtered.iterrows():
                        nivel = int(row.get("nivel") or 3)
                        style = _row_style(nivel)
                        elem_raw = row.get("elemento_tipo") or ""
                        elem_label = ELEMENTO_LABELS.get(elem_raw, elem_raw.replace("_", " ").title()) if elem_raw else ""
                        quant_cells = "".join(
                            f"<td style='{style};text-align:right'>{_fmt_num(row.get(cf))}</td>"
                            for _, cf in _quant_cols
                        )
                        html += (
                            f"<tr>"
                            f"<td style='{style}'>{row.get('artigo_cod','')}</td>"
                            f"<td style='{style}'>{row.get('descricao','') or ''}</td>"
                            f"<td style='{style}'>{row.get('unidade','') or ''}</td>"
                            f"<td style='{style}'>{elem_label}</td>"
                            f"{quant_cells}"
                            f"<td style='{style};text-align:right'>{_fmt_num(row.get('quant_total'))}</td>"
                            f"</tr>"
                        )
                    html += "</tbody></table>"
                    st.markdown(html, unsafe_allow_html=True)
                    st.caption(f"📊 {len(df_filtered)} linhas")
    
    # ============================================================
    # TAB 4 — GESTÃO
    # ============================================================
    with tab4:
        st.header("Gestão de Projectos e Snapshots")
        
        # 1. Tabela de projectos existentes
        st.subheader("📁 Projectos")
        projects_resp = client.table("projects").select("id, nome, tipologia, fase_actual, created_at").execute()
        
        if not projects_resp.data:
            st.info("ℹ️ Nenhum projecto encontrado.")
        else:
            df_projects = pd.DataFrame(projects_resp.data)
            df_projects["created_at"] = pd.to_datetime(df_projects["created_at"]).dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(df_projects, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # 2. Gestão de snapshots por projecto
            st.subheader("📸 Snapshots por Projecto")
            
            project_names = {p["nome"]: p["id"] for p in projects_resp.data}
            selected_project_name = st.selectbox("Seleccionar Projecto", options=list(project_names.keys()), key="gestao_project")
            selected_project_id = project_names[selected_project_name]
            
            # Listar snapshots do projecto
            snapshots_resp = client.table("mqt_snapshots").select("id, fase, data_upload, ficheiro_ref, status").eq("project_id", selected_project_id).order("data_upload", desc=True).execute()
            
            if not snapshots_resp.data:
                st.info(f"ℹ️ Nenhum snapshot encontrado para {selected_project_name}.")
                
                # 4. Botão apagar projecto (só se não houver snapshots)
                st.divider()
                st.warning(f"⚠️ Apagar projecto **{selected_project_name}**")
                confirm_delete_project = st.checkbox(f"Confirmar apagar projecto {selected_project_name}", key="confirm_del_proj")
                
                if st.button("🗑️ Apagar Projecto", type="secondary", disabled=not confirm_delete_project):
                    try:
                        client.table("projects").delete().eq("id", selected_project_id).execute()
                        st.success(f"✅ Projecto {selected_project_name} apagado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao apagar projecto: {str(e)}")
            else:
                df_snapshots = pd.DataFrame(snapshots_resp.data)
                st.dataframe(df_snapshots, use_container_width=True, hide_index=True)
                
                # 3. Apagar snapshot individual
                st.divider()
                st.subheader("🗑️ Apagar Snapshot")
                
                snapshot_options = {
                    f"{s['fase']} — {s['data_upload']} ({s['status']})": s["id"]
                    for s in snapshots_resp.data
                }
                
                if snapshot_options:
                    selected_snapshot_label = st.selectbox("Seleccionar Snapshot para apagar", options=list(snapshot_options.keys()), key="del_snapshot")
                    selected_snapshot_id = snapshot_options[selected_snapshot_label]
                    
                    confirm_delete = st.checkbox(f"Confirmar apagar snapshot: {selected_snapshot_label}", key="confirm_del_snap")
                    
                    if st.button("🗑️ Apagar Snapshot", type="secondary", disabled=not confirm_delete):
                        try:
                            # Ordem obrigatória (FK constraints)
                            client.table("mqt_indices").delete().eq("snapshot_id", selected_snapshot_id).execute()
                            client.table("mqt_artigos").delete().eq("snapshot_id", selected_snapshot_id).execute()
                            client.table("mqt_snapshots").delete().eq("id", selected_snapshot_id).execute()
                            
                            st.success(f"✅ Snapshot apagado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao apagar snapshot: {str(e)}")


if __name__ == "__main__":
    main()
