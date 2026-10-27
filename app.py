"""
WEG em números: análise fundamentalista 2021–2023 (Projeto Final do Módulo 2 - SCTEC).

Painel que compara a WEG com 10 grandes empresas da bolsa a partir dos
demonstrativos financeiros (DFP) da CVM.

Como rodar (a partir da pasta do projeto):
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# configuração da página
st.set_page_config(
    page_title="WEG em números",
    page_icon="🏭",
    layout="wide",
)

PASTA_GOLD = Path(__file__).resolve().parent / "data" / "gold"

# medidas da tabela fato (valores em R$ e indicadores)
COLUNAS_NUMERICAS = ["receita", "lucro_bruto", "ebit", "lucro_liquido", "ativo_circulante", "passivo_circulante",
                     "patrimonio_liquido", "caixa", "aplicacoes", "emprestimos", "arrendamentos", "divida_liquida",
                     "margem_bruta", "margem_ebit", "margem_liquida", "roe", "liquidez_corrente", "alavancagem"]
COLUNAS = ["ticker", "nome", "setor", "grupo", "ano"] + COLUNAS_NUMERICAS + ["alerta_liquidez", "alerta_divida"]

# esquema estrela: a fato com os JOINs nas duas dimensões
CONSULTA_SQL = """
SELECT e.ticker, e.nome, e.setor, e.grupo, t.ano,
       f.receita, f.lucro_bruto, f.ebit, f.lucro_liquido, f.ativo_circulante, f.passivo_circulante,
       f.patrimonio_liquido, f.caixa, f.aplicacoes, f.emprestimos, f.arrendamentos, f.divida_liquida,
       f.margem_bruta, f.margem_ebit, f.margem_liquida, f.roe, f.liquidez_corrente, f.alavancagem,
       f.alerta_liquidez, f.alerta_divida
FROM fato_indicadores f
JOIN dim_empresa e ON e.empresa_sk = f.empresa_sk
JOIN dim_tempo t ON t.tempo_sk = f.tempo_sk
ORDER BY e.ticker, t.ano
"""


# ==============================================================================
# CONEXÃO COM O SUPABASE E PLANO B NO CSV
# ==============================================================================
@st.cache_resource  # abre a conexão uma vez só e reaproveita
def obter_conexao():
    """Conexão com o Supabase; os dados ficam no .streamlit/secrets.toml (fora do git)."""
    return st.connection("postgresql", type="sql")


@st.cache_data(ttl=600, show_spinner="Consultando o Supabase...")  # guarda o resultado por 10 minutos
def consultar_supabase():
    """Busca os dados no banco; se der erro, o Streamlit não guarda o erro no cache."""
    df = obter_conexao().query(CONSULTA_SQL, ttl=600)
    if df is None or df.empty:
        raise ValueError("A consulta ao Supabase voltou vazia.")
    # o PostgreSQL devolve NUMERIC como Decimal; aqui vira número de verdade
    for coluna in COLUNAS_NUMERICAS:
        df[coluna] = pd.to_numeric(df[coluna])
    return df


@st.cache_data  # os CSVs não mudam enquanto o app roda
def ler_csv_local():
    """Plano B: junta os 3 CSVs da camada Gold no mesmo formato da consulta."""
    empresas = pd.read_csv(PASTA_GOLD / "dim_empresa.csv")
    tempo = pd.read_csv(PASTA_GOLD / "dim_tempo.csv")
    fato = pd.read_csv(PASTA_GOLD / "fato_indicadores.csv")
    df = fato.merge(empresas, on="empresa_sk").merge(tempo, on="tempo_sk")
    return df[COLUNAS].sort_values(["ticker", "ano"]).reset_index(drop=True)


def carregar_dados():
    """Tenta o Supabase; se falhar, usa o CSV local e devolve o erro para mostrar na barra lateral."""
    try:
        return consultar_supabase(), "Supabase (PostgreSQL)", None
    except Exception as erro:
        return ler_csv_local(), "CSV local (data/gold)", erro


def filtrar(df, grupos, empresas, anos):
    """Aplica os filtros da barra lateral: grupos, empresas e intervalo de anos."""
    filtro = df["grupo"].isin(grupos) & df["ticker"].isin(empresas) & df["ano"].between(anos[0], anos[1])
    return df[filtro]


df, origem, erro = carregar_dados()

# ==============================================================================
# FILTROS NA BARRA LATERAL (com session_state)
# ==============================================================================
GRUPOS = sorted(df["grupo"].unique().tolist())
EMPRESAS = sorted(df["ticker"].unique().tolist())
ANOS = sorted(df["ano"].unique().tolist())

# valor padrão só na primeira execução; depois o session_state guarda a escolha
st.session_state.setdefault("filtro_grupos", GRUPOS)
st.session_state.setdefault("filtro_empresas", EMPRESAS)

st.sidebar.header("Filtros")
grupos = st.sidebar.multiselect("Grupo de setor", GRUPOS, key="filtro_grupos")
empresas = st.sidebar.multiselect("Empresas", EMPRESAS, key="filtro_empresas")
# o select_slider só funciona como intervalo quando o value é uma tupla (por isso não usa o setdefault)
anos = st.sidebar.select_slider("Período", options=ANOS, value=(ANOS[0], ANOS[-1]), key="filtro_anos")

# de onde vieram os dados
st.sidebar.divider()
if erro is None:
    st.sidebar.markdown(f"🟢 Dados do {origem}")
else:
    st.sidebar.markdown(f"🟡 Dados do {origem}")
    with st.sidebar.expander("Por que o CSV?"):
        st.caption(f"Não foi possível consultar o Supabase: {type(erro).__name__}")
        st.caption(str(erro)[:300])

df_filtrado = filtrar(df, grupos, empresas, anos)

st.dataframe(df_filtrado, width="stretch")
st.caption(f"{len(df_filtrado)} linhas carregadas")
