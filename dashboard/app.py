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
                            area_construcao=area_construcao if area_construcao > 0 else None
                        )
                        
                        # 3. Calcular índices
                        indices = calcular_indices(snapshot_id, client)
                        
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
                
                # Carregar índices
                indices_resp = client.table("mqt_indices").select("*").eq("snapshot_id", snapshot_id).execute()
                
                if not indices_resp.data:
                    st.warning("⚠️ Nenhum índice calculado para este snapshot.")
                else:
                    df = pd.DataFrame(indices_resp.data)
                    
                    # Formatar colunas
                    df_display = df[[
                        "elemento_tipo", "betao_m3", "aco_kg", "av",
                        "cofragem_m2", "vc", "flag"
                    ]].copy()
                    
                    df_display.columns = [
                        "Elemento", "Betão m³", "Aço kg", "A/V kg/m³",
                        "Cofragem m²", "V/C m³/m²", "Flag"
                    ]
                    
                    # Formatar números
                    df_display["Betão m³"] = df_display["Betão m³"].fillna(0).round(2)
                    df_display["Aço kg"] = df_display["Aço kg"].fillna(0).round(0)
                    df_display["A/V kg/m³"] = df_display["A/V kg/m³"].fillna(0).round(1)
                    df_display["Cofragem m²"] = df_display["Cofragem m²"].fillna(0).round(2)
                    df_display["V/C m³/m²"] = df_display["V/C m³/m²"].fillna(0).round(3)
                    
                    # Emoji por flag
                    flag_map = {"ok": "🟢", "alerta": "🟡", "erro": "🔴"}
                    df_display["Flag"] = df_display["Flag"].map(lambda x: f"{flag_map.get(x, '⚪')} {x}")
                    
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
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
                
                # Filtros
                col1, col2 = st.columns(2)
                
                # Carregar artigos
                artigos_resp = client.table("mqt_artigos").select(
                    "artigo_cod, descricao, unidade, elemento_tipo, capitulo, quant_a, quant_b, quant_c, quant_total"
                ).eq("snapshot_id", snapshot_id_art).execute()
                
                if not artigos_resp.data:
                    st.warning("⚠️ Nenhum artigo encontrado.")
                else:
                    df_artigos = pd.DataFrame(artigos_resp.data)
                    
                    with col1:
                        capitulos = ["Todos"] + sorted([c for c in df_artigos["capitulo"].unique().tolist() if c is not None])
                        filtro_capitulo = st.selectbox("Capítulo", capitulos)
                    
                    with col2:
                        elementos = ["Todos"] + sorted([e for e in df_artigos["elemento_tipo"].unique().tolist() if e is not None])
                        filtro_elemento = st.selectbox("Elemento", elementos)
                    
                    # Aplicar filtros
                    df_filtered = df_artigos.copy()
                    if filtro_capitulo != "Todos":
                        df_filtered = df_filtered[df_filtered["capitulo"] == filtro_capitulo]
                    if filtro_elemento != "Todos":
                        df_filtered = df_filtered[df_filtered["elemento_tipo"] == filtro_elemento]
                    
                    # Renomear colunas
                    df_filtered.columns = [
                        "Código", "Descrição", "Unidade", "Elemento", "Capítulo",
                        "Quant A", "Quant B", "Quant C", "Total"
                    ]
                    
                    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
                    st.caption(f"📊 {len(df_filtered)} artigos")
    
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
