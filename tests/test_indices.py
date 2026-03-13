"""
Teste de cálculo de índices estruturais
"""
from supabase import create_client
from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from validation.indices import calcular_indices


def test_calcular_indices():
    """
    Testa cálculo de índices para snapshot existente
    Usa snapshot criado em test_ingest.py
    """
    print("\n" + "="*70)
    print("TESTE DE CÁLCULO DE ÍNDICES")
    print("="*70 + "\n")
    
    # Conectar ao Supabase
    print("🔌 Conectando ao Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("✅ Conectado\n")
    
    # Obter snapshot mais recente do projecto AMORIM_TESTE
    print("🔍 A procurar snapshot AMORIM_TESTE...")
    
    # Primeiro encontrar o projecto
    result = client.table('projects').select('id').eq('nome', 'AMORIM_TESTE').execute()
    
    if not result.data:
        print("❌ Projecto AMORIM_TESTE não encontrado")
        print("   Execute primeiro: python tests/test_ingest.py")
        return
    
    project_id = result.data[0]['id']
    
    # Obter snapshot mais recente
    result = client.table('mqt_snapshots') \
        .select('id, fase, data_upload, ficheiro_ref') \
        .eq('project_id', project_id) \
        .order('created_at', desc=True) \
        .limit(1) \
        .execute()
    
    if not result.data:
        print("❌ Nenhum snapshot encontrado para AMORIM_TESTE")
        print("   Execute primeiro: python tests/test_ingest.py")
        return
    
    snapshot = result.data[0]
    snapshot_id = snapshot['id']
    
    print(f"✅ Snapshot encontrado:")
    print(f"   • ID: {snapshot_id}")
    print(f"   • Fase: {snapshot['fase']}")
    print(f"   • Data: {snapshot['data_upload']}")
    print(f"   • Ficheiro: {snapshot['ficheiro_ref']}\n")
    
    # Calcular índices
    print("="*70)
    resultados = calcular_indices(snapshot_id, client)
    
    # Análise adicional
    print("\n" + "="*70)
    print("ANÁLISE DE RESULTADOS")
    print("="*70 + "\n")
    
    # Totais globais
    total_betao = sum(r['betao_m3'] for r in resultados)
    total_aco = sum(r['aco_kg'] for r in resultados)
    total_cofragem = sum(r['cofragem_m2'] for r in resultados)
    
    av_global = (total_aco / total_betao) if total_betao > 0 else 0
    vc_global = (total_betao / total_cofragem) if total_cofragem > 0 else 0
    
    print(f"📊 TOTAIS GLOBAIS:")
    print(f"   • Betão total:    {total_betao:10.2f} m³")
    print(f"   • Aço total:      {total_aco:10.2f} kg")
    print(f"   • Cofragem total: {total_cofragem:10.2f} m²")
    print(f"   • A/V global:     {av_global:10.2f} kg/m³")
    print(f"   • V/C global:     {vc_global:10.4f} m³/m²\n")
    
    # Elementos com índices mais altos/baixos
    elementos_com_av = [r for r in resultados if r['av'] is not None and r['av'] > 0]
    
    if elementos_com_av:
        print("🔝 TOP 3 ELEMENTOS COM MAIOR A/V (kg aço/m³ betão):")
        top_av = sorted(elementos_com_av, key=lambda x: x['av'], reverse=True)[:3]
        for i, r in enumerate(top_av, 1):
            print(f"   {i}. {r['elemento_tipo']:15s}: {r['av']:6.1f} kg/m³")
        
        print("\n🔽 TOP 3 ELEMENTOS COM MENOR A/V (kg aço/m³ betão):")
        bottom_av = sorted(elementos_com_av, key=lambda x: x['av'])[:3]
        for i, r in enumerate(bottom_av, 1):
            print(f"   {i}. {r['elemento_tipo']:15s}: {r['av']:6.1f} kg/m³")
    
    # Elementos sem betão (só cofragem/aço)
    sem_betao = [r for r in resultados if r['betao_m3'] == 0 and (r['cofragem_m2'] > 0 or r['aco_kg'] > 0)]
    if sem_betao:
        print(f"\n⚠️  ELEMENTOS SEM BETÃO (só cofragem/aço): {len(sem_betao)}")
        for r in sem_betao:
            print(f"   • {r['elemento_tipo']:15s}: cofr={r['cofragem_m2']:.1f} m², aço={r['aco_kg']:.1f} kg")
    
    # Verificar dados inseridos na DB
    print(f"\n" + "="*70)
    print("VERIFICAÇÃO NA BASE DE DADOS")
    print("="*70 + "\n")
    
    result = client.table('mqt_indices').select('*').eq('snapshot_id', snapshot_id).execute()
    
    print(f"✅ {len(result.data)} registos inseridos em mqt_indices")
    print(f"   Esperado: {len(resultados)}\n")
    
    if len(result.data) != len(resultados):
        print("⚠️  ALERTA: Número de registos diferente do esperado!")
    
    print("="*70)
    print("✅ TESTE DE ÍNDICES COMPLETO")
    print("="*70 + "\n")
    
    return resultados


if __name__ == "__main__":
    test_calcular_indices()
