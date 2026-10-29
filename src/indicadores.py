"""
Indicadores financeiros da camada Gold, calculados a partir das contas da CVM.

As fórmulas estão explicadas no README, na seção "Dicionário de dados".
"""

# corte de liquidez do enunciado (pergunta 4): abaixo de 1,5x a empresa entra em alerta
LIMITE_LIQUIDEZ = 1.5

# régua usual de mercado para dívida líquida / EBIT: acima de 3x a dívida é alta
LIMITE_ALAVANCAGEM = 3.0


def calcular_indicadores(contas):
    """Recebe uma linha por empresa-ano com as colunas de CONTAS e devolve uma cópia com os indicadores."""
    df = contas.copy()

    # empréstimos de curto + longo prazo; arrendamento que não existe conta como zero
    df["emprestimos"] = df["emprestimos_cp"] + df["emprestimos_lp"]
    df["arrendamentos"] = df["arrendamentos_cp"].fillna(0) + df["arrendamentos_lp"].fillna(0)

    # dívida líquida sem arrendamentos (IFRS 16): Petrobras e Vale lançam dentro de empréstimos, as outras não
    df["divida_liquida"] = df["emprestimos"] - df["arrendamentos"] - df["caixa"] - df["aplicacoes"]

    # margens: quanto de cada real de receita sobra em cada etapa
    df["margem_bruta"] = df["lucro_bruto"] / df["receita"]
    df["margem_ebit"] = df["ebit"] / df["receita"]
    df["margem_liquida"] = df["lucro_liquido"] / df["receita"]

    # ROE com o patrimônio líquido do fim do ano
    df["roe"] = df["lucro_liquido"] / df["patrimonio_liquido"]
    df["liquidez_corrente"] = df["ativo_circulante"] / df["passivo_circulante"]

    # dívida líquida / EBIT só faz sentido com EBIT positivo; com EBIT zero ou negativo fica vazio
    df["alavancagem"] = df["divida_liquida"] / df["ebit"]
    df.loc[df["ebit"] <= 0, "alavancagem"] = None

    # pergunta 4: alerta quando a liquidez é baixa ou a dívida é alta
    df["alerta_liquidez"] = df["liquidez_corrente"] < LIMITE_LIQUIDEZ
    divida_alta = df["alavancagem"] > LIMITE_ALAVANCAGEM
    ebit_negativo_com_divida = (df["ebit"] <= 0) & (df["divida_liquida"] > 0)
    df["alerta_divida"] = divida_alta | ebit_negativo_com_divida
    return df
