"""
Script principal de ingestão de dados MQT
Orquestra o processo completo: Excel → Parser → Mapper → Supabase
"""
import argparse
import sys
from pathlib import Path
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from pipeline.parser_excel import parse_mqt_excel
from pipeline.mapper_artigos import map_artigo_to_elemento


def ingest_mqt_file(excel_path: str, project_id: str, fase: str = "Projecto", 
                    entrega: str = "Final", notas: str = ""):
    """
    Ingere um ficheiro Excel MQT para a base de dados Supabase
    
    Args:
        excel_path: Caminho completo para o ficheiro Excel MQT
        project_id: ID do projecto na tabela projects (SSOT)
        fase: Fase do projecto (ex: "Projecto", "Obra")
        entrega: Tipo de entrega (ex: "Final", "Preliminar", "Revisão")
        notas: Notas adicionais sobre este snapshot
    """
    print(f"📊 Iniciando ingestão de MQT...")
    print(f"   Ficheiro: {excel_path}")
    print(f"   Projecto ID: {project_id}")
    
    # 1. Verificar se o ficheiro existe
    if not Path(excel_path).exists():
        print(f"❌ Ficheiro não encontrado: {excel_path}")
        sys.exit(1)
    
    # 2. Conectar ao Supabase
    print("🔌 A conectar ao Supabase...")
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # 3. Parse do Excel
    print("📖 A fazer parse do Excel MQT...")
    # TODO: Implementar parse_mqt_excel
    # df_artigos = parse_mqt_excel(excel_path)
    
    # 4. Criar snapshot
    print("💾 A criar snapshot...")
    # TODO: Inserir na tabela mqt_snapshots
    
    # 5. Mapear e inserir artigos
    print("🗺️  A mapear e inserir artigos...")
    # TODO: Para cada artigo, mapear elemento_tipo e inserir em mqt_artigos
    
    # 6. Calcular índices
    print("📐 A calcular índices...")
    # TODO: Chamar validation.indices
    
    print("✅ Ingestão completa!")


def main():
    parser = argparse.ArgumentParser(description="Ingestão de ficheiros MQT para Supabase")
    parser.add_argument("--file", required=True, help="Caminho para o ficheiro Excel MQT")
    parser.add_argument("--project-id", required=True, help="ID do projecto (FK para projects.id)")
    parser.add_argument("--fase", default="Projecto", help="Fase do projecto")
    parser.add_argument("--entrega", default="Final", help="Tipo de entrega")
    parser.add_argument("--notas", default="", help="Notas sobre este snapshot")
    
    args = parser.parse_args()
    
    ingest_mqt_file(
        excel_path=args.file,
        project_id=args.project_id,
        fase=args.fase,
        entrega=args.entrega,
        notas=args.notas
    )


if __name__ == "__main__":
    main()
