# ==========================================
#  CONFIGURAÇÕES E CONSTANTES
# ==========================================

# Caminho do arquivo bruto da ANAC (CSV)
CAMINHO_VRA = "data/VRA_20241.csv"

# Definição de alvos operacionais (Aeroportos)
AEROPORTOS_SP = ["SBSP", "SBGR", "SBKP"]  # Congonhas, Guarulhos, Viracopos
AEROPORTOS_RJ = ["SBRJ", "SBGL"]          # Santos Dumont, Galeão

# Tríade Comercial (Companhias Aéreas)
FROTA_ALVO = ["GLO", "TAM", "AZU"]

# Mapa de tradução (Códigos ICAO para Nomes Comerciais)
MAPA_COMPANHIAS = {
    "GLO": "Gol Linhas Aéreas",
    "TAM": "LATAM Airlines",
    "AZU": "Azul Linhas Aéreas",
}

# ==========================================
# PARÂMETROS DA API DE CLIMA (OPEN-METEO)
# ==========================================
URL_API_CLIMA = "https://archive-api.open-meteo.com/v1/archive"

# São Paulo (Congonhas como epicentro)
PARAMS_API_SP = {
    "latitude": -23.62,
    "longitude": -46.65,
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "hourly": "precipitation",
    "timezone": "America/Sao_Paulo",
}

# Rio de Janeiro (Galeão como epicentro)
PARAMS_API_RJ = {
    "latitude": -22.81,
    "longitude": -43.25,
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "hourly": "precipitation",
    "timezone": "America/Sao_Paulo",
}
