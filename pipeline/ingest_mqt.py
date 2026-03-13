"""
Script principal de ingestão de dados MQT
Orquestra o processo completo: Excel → Parser → Mapper → Supabase
"""
import argparse
import sys
from pathlib import Path
from datetime import date
from supabase import Client
from pipeline.parser_excel import parse_mqt
from pipeline.mapper_artigos import map_artigos


def ingest_mqt(excel_path: str, project_id: str, 
               fase: str, supabase_client: Client,
               emissao: str = 'E01', area_construcao: float = None) -> str:
    """
    Ingere um ficheiro Excel MQT para a base de dados Supabase
    
    Args:
        excel_path: Caminho completo para o ficheiro Excel MQT
        project_id: UUID do projecto na tabela projects
        fase: Fase do projecto - 'EP' | 'Anteprojeto' | 'CE' | 'Execucao'
        supabase_client: Cliente Supabase autenticado
        emissao: Emissão do MQT (E01, E02, etc) - default 'E01'
        area_construcao: Área de construção em m² (opcional)
        
    Returns:
        snapshot_id: UUID do snapshot criado
    """
    print(f"\n{'='*70}")
    print(f"INGESTÃO MQT → SUPABASE")
    print(f"{'='*70}\n")
    print(f"📂 Ficheiro: {excel_path}")
    print(f"🏢 Projecto ID: {project_id}")
    print(f"📋 Fase: {fase}")
    print(f"📄 Emissão: {emissao}")
    if area_construcao:
        print(f"📐 Área: {area_construcao} m²")
    print()
    
    # 1. Aceitar path string OU file-like object
    if hasattr(excel_path, 'read'):
        ficheiro_ref = getattr(excel_path, 'name', 'upload.xlsx')
    else:
        excel_file = Path(excel_path)
        if not excel_file.exists():
            raise FileNotFoundError(f"Ficheiro não encontrado: {excel_path}")
        ficheiro_ref = excel_file.name
    
    # 2. Parse do Excel MQT
    print("📖 A fazer parse do Excel...")
    parsed_data = parse_mqt(excel_path)
    artigos = parsed_data['artigos']
    parser_num_zonas = parsed_data.get('num_zonas', 1)
    print(f"✅ {len(artigos)} artigos parseados\n")
    
    # 3. Mapear artigos para elemento_tipo
    print("🗺️  A mapear artigos para elemento_tipo...")
    artigos_mapped = map_artigos(artigos, supabase_client)
    print(f"✅ {len(artigos_mapped)} artigos mapeados\n")
    
    # 4. Buscar configuração do projeto (zona_config, num_zonas)
    print("🔍 A buscar configuração do projeto...")
    project = supabase_client.table('projects')\
        .select('zona_config, num_zonas')\
        .eq('id', project_id)\
        .single()\
        .execute()
    
    zona_config = project.data.get('zona_config') or []
    zona_labels = {z['key']: z.get('label') or z.get('tipo') for z in zona_config}
    project_num_zonas = project.data.get('num_zonas', 1)
    print(f"✅ Projeto configurado com {project_num_zonas} zona(s)\n")
    
    # Validação cruzada num_zonas (warning, não erro)
    if parser_num_zonas != project_num_zonas:
        print(f"⚠️  ATENÇÃO: MQT tem {parser_num_zonas} zona(s) detectada(s) "
              f"mas o projeto está configurado com {project_num_zonas}. "
              f"Confirmar se o ficheiro está correto.\n")
    
    # 5. Verificar snapshot duplicado por (project_id, fase, emissao)
    existing = supabase_client.table('mqt_snapshots')\
        .select('id')\
        .eq('project_id', project_id)\
        .eq('fase', fase)\
        .eq('emissao', emissao)\
        .execute()
    
    if existing.data:
        print(f"⚠️  Snapshot já existe para esta fase/emissão.")
        return existing.data[0]['id']
    
    # 6. Criar snapshot
    print("💾 A criar snapshot em mqt_snapshots...")
    snapshot_data = {
        'project_id': project_id,
        'fase': fase,
        'emissao': emissao,
        'data_upload': date.today().isoformat(),
        'ficheiro_ref': ficheiro_ref,
        'area_construcao': area_construcao if area_construcao and area_construcao > 0 else None,
        'num_zonas': parser_num_zonas,
        'zona_labels': zona_labels,
        'status': 'activo'
    }
    
    result = supabase_client.table('mqt_snapshots').insert(snapshot_data).execute()
    
    if not result.data or len(result.data) == 0:
        raise Exception("Erro ao criar snapshot: nenhum ID retornado")
    
    snapshot_id = result.data[0]['id']
    print(f"✅ Snapshot criado: {snapshot_id}\n")
    
    # 7. Preparar dados para mqt_artigos (bulk insert)
    print("📝 A preparar artigos para inserção...")
    artigos_db = []
    for artigo in artigos_mapped:
        artigo_db = {
            'snapshot_id': snapshot_id,
            'capitulo': artigo.get('capitulo'),
            'subcapitulo': artigo.get('subcapitulo'),
            'artigo_cod': artigo.get('artigo_cod'),
            'sufixo': artigo.get('sufixo'),
            'elemento_sufixo': artigo.get('elemento_sufixo'),
            'descricao': artigo.get('descricao'),
            'unidade': artigo.get('unidade'),
            'classe_material': artigo.get('classe_material'),
            'elemento_tipo': artigo.get('elemento_tipo'),
            'quant_a': artigo.get('quant_a'),
            'quant_b': artigo.get('quant_b'),
            'quant_c': artigo.get('quant_c'),
            'quant_d': artigo.get('quant_d'),
            'quant_total': artigo.get('quant_total')
        }
        artigos_db.append(artigo_db)
    
    # 8. Bulk insert em mqt_artigos
    print(f"💾 A inserir {len(artigos_db)} artigos em mqt_artigos...")
    result = supabase_client.table('mqt_artigos').insert(artigos_db).execute()
    
    if not result.data:
        raise Exception("Erro ao inserir artigos: nenhum dado retornado")
    
    print(f"✅ {len(result.data)} artigos inseridos\n")
    
    print(f"{'='*70}")
    print(f"✅ INGESTÃO COMPLETA")
    print(f"{'='*70}")
    print(f"Snapshot ID: {snapshot_id}")
    print(f"Artigos: {len(result.data)}")
    print(f"{'='*70}\n")
    
    return snapshot_id


def main():
    """CLI para ingestão de MQT via linha de comando"""
    from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
    from supabase import create_client
    
    parser = argparse.ArgumentParser(description="Ingestão de ficheiros MQT para Supabase")
    parser.add_argument("--file", required=True, help="Caminho para o ficheiro Excel MQT")
    parser.add_argument("--project-id", required=True, help="UUID do projecto (FK para projects.id)")
    parser.add_argument("--fase", required=True, 
                       choices=['EP', 'Anteprojeto', 'CE', 'Execucao'],
                       help="Fase do projecto")
    
    args = parser.parse_args()
    
    # Conectar ao Supabase
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Executar ingestão
    try:
        snapshot_id = ingest_mqt(
            excel_path=args.file,
            project_id=args.project_id,
            fase=args.fase,
            supabase_client=client
        )
        print(f"\n✅ Snapshot criado com sucesso: {snapshot_id}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro durante a ingestão: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
