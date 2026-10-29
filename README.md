# WEG em números: análise fundamentalista 2021–2023

Projeto Avaliativo Final do Módulo 2 (SCTEC) — em construção.

## Resumo

(em construção)

## Contexto e pergunta orientadora

(em construção)

## Fonte dos dados e licença

(em construção)

## Pipeline de dados

(em construção)

## Dicionário de dados

A camada Gold é um esquema estrela com duas dimensões e uma tabela fato, nos arquivos de `data/gold/`. O grão da fato é uma linha por empresa por exercício fiscal (11 empresas x 3 anos = 33 linhas). Os valores estão em reais (R$), já multiplicados pela escala da CVM. Margens e ROE estão em fração (0,329 = 32,9%); liquidez e alavancagem estão em vezes (1,92 = 1,92x).

### dim_empresa (11 linhas)

| Coluna | Tipo | Significado | Regra |
|---|---|---|---|
| `empresa_sk` | inteiro | chave da empresa (PK) | chave substituta, de 1 a 11 em ordem alfabética de ticker (WEGE3 = 11) |
| `ticker` | texto | código da ação na B3 | ex.: WEGE3 |
| `cd_cvm` | texto | código da empresa na CVM | como vem no DFP, com 6 dígitos |
| `cnpj` | texto | CNPJ da companhia | cadastro da CVM |
| `nome` | texto | nome da empresa | cadastro da CVM |
| `setor` | texto | setor de atuação | cadastro da CVM, simplificado |
| `grupo` | texto | grupo usado para comparar setores (pergunta 3) | Indústria, Commodities ou Consumo e serviços (classificação nossa) |

### dim_tempo (3 linhas)

| Coluna | Tipo | Significado | Regra |
|---|---|---|---|
| `tempo_sk` | inteiro | chave do ano (PK) | chave substituta, de 1 a 3 |
| `ano` | inteiro | exercício fiscal | 2021, 2022 e 2023 |
| `data_inicio` | data | início do exercício | 1º de janeiro |
| `data_fim` | data | fim do exercício (data do balanço) | 31 de dezembro |

### fato_indicadores (33 linhas)

| Coluna | Tipo | Significado | Regra |
|---|---|---|---|
| `indicador_sk` | inteiro | chave da linha (PK) | chave substituta, de 1 a 33 |
| `empresa_sk` | inteiro | empresa (FK) | liga com a `dim_empresa` |
| `tempo_sk` | inteiro | ano (FK) | liga com a `dim_tempo` |
| `receita` | decimal | receita líquida de vendas e serviços | conta 3.01 da DRE |
| `lucro_bruto` | decimal | receita menos o custo do que foi vendido | conta 3.03 |
| `ebit` | decimal | resultado operacional, antes do resultado financeiro e dos impostos | conta 3.05 |
| `lucro_liquido` | decimal | lucro líquido consolidado (inclui a parte dos acionistas minoritários) | conta 3.11 |
| `ativo_circulante` | decimal | dinheiro e direitos que viram dinheiro em até 12 meses | conta 1.01 do balanço |
| `passivo_circulante` | decimal | dívidas e contas que vencem em até 12 meses | conta 2.01 |
| `patrimonio_liquido` | decimal | patrimônio líquido consolidado no fim do ano | conta 2.03 |
| `caixa` | decimal | caixa e equivalentes de caixa | conta 1.01.01 |
| `aplicacoes` | decimal | aplicações financeiras | conta 1.01.02 |
| `emprestimos` | decimal | empréstimos e financiamentos de curto e longo prazo | 2.01.04 + 2.02.01 |
| `arrendamentos` | decimal | aluguéis contados como dívida (IFRS 16) que algumas empresas lançam dentro dos empréstimos | 2.01.04.03 + 2.02.01.03 (0 quando a conta não existe) |
| `divida_liquida` | decimal | dívida menos o dinheiro em caixa; negativa quando a empresa tem mais caixa que dívida | emprestimos - arrendamentos - caixa - aplicacoes |
| `margem_bruta` | decimal | parte da receita que sobra depois do custo | lucro_bruto / receita |
| `margem_ebit` | decimal | margem operacional | ebit / receita |
| `margem_liquida` | decimal | parte da receita que vira lucro | lucro_liquido / receita |
| `roe` | decimal | retorno sobre o patrimônio dos sócios | lucro_liquido / patrimonio_liquido |
| `liquidez_corrente` | decimal | quanto a empresa tem no curto prazo para cada real que deve no curto prazo | ativo_circulante / passivo_circulante |
| `alavancagem` | decimal | quantos anos de EBIT pagariam a dívida líquida | divida_liquida / ebit; vazio quando o EBIT é zero ou negativo |
| `alerta_liquidez` | booleano | alerta de liquidez (pergunta 4) | liquidez_corrente abaixo de 1,5 |
| `alerta_divida` | booleano | alerta de dívida (pergunta 4) | alavancagem acima de 3, ou EBIT zero ou negativo com dívida líquida positiva |

O enunciado cita Dívida Líquida / EBITDA. Aqui a alavancagem usa o EBIT, porque a depreciação não vem nos três arquivos usados (DRE, BPA e BPP); com o EBIT o número fica um pouco maior, ou seja, mais conservador.

O crescimento da receita não fica na fato, porque depende do período escolhido no filtro: o app calcula receita do último ano / receita do primeiro ano - 1.

A camada Silver (`data/silver/contas_2021_2023.csv`) fica no formato longo, com uma linha por empresa, ano e conta, e as colunas `cd_cvm`, `ticker`, `ano`, `demonstrativo` (DRE, BPA ou BPP), `cd_conta`, `ds_conta`, `valor` (em R$), `versao` (versão do DFP usada) e `dt_refer` (data de referência do documento).

## Tecnologias

(em construção)

## Principais resultados

(em construção)

## Discussão e limitações

(em construção)

## Aplicação profissional

(em construção)

## Demonstração do app

App publicado no Streamlit Community Cloud: **https://weg-em-numeros.streamlit.app**

Na barra lateral ficam os filtros (grupo de setor, empresas e período) e a origem dos dados. O app tem 4 KPIs da carteira no topo e 5 abas: WEG em foco, Crescimento, Rentabilidade, Solvência e Dados. Os dados vêm do Supabase (PostgreSQL); se o banco não responder, o app usa os CSVs da camada Gold e avisa na barra lateral.

## Como executar localmente

Precisa do Python 3.12 e do Git. No terminal (comandos do Windows):

```bash
git clone https://github.com/gobels2/Projeto-Avaliativo-Final-Modulo-2-SCTEC.git
cd Projeto-Avaliativo-Final-Modulo-2-SCTEC
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Para ler os dados do Supabase, copie o `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha com os dados do seu projeto (botão Connect > Session pooler). Esse arquivo está no `.gitignore` e não vai para o GitHub. Sem ele o app funciona do mesmo jeito, lendo os CSVs da camada Gold (`data/gold/`), e avisa isso na barra lateral.

Para abrir o app:

```bash
streamlit run app.py
```

Para refazer os dados do zero (opcional):

```bash
# baixa os DFPs da CVM e gera as camadas Bronze, Silver e Gold
python src/etl.py
# cria as tabelas no Supabase e carrega a Gold (precisa do secrets.toml)
python src/carga_supabase.py
```

## Estrutura de pastas

```text
Projeto-Avaliativo-Final-Modulo-2-SCTEC/
├── app.py                     # app Streamlit (dashboard)
├── requirements.txt           # bibliotecas com versão fixa
├── .streamlit/
│   ├── config.toml            # tema do app (azul da WEG)
│   └── secrets.toml.example   # modelo da conexão com o Supabase
├── data/
│   ├── bronze/                # dados brutos da CVM (DRE, BPA e BPP 2021–2023) e registro do download
│   ├── silver/                # só as contas usadas, limpas, uma linha por empresa, ano e conta
│   └── gold/                  # esquema estrela: dim_empresa, dim_tempo e fato_indicadores
├── notebooks/                 # notebook de exploração dos dados
├── src/
│   ├── etl.py                 # extração e limpeza (Bronze, Silver e Gold)
│   ├── indicadores.py         # cálculo dos indicadores financeiros
│   └── carga_supabase.py      # carga da Gold no Supabase
├── sql/
│   ├── criar_tabelas.sql      # tabelas com chave primária e chave estrangeira
│   └── consultas.sql          # consultas das perguntas de negócio
└── docs/img/                  # prints usados no README
```

## Gestão ágil e links do projeto

(em construção)

## Autoria e referências

(em construção)
