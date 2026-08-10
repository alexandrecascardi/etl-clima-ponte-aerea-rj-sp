# ==========================================
# ORQUESTRAÇÃO: PIPELINE PRINCIPAL (MAIN)
# ==========================================
import config
import extract
import transform
import load
import pandas as pd

def orquestrar_pipeline():
  
    print("🚀 INICIANDO OPERAÇÃO: PIPELINE PONTE AÉREA")
    print("="*50)
    
    # ==========================================
    # 1. EXTRAÇÃO
    # ==========================================
    df_vra_bruto = extract.extrair_dados_vra()
    df_clima_rj_bruto = extract.extrair_dados_clima(config.PARAMS_API_RJ, "Rio de Janeiro")
    df_clima_sp_bruto = extract.extrair_dados_clima(config.PARAMS_API_SP, "São Paulo")
    
    if df_clima_rj_bruto is None or df_clima_sp_bruto is None:
        print("❌ Falha crítica na extração das APIs. Abortando missão.")
        return None

    print("="*50)
    
    # ==========================================
    # 2. TRANSFORMAÇÃO E MODELAGEM
    # ==========================================
    print("⚙️ Iniciando Transformação e Modelagem Star Schema...")
    df_voos_limpo = transform.limpar_e_filtrar_voos(df_vra_bruto)
    dim_cia_aerea, dim_tempo = transform.criar_dimensoes_voos(df_voos_limpo)
    
    dim_clima_rj = transform.processar_clima(df_clima_rj_bruto, config.AEROPORTOS_RJ)
    dim_clima_sp = transform.processar_clima(df_clima_sp_bruto, config.AEROPORTOS_SP)
    
    fato_voos, dim_clima_completa = transform.forjar_tabela_fato(
        df_voos_limpo, dim_cia_aerea, dim_tempo, dim_clima_rj, dim_clima_sp
    )
    print("✅ Transformação concluída. Tabela Fato forjada (Limpa de redundâncias).")

    print("="*50)
    
    # ==========================================
    # 3. INGESTÃO (LOAD)
    # ==========================================
    conn = load.carregar_banco_dados(fato_voos, dim_tempo, dim_cia_aerea, dim_clima_completa)
    
    print("="*50)
    
    # ==========================================
    # 4. VALIDAÇÃO TÁTICA
    # ==========================================
    print("📊 Validando a Integridade no Banco de Dados:")
    query_teste = """
        SELECT 
            COALESCE(c.CONDICAO, '⚠️ ALERTA: SEM DADOS DE CLIMA') AS CONDICAO_CLIMATICA,
            COUNT(f.FLAG_CANCELADO) AS TOTAL_VOOS,
            SUM(f.FLAG_CANCELADO) AS CANCELADOS
        FROM fato_voos f
        LEFT JOIN dim_clima c ON f.ID_CLIMA = c.ID_CLIMA
        GROUP BY 1
    """
    df_teste = pd.read_sql_query(query_teste, conn)
    print(df_teste)
    
    print("="*50)
    print("🎯 MISSÃO CUMPRIDA! O Pipeline rodou com sucesso.")
    
    return conn

# Gatilho de execução principal
if __name__ == "__main__":
    conn_final = orquestrar_pipeline()
