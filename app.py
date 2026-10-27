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
