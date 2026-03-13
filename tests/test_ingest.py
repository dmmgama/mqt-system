"""
Teste de integração completo: Parser + Mapper + Ingest → Supabase
"""
from datetime import date
from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from pipeline.ingest_mqt import ingest_mqt


def test_ingest_complete():
    """
    Teste completo de ingestão:
    1. Criar projecto de teste
    2. Ingerir Excel Amorim
    3. Verificar snapshot e artigos criados
    """
    print("\n" + "="*70)
    print("TESTE DE INGESTÃO COMPLETO")
    print("="*70 + "\n")
    
    # Conectar ao Supabase
    print("🔌 Conectando ao Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✅ Conectado\n")
    
    # 1. Criar projecto de teste (ou usar existente)
    print("🏢 A verificar/criar projecto de teste...")
    project_name = "AMORIM_TESTE"
    
    # Verificar se já existe
    result = client.table('projects').select('id, nome').eq('nome', project_name).execute()
    
    if result.data and len(result.data) > 0:
        project_id = result.data[0]['id']
        print(f"✅ Projecto já existe: {project_name} (ID: {project_id})\n")
    else:
        # Criar novo
        project_data = {
            'nome': project_name,
            'tipologia': 'habitacao',
            'fase_actual': 'CE',
            'data_mqt': date.today().isoformat(),
            'area_total_m2': 5000.0,
            'notas': 'Projecto de teste para validação do pipeline MQT'
        }
        result = client.table('projects').insert(project_data).execute()
        project_id = result.data[0]['id']
        print(f"✅ Projecto criado: {project_name} (ID: {project_id})\n")
    
    # 2. Executar ingestão
    print("="*70)
    snapshot_id = ingest_mqt(
        excel_path='data/samples/MQT_Amorim.xlsx',
        project_id=project_id,
        fase='CE',
        supabase_client=client
    )
    
    # 3. Verificar dados inseridos
    print("\n" + "="*70)
    print("VERIFICAÇÃO DE DADOS")
    print("="*70 + "\n")
    
    # Verificar snapshot
    print(f"📊 Snapshot ID: {snapshot_id}")
    result = client.table('mqt_snapshots').select('*').eq('id', snapshot_id).execute()
    if result.data and len(result.data) > 0:
        snapshot = result.data[0]
        print(f"   • Fase: {snapshot['fase']}")
        print(f"   • Data: {snapshot['data_upload']}")
        print(f"   • Ficheiro: {snapshot['ficheiro_ref']}")
        print(f"   • Status: {snapshot['status']}\n")
    
    # Verificar artigos
    print("📋 A verificar artigos inseridos...")
    result = client.table('mqt_artigos').select('*').eq('snapshot_id', snapshot_id).execute()
    
    num_artigos = len(result.data) if result.data else 0
    print(f"✅ Total artigos inseridos: {num_artigos}")
    print(f"   Esperado: 50 artigos\n")
    
    if num_artigos != 50:
        print(f"⚠️  ALERTA: Número de artigos diferente do esperado!")
    
    # Estatísticas por elemento_tipo
    if result.data:
        print("📊 Distribuição por elemento_tipo:")
        from collections import Counter
        elemento_counts = Counter(a['elemento_tipo'] for a in result.data)
        
        for elemento_tipo, count in sorted(elemento_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / num_artigos) * 100
            print(f"   • {elemento_tipo:15s}: {count:3d} ({pct:5.1f}%)")
    
    # Verificar alguns artigos conhecidos
    print("\n📝 Verificação de artigos específicos:")
    for artigo_cod in ['5.5.1', '5.5.4', '5.5.10', '5.5.11']:
        artigo_data = [a for a in result.data if a['artigo_cod'] == artigo_cod]
        if artigo_data:
            a = artigo_data[0]
            print(f"   • {a['artigo_cod']:8s} → {a['elemento_tipo']:15s} | {a['descricao'][:40]}")
    
    print("\n" + "="*70)
    print("✅ TESTE DE INGESTÃO COMPLETO")
    print("="*70)
    print(f"Snapshot ID: {snapshot_id}")
    print(f"Artigos inseridos: {num_artigos}")
    print(f"Status: {'✅ OK' if num_artigos == 50 else '⚠️  VERIFICAR'}")
    print("="*70 + "\n")
    
    return snapshot_id


if __name__ == "__main__":
    test_ingest_complete()
