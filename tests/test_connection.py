"""
Teste de ligação ao Supabase
Verifica se as credenciais estão correctas e se as tabelas MQT existem
"""
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def test_connection():
    """Testa ligação básica ao Supabase"""
    print("🔌 A testar ligação ao Supabase...")
    print(f"   URL: {SUPABASE_URL}")
    
    try:
        client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("   ✅ Cliente Supabase criado com sucesso")
    except Exception as e:
        print(f"   ❌ Erro ao criar cliente: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Testar acesso às tabelas MQT
    print("\n📊 A verificar tabelas MQT...")
    
    tabelas_mqt = [
        "mqt_snapshots",
        "mqt_artigos",
        "mqt_indices",
        "elemento_map",
        "capitulo_map",
        "jsj_precos_ref"
    ]
    
    for tabela in tabelas_mqt:
        try:
            result = client.table(tabela).select("*").limit(1).execute()
            print(f"   ✅ {tabela}: OK ({len(result.data)} registos)")
        except Exception as e:
            print(f"   ❌ {tabela}: ERRO - {e}")
            print(f"      → A tabela pode não existir. Executar database/schema_mqt_d04.sql no Supabase SQL Editor")
    
    # Testar acesso às tabelas SSOT (só leitura)
    print("\n📚 A verificar tabelas SSOT (só leitura)...")
    
    tabelas_ssot = ["projects", "blocks", "floors", "zones"]
    
    for tabela in tabelas_ssot:
        try:
            result = client.table(tabela).select("id").limit(1).execute()
            print(f"   ✅ {tabela}: OK (acesso de leitura)")
        except Exception as e:
            print(f"   ⚠️  {tabela}: {e}")
    
    print("\n✅ Teste de ligação completo!")
    return True


if __name__ == "__main__":
    test_connection()
