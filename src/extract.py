# ==========================================
# EXTRAÇÃO / INGESTÃO DE DADOS (ETL)
# ==========================================
import pandas as pd
import requests
import config

def extrair_dados_vra():

    print("📥 Iniciando extração dos dados da ANAC...")

    # Extração isolada mapeando a variável (config)
    df_vra_bruto = pd.read_csv(config.CAMINHO_VRA, sep=";", skiprows=1)

    print(f"✅ Extração VRA concluída: {df_vra_bruto.shape[0]} registros encontrados.")
    return df_vra_bruto


def extrair_dados_clima(parametros, nome_regiao):
    # ==========================================
    # INGESTÃO: CLIMA VIA API OPEN-METEO
    # ==========================================

    # 1. Fazendo o disparo e transferindo os dados da API
    print(f"🌦️ Fazendo o disparo para a API de {nome_regiao}...")
    resposta = requests.get(config.URL_API_CLIMA, params=parametros)

    if resposta.status_code == 200:
        dados_clima = resposta.json()
        tempos = dados_clima["hourly"]["time"]
        chuva = dados_clima["hourly"]["precipitation"]

        # 2. Estruturando a tabela bruta com os dados por hora
        df_clima_bruto = pd.DataFrame({"DATA_HORA_API": tempos, "CHUVA_MM": chuva})
        df_clima_bruto["DATA_HORA_API"] = pd.to_datetime(
            df_clima_bruto["DATA_HORA_API"]
        )
        df_clima_bruto["DATA_BASE"] = df_clima_bruto[
            "DATA_HORA_API"
        ].dt.normalize()

        print(f"✅ Clima de {nome_regiao} extraído com sucesso.")
        return df_clima_bruto
    else:
        print(f"❌ Erro na API de {nome_regiao}: Status {resposta.status_code}")
        return None
