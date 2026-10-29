"""
Carga da camada Gold no Supabase (PostgreSQL).

Lê a conexão do .streamlit/secrets.toml (fora do git), recria as tabelas com o
sql/criar_tabelas.sql e grava os 3 CSVs da Gold, dimensões antes da fato.

Como rodar (a partir da pasta do projeto):
    python src/carga_supabase.py
"""

from pathlib import Path

import pandas as pd
import toml
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

PASTA_RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_SECRETS = PASTA_RAIZ / ".streamlit" / "secrets.toml"
ARQUIVO_SQL = PASTA_RAIZ / "sql" / "criar_tabelas.sql"
PASTA_GOLD = PASTA_RAIZ / "data" / "gold"

# dimensões antes da fato, por causa das chaves estrangeiras
TABELAS = ["dim_empresa", "dim_tempo", "fato_indicadores"]


def ler_secrets():
    """Lê os dados de conexão do secrets.toml (o mesmo arquivo que o Streamlit usa)."""
    secrets = toml.load(ARQUIVO_SECRETS)
    return secrets["connections"]["postgresql"]


def criar_engine(config):
    """Cria o engine do SQLAlchemy; o URL.create aceita senha com caractere especial."""
    url = URL.create(
        "postgresql+psycopg",
        username=config["username"],
        password=config["password"],
        host=config["host"],
        port=config["port"],
        database=config["database"],
    )
    return create_engine(url, pool_pre_ping=True)


def criar_tabelas(engine):
    """Roda o sql/criar_tabelas.sql, um comando por vez."""
    comandos = ARQUIVO_SQL.read_text(encoding="utf-8").split(";")
    with engine.begin() as conexao:
        for comando in comandos:
            if comando.strip():
                conexao.execute(text(comando))


def carregar_tabelas(engine):
    """Grava os CSVs da Gold nas tabelas, dimensões antes da fato."""
    for tabela in TABELAS:
        # cd_cvm como texto para não perder os zeros da frente
        df = pd.read_csv(PASTA_GOLD / f"{tabela}.csv", dtype={"cd_cvm": str})
        if tabela == "dim_tempo":
            df["data_inicio"] = pd.to_datetime(df["data_inicio"]).dt.date
            df["data_fim"] = pd.to_datetime(df["data_fim"]).dt.date
        df.to_sql(tabela, engine, if_exists="append", index=False)
        print(f"   {tabela}: {len(df)} linhas gravadas")


def main():
    config = ler_secrets()
    print(f"-> Conectando ao Supabase em: {config['host']} (porta {config['port']})...")
    engine = criar_engine(config)

    print("-> Criando as tabelas com o sql/criar_tabelas.sql...")
    criar_tabelas(engine)

    print("-> Gravando os CSVs da camada Gold...")
    carregar_tabelas(engine)

    # conferência: conta as linhas que ficaram no banco
    with engine.connect() as conexao:
        empresas = conexao.execute(text("SELECT COUNT(*) FROM dim_empresa")).scalar()
        anos = conexao.execute(text("SELECT COUNT(*) FROM dim_tempo")).scalar()
        registros = conexao.execute(text("SELECT COUNT(*) FROM fato_indicadores")).scalar()
    print(f"Carga concluída: {empresas} empresas, {anos} anos, {registros} registros")


if __name__ == "__main__":
    main()
