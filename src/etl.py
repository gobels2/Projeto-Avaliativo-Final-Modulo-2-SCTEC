"""
ETL dos demonstrativos financeiros (DFP) da CVM em camadas: Bronze, Silver e Gold.

Fonte: Portal de Dados Abertos da CVM
https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/

Como rodar (a partir da pasta do projeto):
    python src/etl.py
"""

import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from indicadores import calcular_indicadores

# caminhos relativos à pasta do projeto (funciona em qualquer computador)
PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = PASTA_RAIZ / "data"

# exercícios pedidos no enunciado (Linha 1)
ANOS = [2021, 2022, 2023]

# endereço dos arquivos anuais na CVM
URL_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"

# empresas analisadas: código CVM (como aparece no DFP) -> dados da empresa
# setor = setor do cadastro da CVM, simplificado; grupo = de-para nosso para a pergunta 3
EMPRESAS = {
    "005410": {"ticker": "WEGE3", "nome": "WEG S.A.", "cnpj": "84.429.695/0001-11",
               "setor": "Máquinas e Equipamentos", "grupo": "Indústria"},
    "020087": {"ticker": "EMBR3", "nome": "Embraer S.A.", "cnpj": "07.689.002/0001-89",
               "setor": "Máquinas e Equipamentos", "grupo": "Indústria"},
    "004170": {"ticker": "VALE3", "nome": "Vale S.A.", "cnpj": "33.592.510/0001-54",
               "setor": "Extração Mineral", "grupo": "Commodities"},
    "003980": {"ticker": "GGBR4", "nome": "Gerdau S.A.", "cnpj": "33.611.500/0001-19",
               "setor": "Metalurgia e Siderurgia", "grupo": "Commodities"},
    "012653": {"ticker": "KLBN11", "nome": "Klabin S.A.", "cnpj": "89.637.490/0001-45",
               "setor": "Papel e Celulose", "grupo": "Commodities"},
    "013986": {"ticker": "SUZB3", "nome": "Suzano S.A.", "cnpj": "16.404.287/0001-55",
               "setor": "Papel e Celulose", "grupo": "Commodities"},
    "009512": {"ticker": "PETR4", "nome": "Petrobras", "cnpj": "33.000.167/0001-01",
               "setor": "Petróleo e Gás", "grupo": "Commodities"},
    "020575": {"ticker": "JBSS3", "nome": "JBS S.A.", "cnpj": "02.916.265/0001-60",
               "setor": "Alimentos", "grupo": "Commodities"},
    "023264": {"ticker": "ABEV3", "nome": "Ambev S.A.", "cnpj": "07.526.557/0001-00",
               "setor": "Bebidas", "grupo": "Consumo e serviços"},
    "008133": {"ticker": "LREN3", "nome": "Lojas Renner S.A.", "cnpj": "92.754.738/0001-62",
               "setor": "Comércio (varejo)", "grupo": "Consumo e serviços"},
    "017329": {"ticker": "EGIE3", "nome": "Engie Brasil Energia S.A.", "cnpj": "02.474.103/0001-19",
               "setor": "Energia Elétrica", "grupo": "Consumo e serviços"},
}

# o Itaú (ITUB4) entra só na Bronze: banco usa outro plano de contas e sai na Silver
CD_CVM_ITAU = "019348"

# contas da CVM usadas nos indicadores: código -> nome da coluna
CONTAS = {
    "3.01": "receita",
    "3.03": "lucro_bruto",
    "3.05": "ebit",
    "3.11": "lucro_liquido",
    "1.01": "ativo_circulante",
    "1.01.01": "caixa",
    "1.01.02": "aplicacoes",
    "2.01": "passivo_circulante",
    "2.01.04": "emprestimos_cp",
    "2.01.04.03": "arrendamentos_cp",
    "2.02.01": "emprestimos_lp",
    "2.02.01.03": "arrendamentos_lp",
    "2.03": "patrimonio_liquido",
}


def ler_demonstrativo(caminho_zip, tipo, ano):
    """Lê um demonstrativo consolidado (DRE, BPA ou BPP) direto de dentro do zip da CVM."""
    nome_arquivo = f"dfp_cia_aberta_{tipo}_con_{ano}.csv"
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        with arquivo_zip.open(nome_arquivo) as arquivo:
            # os arquivos da CVM vêm em latin-1; lendo como utf-8 dá erro nos acentos
            df = pd.read_csv(arquivo, sep=";", encoding="latin-1", dtype=str)
    return df


def baixar_zips(pasta_zips):
    """Baixa da CVM os zips que ainda não estão na pasta e registra a data do download."""
    pasta_zips.mkdir(parents=True, exist_ok=True)
    caminhos = []
    baixou_algum = False
    for ano in ANOS:
        caminho = pasta_zips / f"dfp_cia_aberta_{ano}.zip"
        if not caminho.exists():
            print(f"Baixando o DFP de {ano}...")
            resposta = requests.get(URL_CVM.format(ano=ano), timeout=120)
            resposta.raise_for_status()
            caminho.write_bytes(resposta.content)
            baixou_algum = True
        caminhos.append(caminho)

    # a CVM republica os arquivos quando uma empresa reenvia o DFP, então guardamos a data
    if baixou_algum:
        registro = PASTA_DADOS / "bronze" / "data_download.txt"
        registro.write_text(f"DFP da CVM baixados em {date.today():%d/%m/%Y}\n", encoding="utf-8")
    return caminhos


def montar_bronze(pasta_zips):
    """Junta DRE, BPA e BPP dos três anos e guarda só as linhas das empresas, sem alterar nada."""
    codigos = list(EMPRESAS) + [CD_CVM_ITAU]
    partes = []
    for ano in ANOS:
        caminho_zip = pasta_zips / f"dfp_cia_aberta_{ano}.zip"
        for tipo in ["DRE", "BPA", "BPP"]:
            df = ler_demonstrativo(caminho_zip, tipo, ano)
            df = df[df["CD_CVM"].isin(codigos)].copy()
            # guarda de qual arquivo veio cada linha (rastreabilidade)
            df["ARQUIVO_ORIGEM"] = f"dfp_cia_aberta_{tipo}_con_{ano}.csv"
            partes.append(df)
    return pd.concat(partes, ignore_index=True)


def montar_silver(bronze, conferir=False):
    """Limpa a Bronze: exercício certo, versão mais recente, só as contas usadas, valor em reais e datas."""
    df = bronze.copy()

    # Regra 1: cada arquivo traz o ano (ÚLTIMO) e o ano anterior (PENÚLTIMO); fica o ÚLTIMO
    df = df[df["ORDEM_EXERC"] == "ÚLTIMO"].copy()
    if conferir:
        print(f"  depois do ÚLTIMO: {len(df)} linhas")

    # Regra 2: quem reenviou o DFP tem mais de uma versão; fica a maior
    # (vira número antes, porque como texto "10" vem antes de "9")
    df["VERSAO"] = df["VERSAO"].astype(int)
    maior_versao = df.groupby(["CD_CVM", "DT_REFER"])["VERSAO"].transform("max")
    df = df[df["VERSAO"] == maior_versao].copy()
    if conferir:
        print(f"  depois da maior versão: {len(df)} linhas")

    # Regra 3: só as 11 empresas analisadas (o Itaú sai aqui)
    df = df[df["CD_CVM"].isin(list(EMPRESAS))].copy()
    if conferir:
        print(f"  depois de tirar o Itaú: {len(df)} linhas")

    # Regra 4: só as contas usadas nos indicadores
    df = df[df["CD_CONTA"].isin(list(CONTAS))].copy()
    if conferir:
        print(f"  depois de filtrar as contas: {len(df)} linhas")

    # Regra 5: valor em reais (texto com ponto decimal; escala MIL = multiplicar por 1000)
    df["valor"] = df["VL_CONTA"].astype(float)
    df.loc[df["ESCALA_MOEDA"] == "MIL", "valor"] = df["valor"] * 1000

    # Regra 6: datas de texto para datetime e o ano do exercício
    for coluna in ["DT_REFER", "DT_INI_EXERC", "DT_FIM_EXERC"]:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
    df["ano"] = df["DT_FIM_EXERC"].dt.year

    # Regra 7: linhas repetidas saem
    antes = len(df)
    df = df.drop_duplicates()
    if conferir:
        print(f"  duplicadas removidas: {antes - len(df)}")

    df["ticker"] = df["CD_CVM"].map(lambda codigo: EMPRESAS[codigo]["ticker"])
    df["demonstrativo"] = df["ARQUIVO_ORIGEM"].str.split("_").str[3]
    df = df.rename(columns={"CD_CVM": "cd_cvm", "CD_CONTA": "cd_conta", "DS_CONTA": "ds_conta",
                            "VERSAO": "versao", "DT_REFER": "dt_refer"})
    colunas = ["cd_cvm", "ticker", "ano", "demonstrativo", "cd_conta", "ds_conta", "valor", "versao", "dt_refer"]
    return df[colunas].reset_index(drop=True)


def pivotar_contas(silver):
    """Passa a Silver do formato longo para uma linha por empresa-ano, com uma coluna por conta."""
    df = silver.pivot(index=["cd_cvm", "ticker", "ano"], columns="cd_conta", values="valor")
    df = df.rename(columns=CONTAS).reset_index()
    df.columns.name = None
    # nem toda empresa lança arrendamento: conta ausente vira 0
    df["arrendamentos_cp"] = df["arrendamentos_cp"].fillna(0)
    df["arrendamentos_lp"] = df["arrendamentos_lp"].fillna(0)
    return df


def montar_gold(silver):
    """Monta o esquema estrela: dim_empresa, dim_tempo e a fato com os indicadores de cada empresa-ano."""
    # dim_empresa: chave substituta em ordem alfabética de ticker (ABEV3 = 1 ... WEGE3 = 11)
    dim_empresa = pd.DataFrame.from_dict(EMPRESAS, orient="index").rename_axis("cd_cvm").reset_index()
    dim_empresa = dim_empresa.sort_values("ticker").reset_index(drop=True)
    dim_empresa["empresa_sk"] = range(1, len(dim_empresa) + 1)
    dim_empresa = dim_empresa[["empresa_sk", "ticker", "cd_cvm", "cnpj", "nome", "setor", "grupo"]]

    # dim_tempo: um exercício fiscal por ano, de 1º de janeiro a 31 de dezembro
    dim_tempo = pd.DataFrame({"tempo_sk": range(1, len(ANOS) + 1), "ano": ANOS})
    dim_tempo["data_inicio"] = pd.to_datetime(dim_tempo["ano"].astype(str) + "-01-01")
    dim_tempo["data_fim"] = pd.to_datetime(dim_tempo["ano"].astype(str) + "-12-31")

    # fato: grão = uma linha por empresa por exercício, ligada às dimensões pelas chaves
    fato = calcular_indicadores(pivotar_contas(silver))
    fato = fato.merge(dim_empresa[["empresa_sk", "cd_cvm"]], on="cd_cvm")
    fato = fato.merge(dim_tempo[["tempo_sk", "ano"]], on="ano")
    fato = fato.sort_values(["empresa_sk", "tempo_sk"]).reset_index(drop=True)
    fato["indicador_sk"] = range(1, len(fato) + 1)
    colunas = ["indicador_sk", "empresa_sk", "tempo_sk", "receita", "lucro_bruto", "ebit", "lucro_liquido",
               "ativo_circulante", "passivo_circulante", "patrimonio_liquido", "caixa", "aplicacoes",
               "emprestimos", "arrendamentos", "divida_liquida", "margem_bruta", "margem_ebit", "margem_liquida",
               "roe", "liquidez_corrente", "alavancagem", "alerta_liquidez", "alerta_divida"]
    return dim_empresa, dim_tempo, fato[colunas]


def main():
    # Passo 1: Bronze - baixa os zips e guarda as linhas brutas das empresas
    pasta_zips = PASTA_DADOS / "bronze" / "zips"
    baixar_zips(pasta_zips)
    bronze = montar_bronze(pasta_zips)
    bronze.to_csv(PASTA_DADOS / "bronze" / "dfp_con_2021_2023.csv", index=False, encoding="utf-8")
    print("=== Camada Bronze ===")
    print(f"Linhas: {len(bronze)}")
    print(f"Empresas: {bronze['CD_CVM'].nunique()}")
    print(f"Anos (DT_REFER): {sorted(bronze['DT_REFER'].str[:4].unique())}")
    print(f"Arquivos de origem: {bronze['ARQUIVO_ORIGEM'].nunique()}")

    # Passo 2: Silver - exercício certo, versão mais recente, valores em reais e datas
    print("=== Camada Silver ===")
    silver = montar_silver(bronze, conferir=True)
    silver.to_csv(PASTA_DADOS / "silver" / "contas_2021_2023.csv", index=False, encoding="utf-8")
    print(f"Linhas: {len(silver)} | Empresas: {silver['ticker'].nunique()} | Anos: {sorted(silver['ano'].unique().tolist())}")
    print(f"Nulos: {silver.isna().sum().sum()} | Duplicados: {silver.duplicated().sum()}")

    # Passo 3: Gold - indicadores e esquema estrela (2 dimensões + 1 fato)
    print("=== Camada Gold ===")
    dim_empresa, dim_tempo, fato = montar_gold(silver)
    pasta_gold = PASTA_DADOS / "gold"
    dim_empresa.to_csv(pasta_gold / "dim_empresa.csv", index=False, encoding="utf-8")
    dim_tempo.to_csv(pasta_gold / "dim_tempo.csv", index=False, encoding="utf-8")
    fato.to_csv(pasta_gold / "fato_indicadores.csv", index=False, encoding="utf-8")
    print(f"dim_empresa: {len(dim_empresa)} | dim_tempo: {len(dim_tempo)} | fato_indicadores: {len(fato)} (esperado 11 x 3 = 33)")
    # toda linha da fato precisa achar a sua empresa e o seu ano nas dimensões
    sem_empresa = (~fato["empresa_sk"].isin(dim_empresa["empresa_sk"])).sum()
    sem_ano = (~fato["tempo_sk"].isin(dim_tempo["tempo_sk"])).sum()
    print(f"Chaves sem correspondência: empresa {sem_empresa} | ano {sem_ano}")
    print(f"Alavancagem vazia (EBIT zero ou negativo): {fato['alavancagem'].isna().sum()}")


if __name__ == "__main__":
    main()
