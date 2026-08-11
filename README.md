```
Nieuport 17
                          q*p
___________________________T____________________________
      |                 |/(_)\|                 |
      |         -------:**^^^**:-------         |
      |               ((   o   ))               |
    -----------________\\_____//________-----------  -rw
                       /       \
                    TT/         \TT
                    ||-----------||
                    ||           ||
```
*ASCII art by Christopher Johnson*

# ✈️ ETL Pipeline: Impacto Climático na Ponte Aérea (RJ-SP)

## 📌 Visão Geral

Pipeline ETL que cruza dados de voos da ANAC com histórico meteorológico para analisar o impacto de condições climáticas adversas nos cancelamentos nas operações da Ponte Aérea (Rio de Janeiro – São Paulo).

O pipeline extrai dados governamentais brutos, realiza o cruzamento com uma API meteorológica internacional e modela os dados em um Star Schema para responder a perguntas de negócio diretamente ligadas à resiliência operacional das companhias aéreas.

> **Período analisado:** Janeiro de 2024 — mês de verão e historicamente o de maior incidência de chuvas na região Sudeste.

---

## 🛠️ Tech Stack

| Camada                    | Tecnologia                     |
| ------------------------- | ------------------------------ |
| Linguagem                 | Python                         |
| Manipulação e Vetorização | Pandas, NumPy                  |
| Integração Externa        | Requests (API REST JSON)       |
| Banco de Dados            | SQLite in-memory               |
| Modelagem                 | Star Schema com Surrogate Keys |
| Arquitetura               | Pipeline Modular (`src/`)      |

---

## ⚙️ O Pipeline (ETL)

O pipeline é dividido em módulos independentes dentro de `src/`, cada um responsável por uma etapa do fluxo:

1. **Extract (`extract.py`):** Ingestão do arquivo histórico de voos (VRA) da ANAC e extração dinâmica de dados de precipitação via [Open-Meteo API](https://open-meteo.com/), consumindo as coordenadas dos aeroportos envolvidos (SBSP, SBGR, SBKP, SBRJ, SBGL).

2. **Transform (`transform.py`):** Limpeza de dados nulos, vetorização de flags binárias para cancelamentos, criação de surrogate keys e separação em dimensões isoladas (`dim_tempo`, `dim_cia_aerea`, `dim_clima`), sem atributos climáticos duplicados na tabela fato.

3. **Load (`load.py`):** Consolidação da tabela fato e das dimensões no banco relacional SQLite, com validação de integridade do cruzamento voo x clima antes da liberação do dado.

4. **Config (`config.py`) e Orquestração (`main.py`):** parâmetros de conexão, coordenadas e mapeamentos ficam centralizados em `config.py`; `main.py` executa o fluxo de ponta a ponta.

---

## 🗂️ Modelagem (Star Schema)

[![Star Schema](https://github.com/alexandrecascardi/etl-clima-ponte-aerea-rj-sp/raw/main/star_schema_digitalizado.png)](/alexandrecascardi/etl-clima-ponte-aerea-rj-sp/blob/main/star_schema_digitalizado.png)

> **Nota:** `DIM_AERONAVE` está mapeada no modelo e será implementada na próxima versão com dados simulados.

---

## 📊 Descobertas Operacionais Preliminares (Amostra de Jan/2024)

O modelo dimensional foi desenhado para estruturar o caos dos dados brutos e otimizar consultas analíticas. Com os dados de Janeiro processados, as seguintes volumetrias foram extraídas (scripts SQL disponíveis na pasta `notebooks/`):

**1. Qual companhia aérea apresentou o maior aumento de cancelamentos sob clima adverso?**

- Na amostra processada, a Azul Linhas Aéreas registrou o maior aumento comparativo: cancelamento subindo de 3,74% em dias de céu limpo para 8,50% em dias de tempestade (+4,76 pontos percentuais) — a maior variação entre as três companhias avaliadas.

**2. Qual turno demonstrou maior criticidade operacional sob chuvas fortes?**

- O período noturno (18h–05h) registrou o pico de impacto da amostra, com 14,29% de cancelamentos em condições de tempestade. Isso representa um aumento de +5,67 pontos percentuais em relação à operação desse mesmo turno em dias de céu limpo.

---

## 🚧 Roadmap

- **Big Data (Expansão Histórica):** Ingestão em lote de 12 meses contínuos de dados VRA para fornecer uma base volumosa, permitindo que times de Data Science realizem validações estatísticas de longo prazo.
- **Frotas:** A análise de impacto operacional por modelo de aeronave será desenvolvida com a integração da base RAB/ANAC em uma nova Tabela Dimensão.
- **Resiliência:** implementação de variáveis de ambiente (`.env`) e `try/except` com retries para instabilidades na API.
- **Orquestração:** substituição do SQLite local por um Cloud Data Warehouse e agendamento via Apache Airflow.

---

## 📂 Fontes de Dados

- [ANAC — VRA (Registro de Voos)](https://www.gov.br/anac/pt-br) — Janeiro de 2024
- [Open-Meteo — Historical Weather API](https://open-meteo.com/) — Janeiro de 2024

---

## ▶️ Como Executar

**1. Clone o repositório**

```
git clone https://github.com/alexandrecascardi/etl-clima-ponte-aerea-rj-sp.git
```

**2. Instale as dependências**

```
pip install pandas numpy requests
```

**3. Adicione o arquivo de dados**

Faça o download do arquivo `VRA_20241.csv` diretamente no portal da ANAC e coloque no diretório `data/`.

**4. Execute o pipeline**

```
python src/main.py
```
