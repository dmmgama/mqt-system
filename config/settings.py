"""
Configuração do MQT-System
Carrega variáveis de ambiente do ficheiro .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
MQT_EXCEL_PATH = os.getenv("MQT_EXCEL_PATH")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("Credenciais Supabase em falta no .env")

# Configurações opcionais
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
