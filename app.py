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
# FORMATAÇÃO NO PADRÃO BRASILEIRO (R$ 32,5 bi, 32,9%, 1,92x)
# ==============================================================================
def numero_br(valor, casas, sinal=False):
    """Número com vírgula decimal e ponto de milhar; com sinal=True mostra o + na frente."""
    texto = f"{valor:+,.{casas}f}" if sinal else f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_reais(valor):
    """Valor em reais resumido: R$ 1,37 tri, R$ 32,5 bi, R$ 815,2 mi (negativo com - na frente)."""
    sinal = "-" if valor < 0 else ""
    valor = abs(valor)
    if valor >= 1e12:
        texto = numero_br(valor / 1e12, 2) + " tri"
    elif valor >= 1e9:
        texto = numero_br(valor / 1e9, 1) + " bi"
    elif valor >= 1e6:
        texto = numero_br(valor / 1e6, 1) + " mi"
    else:
        texto = numero_br(valor, 0)
    return f"{sinal}R$ {texto}"


def formatar_pct(valor):
    """Fração em porcentagem com 1 casa: 0.329 vira 32,9%."""
    if pd.isna(valor):
        return "n/d"
    return numero_br(valor * 100, 1) + "%"


def formatar_vezes(valor):
    """Indicador em vezes com 2 casas: 1,92x; vazio (EBIT negativo) vira n/d."""
    if pd.isna(valor):
        return "n/d"
    return numero_br(valor, 2) + "x"


def sem_comparacao(atual, anterior):
    """Não dá para calcular a variação sem o ano anterior."""
    return anterior is None or pd.isna(anterior) or pd.isna(atual)


def delta_pct(atual, anterior):
    """Variação em % contra o ano anterior; divide pelo valor absoluto para sair do prejuízo dar positivo."""
    if sem_comparacao(atual, anterior) or anterior == 0:
        return None
    return numero_br((atual - anterior) / abs(anterior) * 100, 1, sinal=True) + "%"


def delta_pp(atual, anterior):
    """Variação em pontos percentuais (para margens e ROE)."""
    if sem_comparacao(atual, anterior):
        return None
    return numero_br((atual - anterior) * 100, 1, sinal=True) + " p.p."


def delta_num(atual, anterior):
    """Variação simples com 2 casas (para a liquidez corrente)."""
    if sem_comparacao(atual, anterior):
        return None
    return numero_br(atual - anterior, 2, sinal=True)


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


def kpis_do_ano(dados):
    """Os 4 números da carteira num ano: soma da receita e do lucro, média simples do ROE e da liquidez."""
    if dados.empty:
        return {}
    return {
        "receita": dados["receita"].sum(),
        "lucro": dados["lucro_liquido"].sum(),
        "roe": dados["roe"].mean(),
        "liquidez": dados["liquidez_corrente"].mean(),
    }


df, origem, erro = carregar_dados()

# ==============================================================================
# FILTROS NA BARRA LATERAL (com session_state)
# ==============================================================================
GRUPOS = sorted(df["grupo"].unique().tolist())
ANOS = sorted(df["ano"].unique().tolist())


def empresas_dos_grupos(grupos):
    """Tickers das empresas que pertencem aos grupos escolhidos."""
    return sorted(df.loc[df["grupo"].isin(grupos), "ticker"].unique().tolist())


def atualizar_empresas():
    """Filtro cruzado: quando os grupos mudam, a lista de empresas passa a ter todas as desses grupos."""
    st.session_state["filtro_empresas"] = empresas_dos_grupos(st.session_state["filtro_grupos"])


def resetar_filtros():
    """Volta os filtros ao padrão: todos os grupos, todas as empresas e todos os anos."""
    st.session_state["filtro_grupos"] = GRUPOS
    st.session_state["filtro_empresas"] = empresas_dos_grupos(GRUPOS)
    st.session_state["filtro_anos"] = (ANOS[0], ANOS[-1])


# valor padrão só na primeira execução; depois o session_state guarda a escolha
st.session_state.setdefault("filtro_grupos", GRUPOS)
st.session_state.setdefault("filtro_empresas", empresas_dos_grupos(GRUPOS))

st.sidebar.header("Filtros")
grupos = st.sidebar.multiselect("Grupo de setor", GRUPOS, key="filtro_grupos", on_change=atualizar_empresas)
empresas = st.sidebar.multiselect("Empresas", empresas_dos_grupos(grupos), key="filtro_empresas")
# o select_slider só funciona como intervalo quando o value é uma tupla (por isso não usa o setdefault)
anos = st.sidebar.select_slider("Período", options=ANOS, value=(ANOS[0], ANOS[-1]), key="filtro_anos")
st.sidebar.button("🔄 Restaurar filtros", key="botao_reset", on_click=resetar_filtros, width="stretch")

# de onde vieram os dados
st.sidebar.divider()
if erro is None:
    st.sidebar.markdown(f"🟢 Dados do {origem}")
else:
    st.sidebar.markdown(f"🟡 Dados do {origem}")
    with st.sidebar.expander("Por que o CSV?"):
        st.caption(f"Não foi possível consultar o Supabase: {type(erro).__name__}")
        st.caption(str(erro)[:300])
st.sidebar.caption("Fonte: CVM - Dados Abertos (DFP 2021–2023)")

# ==============================================================================
# TOPO: TÍTULO E KPIs DA CARTEIRA FILTRADA
# ==============================================================================
st.title("🏭 WEG em números (2021–2023)")
st.caption("A empresa que mais gerou bilionários no Brasil (Forbes), comparada a 10 gigantes da bolsa")

# sem grupo ou sem empresa não há o que mostrar: avisa e para aqui
if not grupos or not empresas:
    st.warning("Selecione pelo menos um grupo e uma empresa na barra lateral.")
    st.stop()

df_filtrado = filtrar(df, grupos, empresas, anos)

# KPIs no último ano do filtro; o delta compara com o ano anterior (base completa, mesmas empresas)
ultimo_ano = anos[1]
atual = df_filtrado[df_filtrado["ano"] == ultimo_ano]
anterior = df[(df["ano"] == ultimo_ano - 1) & df["ticker"].isin(atual["ticker"])]
k_atual = kpis_do_ano(atual)
k_anterior = kpis_do_ano(anterior)

if k_anterior:
    st.markdown(f"**Carteira filtrada: {len(atual)} empresas em {ultimo_ano}**, com a variação contra {ultimo_ano - 1}")
else:
    st.markdown(f"**Carteira filtrada: {len(atual)} empresas em {ultimo_ano}** (sem ano anterior na base para comparar)")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Receita líquida total", formatar_reais(k_atual["receita"]),
            delta_pct(k_atual["receita"], k_anterior.get("receita")), border=True,
            help="Soma da receita líquida (conta 3.01) das empresas filtradas.")
col2.metric("Lucro líquido total", formatar_reais(k_atual["lucro"]),
            delta_pct(k_atual["lucro"], k_anterior.get("lucro")), border=True,
            help="Soma do lucro líquido consolidado (conta 3.11) das empresas filtradas.")
col3.metric("ROE médio", formatar_pct(k_atual["roe"]),
            delta_pp(k_atual["roe"], k_anterior.get("roe")), border=True,
            help="Média simples do ROE (lucro líquido / patrimônio líquido) entre as empresas.")
col4.metric("Liquidez corrente média", formatar_vezes(k_atual["liquidez"]),
            delta_num(k_atual["liquidez"], k_anterior.get("liquidez")), border=True,
            help="Média simples de ativo circulante / passivo circulante. Abaixo de 1,5x é alerta.")

st.dataframe(df_filtrado, width="stretch")
st.caption(f"{len(df_filtrado)} linhas carregadas")
