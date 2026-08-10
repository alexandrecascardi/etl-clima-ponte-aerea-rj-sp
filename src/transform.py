# ==============================================
# TRANSFORMAÇÃO: ISOLAMENTO, MÉTRICAS E TRÍADE
# ==============================================
import pandas as pd
import numpy as np
import config

def limpar_e_filtrar_voos(df_vra_bruto):
    
    # 1. Sensores de rota (SP <-> RJ) puxando os aeroportos do config
    rota_sp_rj = df_vra_bruto["ICAO Aeródromo Origem"].isin(config.AEROPORTOS_SP) & df_vra_bruto["ICAO Aeródromo Destino"].isin(config.AEROPORTOS_RJ)
    rota_rj_sp = df_vra_bruto["ICAO Aeródromo Origem"].isin(config.AEROPORTOS_RJ) & df_vra_bruto["ICAO Aeródromo Destino"].isin(config.AEROPORTOS_SP)
    
    df_voos = df_vra_bruto[rota_sp_rj | rota_rj_sp].copy()

    # 2. Flag binária de cancelamento (Vetorizada)
    df_voos["FLAG_CANCELADO"] = np.where(df_voos["Situação Voo"] == "CANCELADO", 1, 0)

    # 3. Filtragem da Tríade Comercial puxando do config
    df_voos = df_voos[df_voos["ICAO Empresa Aérea"].isin(config.FROTA_ALVO)].copy()
    
    return df_voos


def criar_dimensoes_voos(df_voos):
    # ==========================================
    # MODELAGEM: DIMENSÕES CIA AÉREA E TEMPO
    # ==========================================
    
    # --- DIMENSÃO CIA AÉREA ---
    dim_cia_aerea = df_voos[["ICAO Empresa Aérea"]].drop_duplicates()
    dim_cia_aerea["Companhia Nome"] = dim_cia_aerea["ICAO Empresa Aérea"].map(config.MAPA_COMPANHIAS)
    dim_cia_aerea = dim_cia_aerea.reset_index(drop=True)
    dim_cia_aerea["ID_CIA_AEREA"] = dim_cia_aerea.index + 1

    # --- DIMENSÃO TEMPO ---
    dim_tempo = df_voos[["Partida Prevista"]].drop_duplicates().reset_index(drop=True)
    dim_tempo = dim_tempo.rename(columns={"Partida Prevista": "DATA_BASE"})
    dim_tempo["DATA_BASE"] = pd.to_datetime(dim_tempo["DATA_BASE"])
    dim_tempo["ANO"] = dim_tempo["DATA_BASE"].dt.year
    dim_tempo["MES"] = dim_tempo["DATA_BASE"].dt.month
    dim_tempo["DIA_SEMANA"] = dim_tempo["DATA_BASE"].dt.dayofweek
    dim_tempo["HORA"] = dim_tempo["DATA_BASE"].dt.hour
    dim_tempo["ID_TEMPO"] = dim_tempo.index + 1

    return dim_cia_aerea, dim_tempo


def processar_clima(df_clima_bruto, siglas_aeroportos):
    # ==========================================
    # REGRAS DE NEGÓCIO E AGRUPAMENTO
    # ==========================================
    
    # Agrupando e somando o volume de chuva por dia
    dim_clima_base = df_clima_bruto.groupby("DATA_BASE").agg(TOTAL_CHUVA_DIA_MM=("CHUVA_MM", "sum")).reset_index()

    def classificar_clima(mm):
        if mm == 0.0: return "Céu Limpo", "Nula"
        elif mm <= 5.0: return "Chuva", "Leve"
        elif mm <= 20.0: return "Chuva", "Moderada"
        else: return "Tempestade", "Severa"

    def deduzir_visibilidade(intensidade):
        if intensidade == "Nula": return "Boa"
        elif intensidade in ["Leve", "Moderada"]: return "Reduzida"
        else: return "Crítica"

    # Aplicando as regras
    dim_clima_base[["CONDICAO", "INTENSIDADE"]] = dim_clima_base.apply(lambda row: pd.Series(classificar_clima(row["TOTAL_CHUVA_DIA_MM"])), axis=1)
    dim_clima_base["VISIBILIDADE"] = dim_clima_base["INTENSIDADE"].apply(deduzir_visibilidade)

    # Duplicando o clima para cobrir os aeroportos da região
    dfs_expandidos = []
    for icao in siglas_aeroportos:
        df_temp = dim_clima_base.copy()
        df_temp["ICAO Aeródromo Origem"] = icao
        dfs_expandidos.append(df_temp)
        
    dim_clima_final = pd.concat(dfs_expandidos, ignore_index=True)
    return dim_clima_final


def forjar_tabela_fato(df_voos, dim_cia_aerea, dim_tempo, dim_clima_rj, dim_clima_sp):
    # ==========================================
    # O GRANDE MERGE DEFINITIVO
    # ==========================================
    
    # 1. Cruzando Fato com Cia Aérea e Tempo
    fato = pd.merge(df_voos, dim_cia_aerea[["ICAO Empresa Aérea", "ID_CIA_AEREA"]], on="ICAO Empresa Aérea", how="left")
    fato["Partida Prevista"] = pd.to_datetime(fato["Partida Prevista"])
    fato = pd.merge(fato, dim_tempo[["DATA_BASE", "ID_TEMPO"]], left_on="Partida Prevista", right_on="DATA_BASE", how="left")
    
    # 2. Empilhamento e Surrogate Key do Clima (SP + RJ)
    dim_clima_completa = pd.concat([dim_clima_rj, dim_clima_sp], ignore_index=True).reset_index(drop=True)
    dim_clima_completa["ID_CLIMA"] = dim_clima_completa.index + 1

    # 3. O Cruzamento Final do Clima
    fato["DATA_MATCH_TMP"] = fato["Partida Prevista"].dt.normalize()
    fato = pd.merge(fato, dim_clima_completa, left_on=["DATA_MATCH_TMP", "ICAO Aeródromo Origem"], right_on=["DATA_BASE", "ICAO Aeródromo Origem"], how="left")

    # 4. Faxina: Removendo colunas desnecessárias
    colunas_para_dropar = [
        "DATA_BASE_x", "DATA_BASE_y", "ICAO Empresa Aérea", "Situação Voo", 
        "Código Justificativa", "Partida Real", "Chegada Real", "Chegada Prevista", 
        "Código Autorização (DI)", "Código Tipo Linha", "DATA_MATCH_TMP", "Partida Prevista"
    ]
    fato = fato.drop(columns=colunas_para_dropar, errors="ignore")
    
    return fato, dim_clima_completa
