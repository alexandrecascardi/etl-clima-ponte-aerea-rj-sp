# ==========================================
# CARGA (LOAD): INGESTÃO NO BANCO DE DADOS
# ==========================================
import sqlite3
import pandas as pd

def carregar_banco_dados(fato_voos, dim_tempo, dim_cia_aerea, dim_clima_completa):

    print("🗄️ Iniciando ingestão no banco de dados SQLite (em memória)...")
    
    # 1. Abrindo os portões do banco
    conn = sqlite3.connect(":memory:")
    
    # 2. Injetando a Tabela Fato e as Tabelas Dimensão (Star Schema Completo)
    fato_voos.to_sql("fato_voos", conn, index=False, if_exists="replace")
    dim_tempo.to_sql("dim_tempo", conn, index=False, if_exists="replace")
    dim_cia_aerea.to_sql("dim_cia_aerea", conn, index=False, if_exists="replace")
    dim_clima_completa.to_sql("dim_clima", conn, index=False, if_exists="replace")
    
    print("✅ Carga Star Schema concluída. Banco de dados pronto e blindado.")
    
    # 3. Retornamos a conexão para quem chamou (o main.py) poder rodar as queries
    return conn
