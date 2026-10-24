"""
ETL dos demonstrativos financeiros (DFP) da CVM em camadas: Bronze, Silver e Gold.

Fonte: Portal de Dados Abertos da CVM
https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/

Como rodar (a partir da pasta do projeto):
    python src/etl.py
"""

import zipfile
from pathlib import Path

import pandas as pd

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


def ler_demonstrativo(caminho_zip, tipo, ano):
    """Lê um demonstrativo consolidado (DRE, BPA ou BPP) direto de dentro do zip da CVM."""
    nome_arquivo = f"dfp_cia_aberta_{tipo}_con_{ano}.csv"
    with zipfile.ZipFile(caminho_zip) as arquivo_zip:
        with arquivo_zip.open(nome_arquivo) as arquivo:
            # os arquivos da CVM vêm em latin-1; lendo como utf-8 dá erro nos acentos
            df = pd.read_csv(arquivo, sep=";", encoding="latin-1", dtype=str)
    return df
