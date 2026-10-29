-- Consultas das perguntas de negócio, sempre a partir da fato com JOIN nas dimensões

-- 1) Ranking do ROE no último ano da base (quem deu mais retorno sobre o patrimônio)
SELECT e.ticker, e.nome, e.grupo, t.ano, ROUND(f.roe * 100, 1) AS roe_pct
FROM fato_indicadores f
JOIN dim_empresa e ON e.empresa_sk = f.empresa_sk
JOIN dim_tempo t ON t.tempo_sk = f.tempo_sk
WHERE t.ano = (SELECT MAX(ano) FROM dim_tempo)
ORDER BY f.roe DESC;

-- 2) Crescimento da receita de 2021 para 2023, por empresa
SELECT e.ticker, e.grupo,
       SUM(CASE WHEN t.ano = 2021 THEN f.receita END) AS receita_2021,
       SUM(CASE WHEN t.ano = 2023 THEN f.receita END) AS receita_2023,
       ROUND((SUM(CASE WHEN t.ano = 2023 THEN f.receita END)
            / SUM(CASE WHEN t.ano = 2021 THEN f.receita END) - 1) * 100, 1) AS crescimento_pct
FROM fato_indicadores f
JOIN dim_empresa e ON e.empresa_sk = f.empresa_sk
JOIN dim_tempo t ON t.tempo_sk = f.tempo_sk
GROUP BY e.ticker, e.grupo
ORDER BY crescimento_pct DESC;

-- 3) Empresas em alerta em 2023 (liquidez abaixo de 1,5x ou dívida alta)
SELECT e.ticker, e.nome, ROUND(f.liquidez_corrente, 2) AS liquidez_corrente,
       ROUND(f.alavancagem, 2) AS alavancagem, f.alerta_liquidez, f.alerta_divida
FROM fato_indicadores f
JOIN dim_empresa e ON e.empresa_sk = f.empresa_sk
JOIN dim_tempo t ON t.tempo_sk = f.tempo_sk
WHERE t.ano = 2023 AND (f.alerta_liquidez OR f.alerta_divida)
ORDER BY e.ticker;
