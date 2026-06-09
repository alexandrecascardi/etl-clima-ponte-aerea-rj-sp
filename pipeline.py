import pandas as pd
import numpy as np
import requests
import sqlite3

# ==========================================
# NOTA DE AMBIENTE: Ajuste o caminho abaixo para o diretório local onde o arquivo VRA da ANAC está salvo.
# Exemplo: 'data/VRA_20241.csv'
# ==========================================
caminho = 'VRA_20241.csv' 
df_vra = pd.read_csv(caminho, sep=";", skiprows=1)

# Delimitação do escopo para a rota da Ponte Aérea (SP-RJ / RJ-SP)
aero_sp = ["SBSP", "SBGR", "SBKP"]
aero_rj = ["SBRJ", "SBGL"]

rota_sp_rj = df_vra["ICAO Aeródromo Origem"].isin(aero_sp) & df_vra["ICAO Aeródromo Destino"].isin(aero_rj)
rota_rj_sp = df_vra["ICAO Aeródromo Origem"].isin(aero_rj) & df_vra["ICAO Aeródromo Destino"].isin(aero_sp)

# Utilização do .copy() para evitar alertas de SettingWithCopy ao fatiar o DataFrame
df_voos = df_vra[rota_sp_rj | rota_rj_sp].copy()

# Criação de flag binária: 1 para cancelado, 0 para normal (vetorização com np.where para otimização de performance)
df_voos["FLAG_CANCELADO"] = np.where(df_voos["Situação Voo"] == "CANCELADO", 1, 0)

# Filtragem restrita às principais companhias aéreas comerciais do país
df_voos = df_voos[df_voos["ICAO Empresa Aérea"].isin(["GLO", "TAM", "AZU"])].copy()

# Criação da dimensão de companhias aéreas com surrogate key (ID numérico) para otimização de merges
dim_cia = df_voos[["ICAO Empresa Aérea"]].drop_duplicates()
mapa_cias = {
    "GLO": "Gol Linhas Aéreas",
    "TAM": "LATAM Airlines",
    "AZU": "Azul Linhas Aéreas",
}
dim_cia["Nome"] = dim_cia["ICAO Empresa Aérea"].map(mapa_cias)
dim_cia = dim_cia.reset_index(drop=True)
dim_cia["ID_CIA_AEREA"] = dim_cia.index + 1

# Criação da dimensão de tempo com base na data de partida prevista
dim_tempo = df_voos[["Partida Prevista"]].drop_duplicates().reset_index(drop=True)
dim_tempo = dim_tempo.rename(columns={"Partida Prevista": "DATA_BASE"})
dim_tempo["DATA_BASE"] = pd.to_datetime(dim_tempo["DATA_BASE"])
dim_tempo["ANO"] = dim_tempo["DATA_BASE"].dt.year
dim_tempo["MES"] = dim_tempo["DATA_BASE"].dt.month
dim_tempo["HORA"] = dim_tempo["DATA_BASE"].dt.hour
dim_tempo["ID_TEMPO"] = dim_tempo.index + 1

# Integração das chaves dimensionais na tabela fato
df_voos = pd.merge(df_voos, dim_cia[["ICAO Empresa Aérea", "ID_CIA_AEREA"]], on="ICAO Empresa Aérea", how="left")

df_voos["Partida Prevista"] = pd.to_datetime(df_voos["Partida Prevista"])
df_voos = pd.merge(df_voos, dim_tempo[["DATA_BASE", "ID_TEMPO"]], left_on="Partida Prevista", right_on="DATA_BASE", how="left")

# Remoção de colunas redundantes para otimização de memória
cols_drop = [
    "DATA_BASE", "ICAO Empresa Aérea", "Situação Voo", "Código Justificativa", 
    "Partida Real", "Chegada Real", "Chegada Prevista", "Código Autorização (DI)", "Código Tipo Linha"
]
df_voos = df_voos.drop(columns=cols_drop, errors="ignore")


# Definição das regras de negócio para classificação do volume de precipitação (mm)
def classificar_clima(mm):
    if mm == 0.0: return "Céu Limpo", "Nula"
    elif mm <= 5.0: return "Chuva", "Leve"
    elif mm <= 20.0: return "Chuva", "Moderada"
    else: return "Tempestade", "Severa"

def deduzir_visibilidade(intensidade):
    if intensidade == "Nula": return "Boa"
    elif intensidade in ["Leve", "Moderada"]: return "Reduzida"
    else: return "Crítica"

# Função para extração de dados climáticos via API Open-Meteo
def get_clima(lat, lon, siglas):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": "2024-01-01", "end_date": "2024-01-31",
        "hourly": "precipitation", "timezone": "America/Sao_Paulo"
    }
    res = requests.get(url, params=params)
    
    if res.status_code == 200:
        dados = res.json()
        df_tmp = pd.DataFrame({
            "DATA_HORA": dados["hourly"]["time"], 
            "CHUVA_MM": dados["hourly"]["precipitation"]
        })
        df_tmp["DATA_HORA"] = pd.to_datetime(df_tmp["DATA_HORA"])
        df_tmp["DATA_BASE"] = df_tmp["DATA_HORA"].dt.normalize()
        
        # Agregação da precipitação por dia (granularidade horária é possível, mas agregamos por dia por ora)
        df_clima = df_tmp.groupby("DATA_BASE").agg(TOTAL_CHUVA_MM=("CHUVA_MM", "sum")).reset_index()
        
        df_clima[["CONDICAO", "INTENSIDADE"]] = df_clima.apply(lambda r: pd.Series(classificar_clima(r["TOTAL_CHUVA_MM"])), axis=1)
        df_clima["VISIBILIDADE"] = df_clima["INTENSIDADE"].apply(deduzir_visibilidade)
        
        # Replicação geográfica para aeroportos da mesma região, evitando valores nulos (NaN) no merge
        dfs = []
        for sigla in siglas:
            df_aux = df_clima.copy()
            df_aux["ICAO Aeródromo Origem"] = sigla
            dfs.append(df_aux)
            
        return pd.concat(dfs, ignore_index=True)
    else:
        print(f"Erro na comunicação com a API para os terminais {siglas}: {res.status_code}")
        return pd.DataFrame()

# Execução da extração climática para os terminais de SP e RJ
clima_rj = get_clima(-22.81, -43.25, ["SBGL", "SBRJ"])
clima_sp = get_clima(-23.62, -46.65, ["SBSP", "SBGR", "SBKP"])

dim_clima = pd.concat([clima_rj, clima_sp], ignore_index=True)

# Ajuste temporário da granularidade da data para cruzamento com o histórico climático diário
df_voos["DATA_TMP"] = df_voos["Partida Prevista"].dt.normalize()

df_final = pd.merge(
    df_voos, dim_clima,
    left_on=["DATA_TMP", "ICAO Aeródromo Origem"],
    right_on=["DATA_BASE", "ICAO Aeródromo Origem"],
    how="left"
)

df_final = df_final.drop(columns=["DATA_TMP", "Partida Prevista"])

# ====================
# Análises de Negócio e Geração de Métricas
# ====================

# 1. Análise de impacto climático por companhia aérea
clima_ruim = ['Chuva', 'Tempestade']
df_clima_ruim = df_final[df_final['CONDICAO'].isin(clima_ruim)].copy()

resp_1 = df_clima_ruim.groupby('ID_CIA_AEREA').agg(
    VOOS_TOTAL=('FLAG_CANCELADO', 'count'),
    CANCELADOS=('FLAG_CANCELADO', 'sum')
).reset_index()

resp_1['PCT_CANCELAMENTO'] = round((resp_1['CANCELADOS'] / resp_1['VOOS_TOTAL']) * 100, 2)
resp_1 = pd.merge(resp_1, dim_cia[['ID_CIA_AEREA', 'Nome']], on='ID_CIA_AEREA', how='left')

print("\n--- Ranking de Cancelamentos sob Condições Climáticas Adversas ---")
print(resp_1.sort_values(by='PCT_CANCELAMENTO', ascending=False).to_string(index=False))


# 2. Análise de impacto por turno (simulação de consulta SQL em ambiente de banco de dados relacional)
conn = sqlite3.connect(":memory:")
df_final.to_sql("fato_voos", conn, index=False, if_exists="replace")
dim_tempo.to_sql("dim_tempo", conn, index=False, if_exists="replace")

query = """
    SELECT 
        CASE 
            WHEN t.HORA >= 18 OR t.HORA <= 5 THEN 'Noturno (18h-05h)'
            ELSE 'Diurno (06h-17h)'
        END AS TURNO,
        COUNT(f."Número Voo") AS TOTAL_VOOS,
        SUM(f.FLAG_CANCELADO) AS CANCELADOS,
        ROUND((CAST(SUM(f.FLAG_CANCELADO) AS FLOAT) / COUNT(f."Número Voo")) * 100, 2) AS PCT_CANCELAMENTO
    FROM fato_voos f
    INNER JOIN dim_tempo t ON f.ID_TEMPO = t.ID_TEMPO
    GROUP BY TURNO;
"""
resp_3 = pd.read_sql_query(query, conn)
print("\n--- Impacto Operacional: Turno Diurno vs Noturno ---")
print(resp_3.to_string(index=False))


# ==========================================
# Exportação do artefato consolidado (Load)
# Ajuste o diretório de saída conforme seu ambiente local
# ==========================================
caminho_exportacao = 'fato_voos_clima.csv'
df_final.to_csv(caminho_exportacao, index=False, sep=';', encoding='utf-8')
print(f"\n✅ Pipeline concluído com sucesso! Arquivo exportado para: {caminho_exportacao}")