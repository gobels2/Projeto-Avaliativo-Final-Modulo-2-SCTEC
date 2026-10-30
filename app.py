"""
WEG em números: análise fundamentalista 2021–2023 (Projeto Final do Módulo 2 - SCTEC).

Painel que compara a WEG com 10 grandes empresas da bolsa a partir dos
demonstrativos financeiros (DFP) da CVM.

Como rodar (a partir da pasta do projeto):
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# configuração da página
st.set_page_config(
    page_title="WEG em números",
    page_icon="🏭",
    layout="wide",
)

PASTA_GOLD = Path(__file__).resolve().parent / "data" / "gold"

# cores do painel: a WEG em azul, as outras em cinza e o vermelho só para alerta
COR_WEG = "#00579D"
COR_OUTRAS = "#8794A6"
COR_ALERTA = "#C0392B"
CORES_ANOS = ["#8DB9E4", "#4A87C9", "#00579D"]  # do ano mais antigo (claro) ao mais recente (escuro)

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


# guarda também a decisão por 10 minutos: com o banco fora do ar, o app não tenta de novo a cada clique
@st.cache_data(ttl=600, show_spinner=False)
def carregar_dados():
    """Tenta o Supabase; se falhar, usa o CSV local e devolve o tipo do erro para mostrar na barra lateral."""
    try:
        return consultar_supabase(), "Supabase (PostgreSQL)", None
    except Exception as erro:
        # a mensagem completa tem o endereço do banco: vai só para o log, não para a tela
        print(f"Supabase falhou: {erro}")
        return ler_csv_local(), "CSV local (data/gold)", type(erro).__name__


def filtrar(df, grupos, empresas, anos):
    """Aplica os filtros da barra lateral: grupos, empresas e intervalo de anos."""
    filtro = df["grupo"].isin(grupos) & df["ticker"].isin(empresas) & df["ano"].between(anos[0], anos[1])
    return df[filtro]


def cores_empresas(tickers):
    """WEG em azul e as demais em cinza (a cor segue a empresa, não a posição no gráfico)."""
    return {ticker: COR_WEG if ticker == "WEGE3" else COR_OUTRAS for ticker in tickers}


def texto_piramide(contexto, insight, acao):
    """Texto curto que abre cada aba, na ordem da pirâmide invertida: contexto, insight e ação."""
    texto = f"**Contexto:** {contexto}\n\n**Insight:** {insight}\n\n**Ação:** {acao}"
    # \$ para o markdown não ler o R$ como fórmula
    st.info(texto.replace("$", "\\$"))


def ajustar_layout(fig):
    """Padrão de todos os gráficos: fundo branco, números em português e legenda sem título."""
    fig.update_layout(template="plotly_white", separators=",.", legend_title_text="",
                      margin=dict(t=60, l=10, r=10, b=10))
    return fig


def motivo_alerta(linha):
    """Explica por que a empresa entrou em alerta na pergunta 4."""
    motivos = []
    if linha["alerta_liquidez"]:
        motivos.append("liquidez abaixo de 1,5x")
    if linha["alerta_divida"]:
        if linha["ebit"] <= 0:
            motivos.append("EBIT negativo com dívida")
        else:
            motivos.append("dívida acima de 3x o EBIT")
    return "; ".join(motivos)


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
        st.caption("Não foi possível consultar o Supabase. O app tenta de novo em 10 minutos.")
        st.caption(f"Tipo do erro: {erro}")
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

# ==============================================================================
# ABAS
# ==============================================================================
aba_weg, aba_crescimento, aba_rentabilidade, aba_solvencia, aba_dados = st.tabs(
    ["🏭 WEG em foco", "📈 Crescimento", "💰 Rentabilidade", "🛡️ Solvência", "📋 Dados"]
)

# --- Aba 1: a WEG aparece sempre, mesmo desmarcada; os filtros mudam só com quem ela é comparada
with aba_weg:
    weg = df[(df["ticker"] == "WEGE3") & df["ano"].between(anos[0], anos[1])]
    w = weg[weg["ano"] == ultimo_ano].iloc[0]
    weg_anterior = df[(df["ticker"] == "WEGE3") & (df["ano"] == ultimo_ano - 1)]
    w_ant = weg_anterior.iloc[0] if not weg_anterior.empty else {}

    st.subheader(f"WEG em {ultimo_ano}")
    w_ini = weg[weg["ano"] == anos[0]].iloc[0]
    fatia = w["receita"] / df.loc[df["ano"] == ultimo_ano, "receita"].sum()
    contexto = (f"Em {ultimo_ano}, a WEG teve receita de {formatar_reais(w['receita'])}, "
                f"{formatar_pct(fatia)} da receita somada das 11 empresas do painel.")
    if anos[0] < ultimo_ano:
        insight = (f"De {anos[0]} a {ultimo_ano}, a receita da WEG variou {delta_pct(w['receita'], w_ini['receita'])} "
                   f"e o lucro líquido {delta_pct(w['lucro_liquido'], w_ini['lucro_liquido'])}; a margem líquida "
                   f"foi de {formatar_pct(w_ini['margem_liquida'])} para {formatar_pct(w['margem_liquida'])}.")
    else:
        insight = (f"Em {ultimo_ano}, a margem líquida da WEG foi de {formatar_pct(w['margem_liquida'])} "
                   f"e o ROE de {formatar_pct(w['roe'])}.")
    acao = ("Para o investidor de longo prazo: acompanhar, a cada novo balanço, se a margem líquida se mantém "
            f"e se o caixa continua maior que a dívida (dívida líquida de {formatar_reais(w['divida_liquida'])} "
            f"em {ultimo_ano}; negativa quer dizer mais caixa que dívida).")
    texto_piramide(contexto, insight, acao)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita da WEG", formatar_reais(w["receita"]),
              delta_pct(w["receita"], w_ant.get("receita")), border=True)
    c2.metric("Lucro líquido da WEG", formatar_reais(w["lucro_liquido"]),
              delta_pct(w["lucro_liquido"], w_ant.get("lucro_liquido")), border=True)
    c3.metric("Margem líquida da WEG", formatar_pct(w["margem_liquida"]),
              delta_pp(w["margem_liquida"], w_ant.get("margem_liquida")), border=True)
    c4.metric("ROE da WEG", formatar_pct(w["roe"]),
              delta_pp(w["roe"], w_ant.get("roe")), border=True)

    graf1, graf2 = st.columns(2)

    # gráfico 1: receita e lucro da WEG por ano (mesma unidade, um eixo só)
    barras = weg.melt(id_vars="ano", value_vars=["receita", "lucro_liquido"], var_name="indicador", value_name="valor")
    barras["indicador"] = barras["indicador"].map({"receita": "Receita líquida", "lucro_liquido": "Lucro líquido"})
    barras["valor_bi"] = barras["valor"] / 1e9
    barras["rotulo"] = barras["valor"].apply(formatar_reais)
    barras["ano"] = barras["ano"].astype(str)
    fig = px.bar(barras, x="ano", y="valor_bi", color="indicador", barmode="group", text="rotulo",
                 color_discrete_map={"Receita líquida": COR_WEG, "Lucro líquido": "#4A87C9"},
                 title="Receita e lucro líquido da WEG por ano",
                 labels={"ano": "Ano", "valor_bi": "R$ bilhões", "indicador": ""})
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{text}<extra></extra>")
    graf1.plotly_chart(ajustar_layout(fig), width="stretch")

    # gráfico 2: margem líquida da WEG contra a mediana das outras empresas selecionadas
    linhas = weg[["ano", "margem_liquida"]].assign(serie="WEG")
    outras = df_filtrado[df_filtrado["ticker"] != "WEGE3"]
    if not outras.empty:
        mediana = outras.groupby("ano", as_index=False)["margem_liquida"].median()
        linhas = pd.concat([linhas, mediana.assign(serie="Mediana das outras selecionadas")])
    linhas["margem_pct"] = linhas["margem_liquida"] * 100
    linhas["ano"] = linhas["ano"].astype(str)
    fig = px.line(linhas, x="ano", y="margem_pct", color="serie", markers=True,
                  color_discrete_map={"WEG": COR_WEG, "Mediana das outras selecionadas": COR_OUTRAS},
                  title="Margem líquida: WEG contra a mediana das outras",
                  labels={"ano": "Ano", "margem_pct": "Margem líquida (%)", "serie": ""})
    fig.update_traces(line_width=2, marker_size=9,
                      hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:.1f}%<extra></extra>")
    graf2.plotly_chart(ajustar_layout(fig), width="stretch")

with aba_crescimento:
    st.subheader("Quem cresceu e quem encolheu")

    # crescimento da receita do primeiro ao último ano do filtro, por empresa
    receita_ano = df_filtrado.pivot_table(index="ticker", columns="ano", values="receita")
    crescimento = pd.DataFrame()
    if anos[0] < ultimo_ano:
        crescimento = (receita_ano[ultimo_ano] / receita_ano[anos[0]] - 1).rename("variacao").reset_index()
        crescimento = crescimento.sort_values("variacao")
        maior = crescimento.iloc[-1]
        menor = crescimento.iloc[0]
        variacao_maior = numero_br(maior["variacao"] * 100, 1, sinal=True) + "%"
        variacao_menor = numero_br(menor["variacao"] * 100, 1, sinal=True) + "%"
        if maior["ticker"] == menor["ticker"]:
            insight = f"De {anos[0]} a {ultimo_ano}, a receita da {maior['ticker']} variou {variacao_maior}."
        else:
            # o artigo e a palavra mudam quando até a primeira do ranking encolheu
            topo = "o maior crescimento" if maior["variacao"] >= 0 else "a menor queda"
            fundo = "a maior queda" if menor["variacao"] < 0 else "o menor crescimento"
            insight = (f"De {anos[0]} a {ultimo_ano}, {topo} da receita foi da {maior['ticker']} ({variacao_maior}) "
                       f"e {fundo} foi da {menor['ticker']} ({variacao_menor}).")
        # crescimento da receita somada de cada grupo, do maior para o menor
        receita_grupo = df_filtrado.pivot_table(index="grupo", columns="ano", values="receita", aggfunc="sum")
        por_grupo = (receita_grupo[ultimo_ano] / receita_grupo[anos[0]] - 1).sort_values(ascending=False)
        lista = ", ".join(f"{grupo} {numero_br(v * 100, 1, sinal=True)}%" for grupo, v in por_grupo.items())
        insight += f" Somando a receita por grupo: {lista}."
    else:
        insight = "Com um ano só não dá para medir crescimento: escolha pelo menos dois anos no filtro de período."
    total = df_filtrado.loc[df_filtrado["ano"] == ultimo_ano, "receita"].sum()
    contexto = (f"Receita líquida das {df_filtrado['ticker'].nunique()} empresas selecionadas: "
                f"{formatar_reais(total)} em {ultimo_ano}.")
    acao = ("Antes de concluir, olhar o crescimento junto com a margem (aba Rentabilidade): crescer a receita "
            "com margem menor não é o mesmo que crescer com lucro.")
    texto_piramide(contexto, insight, acao)

    # gráfico 3: receita por empresa e ano, com a WEG primeiro no eixo
    ordem = ["WEGE3"] + sorted(t for t in df_filtrado["ticker"].unique() if t != "WEGE3")
    barras = df_filtrado.assign(receita_bi=df_filtrado["receita"] / 1e9, ano_texto=df_filtrado["ano"].astype(str))
    barras["rotulo"] = barras["receita"].apply(formatar_reais)
    anos_texto = [str(a) for a in ANOS]
    fig = px.bar(barras, x="ticker", y="receita_bi", color="ano_texto", barmode="group",
                 category_orders={"ticker": [t for t in ordem if t in set(barras["ticker"])], "ano_texto": anos_texto},
                 color_discrete_map=dict(zip(anos_texto, CORES_ANOS)), custom_data=["nome", "rotulo"],
                 title="Receita líquida por empresa e ano",
                 labels={"ticker": "Empresa", "receita_bi": "R$ bilhões", "ano_texto": "Ano"})
    fig.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>%{fullData.name}: %{customdata[1]}<extra></extra>")
    st.plotly_chart(ajustar_layout(fig), width="stretch")

    graf1, graf2 = st.columns(2)

    # gráfico 4: ranking do crescimento (WEG em azul, queda em vermelho)
    with graf1:
        if crescimento.empty:
            st.info("Escolha pelo menos dois anos para ver o crescimento.")
        else:
            crescimento["variacao_pct"] = crescimento["variacao"] * 100
            crescimento["rotulo"] = crescimento["variacao_pct"].apply(lambda v: numero_br(v, 1, sinal=True) + "%")
            crescimento["situacao"] = "Cresceu"
            crescimento.loc[crescimento["variacao"] < 0, "situacao"] = "Encolheu"
            crescimento.loc[crescimento["ticker"] == "WEGE3", "situacao"] = "WEG"
            fig = px.bar(crescimento, x="variacao_pct", y="ticker", orientation="h", color="situacao", text="rotulo",
                         color_discrete_map={"WEG": COR_WEG, "Cresceu": COR_OUTRAS, "Encolheu": COR_ALERTA},
                         category_orders={"ticker": crescimento["ticker"].tolist()},
                         title=f"Crescimento da receita de {anos[0]} a {ultimo_ano}",
                         labels={"variacao_pct": "Variação da receita (%)", "ticker": "Empresa", "situacao": ""})
            fig.update_traces(textposition="outside", cliponaxis=False,
                              hovertemplate="<b>%{y}</b>: %{text}<extra></extra>")
            st.plotly_chart(ajustar_layout(fig), width="stretch")

    # gráfico 5: de onde vem a receita do último ano (grupo > setor > empresa)
    with graf2:
        mapa = df_filtrado[df_filtrado["ano"] == ultimo_ano].copy()
        mapa["receita_bi"] = mapa["receita"] / 1e9
        mapa["destaque"] = "Outras"
        mapa.loc[mapa["ticker"] == "WEGE3", "destaque"] = "WEG"
        fig = px.treemap(mapa, path=["grupo", "setor", "ticker"], values="receita_bi", color="destaque",
                         color_discrete_map={"WEG": COR_WEG, "Outras": COR_OUTRAS, "(?)": "#C9D1DC"},
                         title=f"Receita de {ultimo_ano} por grupo, setor e empresa")
        fig.update_traces(texttemplate="%{label}<br>R$ %{value:,.1f} bi<br>%{percentRoot:.1%}",
                          hovertemplate="<b>%{label}</b><br>R$ %{value:,.1f} bi (%{percentRoot:.1%} do total)<extra></extra>")
        st.plotly_chart(ajustar_layout(fig), width="stretch")

with aba_rentabilidade:
    st.subheader(f"Margem e retorno em {ultimo_ano}")

    ranking = atual.sort_values("roe", ascending=False).reset_index(drop=True)
    primeira = ranking.iloc[0]
    mediana_roe = ranking["roe"].median()
    mediana_margem = ranking["margem_liquida"].median()
    insight = (f"Em {ultimo_ano}, o maior ROE foi da {primeira['ticker']} ({formatar_pct(primeira['roe'])}); "
               f"a mediana das {len(ranking)} empresas selecionadas foi {formatar_pct(mediana_roe)}.")
    if "WEGE3" in set(ranking["ticker"]):
        posicao = ranking.index[ranking["ticker"] == "WEGE3"][0] + 1
        roe_weg = ranking.loc[ranking["ticker"] == "WEGE3", "roe"].iloc[0]
        insight += f" A WEG ficou em {posicao}º lugar, com ROE de {formatar_pct(roe_weg)}."
    contexto = ("O ROE mostra quanto lucro a empresa gerou para cada real dos sócios; a margem líquida, "
                "quanto de cada real vendido virou lucro.")
    acao = ("Para o investidor: comparar cada empresa com a mediana (linhas tracejadas), e não com a média, "
            "que é puxada pelos casos extremos. Quem fica acima e à direita das duas linhas junta margem e retorno altos.")
    texto_piramide(contexto, insight, acao)

    graf1, graf2 = st.columns(2)

    # gráfico 6: quadrantes margem líquida x ROE, bolha do tamanho da receita
    with graf1:
        pontos = atual.assign(margem_pct=atual["margem_liquida"] * 100, roe_pct=atual["roe"] * 100,
                              rotulo=atual["receita"].apply(formatar_reais))
        pontos["destaque"] = "Outras"
        pontos.loc[pontos["ticker"] == "WEGE3", "destaque"] = "WEG"
        fig = px.scatter(pontos, x="margem_pct", y="roe_pct", size="receita", text="ticker", color="destaque",
                         color_discrete_map={"WEG": COR_WEG, "Outras": COR_OUTRAS}, size_max=45,
                         custom_data=["nome", "rotulo"],
                         title=f"Margem líquida x ROE em {ultimo_ano} (bolha = receita)",
                         labels={"margem_pct": "Margem líquida (%)", "roe_pct": "ROE (%)", "destaque": ""})
        fig.update_traces(textposition="top center",
                          hovertemplate="<b>%{customdata[0]}</b><br>Margem líquida: %{x:.1f}%<br>"
                                        "ROE: %{y:.1f}%<br>Receita: %{customdata[1]}<extra></extra>")
        fig.add_vline(x=mediana_margem * 100, line_dash="dash", line_color=COR_OUTRAS,
                      annotation_text="mediana da margem", annotation_position="bottom right")
        fig.add_hline(y=mediana_roe * 100, line_dash="dash", line_color=COR_OUTRAS,
                      annotation_text="mediana do ROE", annotation_position="right")
        # folga em cima e embaixo para o nome da bolha mais alta não ser cortado
        fig.update_yaxes(range=[pontos["roe_pct"].min() - 8, pontos["roe_pct"].max() + 8])
        st.plotly_chart(ajustar_layout(fig), width="stretch")

    # gráfico 7: margem EBIT por grupo em todos os anos do filtro (pontos da WEG em azul)
    with graf2:
        caixas = df_filtrado.assign(margem_ebit_pct=df_filtrado["margem_ebit"] * 100)
        fig = px.box(caixas, x="grupo", y="margem_ebit_pct", points="all", hover_data=["ticker", "ano"],
                     category_orders={"grupo": GRUPOS}, color_discrete_sequence=[COR_OUTRAS],
                     title=f"Margem EBIT por grupo ({anos[0]} a {ultimo_ano})",
                     labels={"grupo": "Grupo", "margem_ebit_pct": "Margem EBIT (%)"})
        fig.update_traces(name="Todas as empresas", showlegend=True)
        weg_caixas = caixas[caixas["ticker"] == "WEGE3"]
        if not weg_caixas.empty:
            fig.add_scatter(x=weg_caixas["grupo"], y=weg_caixas["margem_ebit_pct"], mode="markers", name="WEG",
                            marker=dict(color=COR_WEG, size=10, line=dict(color="white", width=2)),
                            customdata=weg_caixas["ano"],
                            hovertemplate="<b>WEG</b> %{customdata}: %{y:.1f}%<extra></extra>")
        st.plotly_chart(ajustar_layout(fig), width="stretch")

with aba_solvencia:
    st.subheader(f"Liquidez e dívida em {ultimo_ano}")

    em_alerta = atual[atual["alerta_liquidez"] | atual["alerta_divida"]].sort_values("ticker")
    liquidez_baixa = atual.loc[atual["alerta_liquidez"], "ticker"].tolist()
    divida_alta = atual.loc[atual["alerta_divida"], "ticker"].tolist()
    contexto = ("Liquidez corrente: quanto a empresa tem no curto prazo para cada real que deve no curto prazo. "
                "Alavancagem: quantos anos de EBIT pagariam a dívida líquida.")
    insight = (f"Em {ultimo_ano}, {len(liquidez_baixa)} empresa(s) ficaram abaixo de 1,5x de liquidez "
               f"({', '.join(liquidez_baixa) or 'nenhuma'}) e {len(divida_alta)} passaram de 3x de alavancagem "
               f"ou tinham EBIT negativo com dívida ({', '.join(divida_alta) or 'nenhuma'}).")
    acao = ("Para o gestor financeiro e o investidor: olhar os dois alertas juntos antes de investir ou conceder "
            "crédito. Liquidez baixa com caixa maior que a dívida (dívida líquida negativa) pesa menos que liquidez "
            "baixa com dívida alta.")
    texto_piramide(contexto, insight, acao)

    solv = atual.copy()
    solv["situacao"] = "Sem alerta"
    SITUACOES = ["WEG", "Sem alerta", "Em alerta"]  # mesma ordem de legenda nos dois gráficos
    graf1, graf2 = st.columns(2)

    # gráfico 8: liquidez corrente com a linha de corte em 1,5x
    with graf1:
        liq = solv.sort_values("liquidez_corrente", ascending=False)
        liq.loc[liq["alerta_liquidez"], "situacao"] = "Em alerta"
        liq.loc[liq["ticker"] == "WEGE3", "situacao"] = "WEG"
        liq["rotulo"] = liq["liquidez_corrente"].apply(formatar_vezes)
        fig = px.bar(liq, x="ticker", y="liquidez_corrente", color="situacao", text="rotulo",
                     color_discrete_map={"WEG": COR_WEG, "Sem alerta": COR_OUTRAS, "Em alerta": COR_ALERTA},
                     category_orders={"ticker": liq["ticker"].tolist(), "situacao": SITUACOES},
                     title=f"Liquidez corrente em {ultimo_ano}",
                     labels={"ticker": "Empresa", "liquidez_corrente": "Liquidez corrente (x)", "situacao": ""})
        fig.update_traces(textposition="outside", cliponaxis=False,
                          hovertemplate="<b>%{x}</b>: %{text}<extra></extra>")
        fig.add_hline(y=1.5, line_dash="dash", line_color=COR_ALERTA,
                      annotation_text="1,5x", annotation_position="top right")
        st.plotly_chart(ajustar_layout(fig), width="stretch")

    # gráfico 9: dívida líquida em R$ bi (negativa = caixa líquido), com a alavancagem escrita na barra
    with graf2:
        div = solv.sort_values("divida_liquida", ascending=False)
        div.loc[div["alerta_divida"], "situacao"] = "Em alerta"
        div.loc[div["ticker"] == "WEGE3", "situacao"] = "WEG"
        div["divida_bi"] = div["divida_liquida"] / 1e9
        div["rotulo"] = div["alavancagem"].apply(formatar_vezes)
        div["valor"] = div["divida_liquida"].apply(formatar_reais)
        fig = px.bar(div, x="ticker", y="divida_bi", color="situacao", text="rotulo", custom_data=["valor"],
                     color_discrete_map={"WEG": COR_WEG, "Sem alerta": COR_OUTRAS, "Em alerta": COR_ALERTA},
                     category_orders={"ticker": div["ticker"].tolist(), "situacao": SITUACOES},
                     title=f"Dívida líquida em {ultimo_ano} (texto = dívida líquida / EBIT)",
                     labels={"ticker": "Empresa", "divida_bi": "Dívida líquida (R$ bilhões)", "situacao": ""})
        fig.update_traces(textposition="outside", cliponaxis=False,
                          hovertemplate="<b>%{x}</b><br>Dívida líquida: %{customdata[0]}<br>"
                                        "Alavancagem: %{text}<extra></extra>")
        st.plotly_chart(ajustar_layout(fig), width="stretch")

    # tabela das empresas em alerta (pergunta 4)
    st.markdown(f"**Empresas em alerta em {ultimo_ano}**")
    if em_alerta.empty:
        st.success("Nenhuma empresa em alerta no período.")
    else:
        tabela_alerta = pd.DataFrame({
            "ticker": em_alerta["ticker"],
            "liquidez_corrente": em_alerta["liquidez_corrente"].apply(formatar_vezes),
            "alavancagem": em_alerta["alavancagem"].apply(formatar_vezes),
            "motivo": em_alerta.apply(motivo_alerta, axis=1),
        })
        st.dataframe(tabela_alerta, width="stretch", hide_index=True)

with aba_dados:
    st.subheader("Dados filtrados")

    # na tela: reais em bilhões e margens/ROE em %; o download leva os números completos
    colunas_reais = COLUNAS_NUMERICAS[:12]
    colunas_pct = ["margem_bruta", "margem_ebit", "margem_liquida", "roe"]
    tabela = df_filtrado.copy()
    tabela[colunas_reais] = (tabela[colunas_reais] / 1e9).round(2)
    tabela[colunas_pct] = (tabela[colunas_pct] * 100).round(1)
    tabela[["liquidez_corrente", "alavancagem"]] = tabela[["liquidez_corrente", "alavancagem"]].round(2)

    configuracao = {"ano": st.column_config.NumberColumn("ano", format="%d")}
    for coluna in colunas_reais:
        configuracao[coluna] = st.column_config.NumberColumn(f"{coluna} (R$ bi)", format="localized")
    for coluna in colunas_pct:
        configuracao[coluna] = st.column_config.NumberColumn(f"{coluna} (%)", format="localized")
    for coluna in ["liquidez_corrente", "alavancagem"]:
        configuracao[coluna] = st.column_config.NumberColumn(f"{coluna} (x)", format="localized")

    st.dataframe(tabela, width="stretch", hide_index=True, column_config=configuracao)
    st.caption(f"{len(tabela)} linhas, uma por empresa e ano. Alavancagem vazia = EBIT zero ou negativo.")

    # CSV com ; e vírgula decimal, para abrir direto no Excel em português
    csv = df_filtrado.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button("📥 Baixar dados filtrados (CSV)", data=csv,
                       file_name="weg_em_numeros_filtrado.csv", mime="text/csv")

    with st.expander("📖 Dicionário de dados"):
        st.markdown("""
| Coluna | O que é |
|---|---|
| receita | receita líquida de vendas e serviços (conta 3.01 da DRE) |
| lucro_bruto | receita menos o custo do que foi vendido (3.03) |
| ebit | resultado antes do resultado financeiro e dos impostos (3.05) |
| lucro_liquido | lucro líquido consolidado, com a parte dos minoritários (3.11) |
| ativo_circulante / passivo_circulante | o que vira dinheiro / o que vence em até 12 meses (1.01 / 2.01) |
| patrimonio_liquido | patrimônio líquido consolidado no fim do ano (2.03) |
| caixa / aplicacoes | caixa e equivalentes (1.01.01) / aplicações financeiras (1.01.02) |
| emprestimos / arrendamentos | empréstimos de curto + longo prazo (2.01.04 + 2.02.01) / arrendamentos (2.01.04.03 + 2.02.01.03) |
| divida_liquida | empréstimos - arrendamentos - caixa - aplicações; negativa = mais caixa que dívida |
| margem_bruta / margem_ebit / margem_liquida | lucro bruto / EBIT / lucro líquido divididos pela receita |
| roe | lucro líquido / patrimônio líquido |
| liquidez_corrente | ativo circulante / passivo circulante |
| alavancagem | dívida líquida / EBIT; vazia quando o EBIT é zero ou negativo |
| alerta_liquidez / alerta_divida | liquidez abaixo de 1,5x / alavancagem acima de 3x, ou EBIT negativo com dívida |

O dicionário completo, com os tipos de cada coluna, está no README do repositório.
""")

    with st.expander("⚠️ Limitações dos dados"):
        # r antes das aspas: o \$ impede que o markdown leia o R$ como fórmula
        st.markdown(r"""
- O lucro é o **consolidado** (inclui os minoritários). As notícias costumam usar o lucro dos controladores
  (WEG 2023: R\$ 5,87 bi consolidado contra R\$ 5,73 bi dos controladores).
- O EBIT da CVM (conta 3.05) inclui a equivalência patrimonial (pesa na Vale, na Petrobras e na Engie).
- A alavancagem usa o EBIT e não o EBITDA, porque a depreciação não vem nos três arquivos usados.
  Com o EBIT o número fica um pouco maior, ou seja, mais conservador.
- A dívida líquida não conta derivativos nem arrendamentos. As empresas às vezes contam,
  então o número pode ser diferente do release.
- A receita da Renner inclui cerca de R\$ 2,0 bi de serviços financeiros, e o lucro da Vale em 2021 e 2022
  inclui operações descontinuadas.
- O Itaú (ITUB4) ficou de fora: banco usa outro plano de contas e os indicadores não se comparam.
- São três anos e onze empresas: os números mostram o que aconteceu, não explicam por que aconteceu.
""")
