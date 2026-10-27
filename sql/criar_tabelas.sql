-- Esquema estrela da camada Gold no Supabase (PostgreSQL)
-- Grão da fato: uma linha por empresa por exercício fiscal

-- apaga a fato antes das dimensões, porque ela depende delas
DROP TABLE IF EXISTS fato_indicadores;
DROP TABLE IF EXISTS dim_empresa;
DROP TABLE IF EXISTS dim_tempo;

-- dimensão das empresas (chave substituta em ordem alfabética de ticker)
CREATE TABLE dim_empresa (
    empresa_sk INTEGER PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    cd_cvm VARCHAR(6) NOT NULL,
    cnpj VARCHAR(18) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    setor VARCHAR(50) NOT NULL,
    grupo VARCHAR(30) NOT NULL
);

-- dimensão de tempo (um exercício fiscal por ano)
CREATE TABLE dim_tempo (
    tempo_sk INTEGER PRIMARY KEY,
    ano INTEGER NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL
);

-- fato: valores em reais com 2 casas e indicadores (razões) com 6 casas
CREATE TABLE fato_indicadores (
    indicador_sk INTEGER PRIMARY KEY,
    empresa_sk INTEGER NOT NULL REFERENCES dim_empresa (empresa_sk),
    tempo_sk INTEGER NOT NULL REFERENCES dim_tempo (tempo_sk),
    receita NUMERIC(20,2),
    lucro_bruto NUMERIC(20,2),
    ebit NUMERIC(20,2),
    lucro_liquido NUMERIC(20,2),
    ativo_circulante NUMERIC(20,2),
    passivo_circulante NUMERIC(20,2),
    patrimonio_liquido NUMERIC(20,2),
    caixa NUMERIC(20,2),
    aplicacoes NUMERIC(20,2),
    emprestimos NUMERIC(20,2),
    arrendamentos NUMERIC(20,2),
    divida_liquida NUMERIC(20,2),
    margem_bruta NUMERIC(12,6),
    margem_ebit NUMERIC(12,6),
    margem_liquida NUMERIC(12,6),
    roe NUMERIC(12,6),
    liquidez_corrente NUMERIC(12,6),
    alavancagem NUMERIC(12,6),
    alerta_liquidez BOOLEAN NOT NULL,
    alerta_divida BOOLEAN NOT NULL,
    UNIQUE (empresa_sk, tempo_sk)
);
