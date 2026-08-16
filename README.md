# ⚓ Desafio Lighthouse 2026 — LH Nautical

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%2F%20TMDL-F2C811?logo=powerbi&logoColor=black)](https://learn.microsoft.com/power-bi/developer/projects/)
[![DAX](https://img.shields.io/badge/DAX-48%20medidas-0E5C7F)](powerbi/sm_lh_nautical.SemanticModel/definition/tables/_Medidas.tmdl)
[![Conferências](https://img.shields.io/badge/confer%C3%AAncias%20adversariais-46%20aprovadas-2E7D32)](tests/verificar_respostas.py)
[![Validador](https://img.shields.io/badge/validador%20PBIP-20%20regras-6A4C93)](tests/validar_pbip.py)

Resposta ao Desafio Técnico do Programa Lighthouse 2026 da **Indicium**, trilha **Dados e IA**.

**[▶ Abrir o dashboard publicado](https://app.powerbi.com/view?r=eyJrIjoiMDY4MDQxM2ItYWI4Ni00ZjQ5LWJmOGMtMTlhNDgwNDAzNjQzIiwidCI6ImMyMGU3MTg4LTNkMzEtNGM1ZC05YWNlLTE4MzQyM2E2MGMxZCJ9)** · [PDF das 5 páginas](powerbi/lh_nautical.pdf) · por **[Breno Teodomiro](https://www.linkedin.com/in/breno-teodomiro-power-bi/)**

> *"Eu valorizo mais a organização e a explicação do que o código rodando sem eu entender nada."*
> — Gabriel Santos, Tech Lead (LH Nautical)
>
> Este repositório foi construído com essa frase como critério de projeto.

---

## 🎯 O que este projeto entrega

Um pipeline de dados completo sobre o dump relacional de uma varejista náutica
fictícia — **24 CSVs, 433.424 linhas, sem tratamento algum** — e as sete
respostas que o desafio pede, mais um dashboard executivo.

Em quatro camadas:

| | O quê | Como |
|---|---|---|
| 🗄 **Engenharia** | schema PostgreSQL gerado por inferência de tipos a partir dos CSVs, e a carga das 433 mil linhas | Python **só com biblioteca padrão** (a Q2 desclassifica quem usar pandas) e `COPY FROM STDIN` com bytes crus |
| 🔎 **Análise** | EDA de confiabilidade, ranking de clientes, calendário de sazonalidade | SQL puro sobre a camada bruta, como as premissas exigem |
| 🤖 **Ciência de dados** | previsão de demanda por média móvel e recomendação por similaridade de cosseno | pandas, numpy e scikit-learn — com a prova de que **os dois baselines falham**, e por quê |
| 📊 **Visualização** | 5 páginas, 21 componentes, 13 deles filtrando a página ao clique | Power BI em **PBIP/TMDL versionado como código**, com os visuais em HTML gerado por DAX |

**O diferencial não é o código — é o que ele encontra.** Três das sete respostas
mudam conforme a leitura da premissa, e cada ambiguidade está documentada com o
cenário alternativo em vez de resolvida em silêncio. Todo número foi recalculado
por um **caminho independente**: o que saiu em SQL foi refeito em Python sobre
os CSVs, e vice-versa — 46 conferências, todas aprovadas.

---

## 📊 O dashboard

Cinco páginas, **21 componentes em HTML gerado por DAX** — 13 deles filtram a
página inteira ao clique. Tema escuro, paleta validada para daltonismo, e cada
título é uma frase de conclusão, não um rótulo.

### Sumário executivo

![Sumário executivo](docs/imagens/1-sumario-executivo.png)

### Vendas e margem

![Vendas e margem](docs/imagens/2-vendas-e-margem.png)

### Clientes — Questão 4

![Clientes](docs/imagens/3-clientes-q4.png)

### Sazonalidade — Questão 5

![Sazonalidade](docs/imagens/4-sazonalidade-q5.png)

### Previsão e recomendação — Questões 6 e 7

![Previsão e recomendação](docs/imagens/5-previsao-e-recomendacao-q6-q7.png)

**Como ele é feito:** o projeto é versionado em **PBIP** — o modelo em TMDL e o
relatório em PBIR, ambos texto. Dá para ler o diff de uma medida no GitHub. Os
componentes saem de [`powerbi/gerar_html_dax.py`](powerbi/gerar_html_dax.py), e
[`tests/validar_pbip.py`](tests/validar_pbip.py) roda **20 regras** contra o
projeto antes de abrir o Desktop — cada uma testada injetando o defeito que ela
deve pegar.

---

## 🧭 O problema

A LH Nautical opera lojas físicas, armazéns e e-commerce. Seus dados de 2020 a
2026 cobrem o ciclo completo — catálogo, pedidos, pagamentos, NF-e, compras,
estoque e devoluções — em **24 CSVs, 433.424 linhas, 36 MB**, sem tratamento
algum.

A missão: transformar isso em respostas que a diretoria consiga usar.

## 🔎 Números da base

| | |
|---|---|
| Tabelas | 24 |
| Linhas | 433.424 |
| Período | 2020-01-01 a **2027-02-13** (o enunciado diz 2026) |
| Integridade referencial | **37/37 relacionamentos sem órfãos** |
| Consistência aritmética | fecha ao centavo em ~260 mil conferências |
| Classes de problema de qualidade | **22** ([ADR-002](docs/adr/ADR-002-arquitetura-medalhao.md)) |

A base é estruturalmente sólida e semanticamente suja — a combinação exata que
exige perfilamento antes de qualquer conclusão. O perfilamento coluna a coluna
está em [`entregaveis/Q2_schema/perfil.md`](entregaveis/Q2_schema/perfil.md), e
o que cada classe de sujeira muda na resposta, em
[`docs/MAPA_QUESTOES.md`](docs/MAPA_QUESTOES.md).

## 🏗 Arquitetura

```
24 CSVs ──▶ [raw]  ──▶ [silver] ──▶ [gold] ──▶ Power BI
            bruto      limpo        star        dashboard
            sem        tipado       schema
            tratamento
               │
               └──▶ Q1, Q2, Q3, Q4, Q5   (as premissas exigem dado bruto)
```

Três schemas no mesmo PostgreSQL. As questões são respondidas contra `raw`, como
o enunciado manda; o dashboard bebe de `gold`. A distância entre os dois **é** a
resposta da questão 1.3.

## ✅ As 7 questões

| # | Frente | Entregável | Restrição crítica |
|---|---|---|---|
| 1 | EDA | [`q1_eda_orders.sql`](entregaveis/Q1_eda/) | só `orders`, sem limpeza, SQL |
| 2 | Schema | [`q2_gerar_schema.py`](entregaveis/Q2_schema/) | **somente stdlib** — pandas desclassifica |
| 3 | Carga | [`q3_carregar_csvs.py`](entregaveis/Q3_carga/) | sem tratamento de dados |
| 4 | Clientes | [`q4_clientes_elite.sql`](entregaveis/Q4_clientes/) | ≥13 de 14 categorias |
| 5 | Calendário | [`q5_dim_calendario.sql`](entregaveis/Q5_calendario/) | dias sem venda contam como zero |
| 6 | Previsão | [`q6_previsao_demanda.py`](entregaveis/Q6_previsao/) | média móvel 3m, sem vazamento |
| 7 | Recomendação | [`q7_recomendacao.py`](entregaveis/Q7_recomendacao/) | matriz binária, cosseno |

Rastreabilidade completa — premissa, entregável, resposta e gate de conformidade
— em [`docs/MAPA_QUESTOES.md`](docs/MAPA_QUESTOES.md).

## 💡 Três achados que mudam respostas

**O filtro de elite da questão 4 não filtra.** Existem 14 categorias e o critério
exige 13. Resultado: **1.971 dos 2.000 clientes (98,5%) passam** — 1.771 deles
compraram de todas as 14. O ranking é decidido exclusivamente pelo ticket médio.

**O erro do estagiário na questão 5 troca o diagnóstico de dia.** Com o
calendário completo, o pior dia é **quinta-feira** (R$ 157.154). Ignorando os 78
dias sem venda, a resposta vira segunda-feira. Seguindo o cálculo errado, a loja
fecharia no dia errado.

**"Bússola de Bordo 702" existe duas vezes.** Dois `product_id` (74 e 240),
marcas e categorias diferentes, descrição idêntica. A previsão da questão 6 vale
116, 76 ou 40 unidades conforme a leitura — e o baseline subestima a demanda real
em 44% em qualquer cenário.

## 🛠 Stack

**PostgreSQL** (exigido pelas questões 2 e 3) · **Python 3.12** com `uv` ·
pandas, numpy, scikit-learn, pyarrow · **Power BI** via PBIP/TMDL · ruff, mypy,
pytest

Sem Docker, sem dbt, sem DuckDB — decisões justificadas nos
[ADRs](docs/adr/); a de não usar dbt está detalhada na
[ADR-008](docs/adr/ADR-008-sem-dbt.md).

## ⚙ Como executar

Os CSVs não são versionados (material da Indicium). Coloque-os em
`1-lh_nautical_csv/` na raiz.

```bash
sudo apt install -y postgresql postgresql-contrib   # uma vez
make setup      # dependências + verificação do ambiente
make db         # cria o banco e aplica o schema da Q2
make carga      # Q3 — carrega os 24 CSVs
make questoes   # roda as 7 questões e confere os números
make pipeline   # silver -> gold -> Parquet para o Power BI
make check      # ruff + mypy + pytest + gate de conformidade
```

`make check` inclui o **gate da questão 2**: um scan por AST que falha se o
script importar qualquer coisa fora da biblioteca padrão.

## 🤝 Como este projeto foi construído

Usei **IA como par de programação** — Claude Code — do início ao fim. Está
declarado nos 36 commits, no [`CLAUDE.md`](CLAUDE.md) e nos agentes em
`.claude/`, porque esconder seria incoerente com um repositório que existe para
mostrar como as decisões foram tomadas.

**O que a IA fez:** escreveu código sob direção, gerou o projeto Power BI a
partir de especificação, produziu documentação e executou as verificações.

**O que foi decisão minha, e está registrado:**

- **As 8 [ADRs](docs/adr/)** — PostgreSQL em vez de DuckDB, sem dbt, medalhão em
  três schemas, postura literal com nota de senioridade, entregáveis
  autocontidos. Cada uma com o contexto, a alternativa descartada e a
  consequência aceita.
- **A calibração visual do dashboard.** Ajustei a primeira página à mão no
  Desktop, com a grade que queria — margem 15, respiro 15, caixas de tamanho
  fixo — e a IA leu as posições de volta do arquivo para replicar nas outras
  quatro. A régua é minha.
- **O controle de qualidade.** Vários defeitos que chegaram ao Power BI só
  apareceram porque eu abri, olhei e apontei: barras desproporcionais, títulos
  sobrepostos, componentes com rolagem, um card cujo rótulo não dizia do que se
  tratava. Cada um virou uma regra no validador.

**Por que isso importa para quem avalia:** o julgamento técnico é a parte que
não terceirizei. As 46 conferências adversariais existem porque decidi que
nenhum número entraria na entrega sem ser recalculado por outro caminho — e foi
assim que três respostas mudaram antes de virarem resposta final.

## 📚 Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/MAPA_QUESTOES.md`](docs/MAPA_QUESTOES.md) | controle central: premissa → entregável → resposta → gate, questão a questão, com cada ambiguidade e a leitura adotada |
| [`docs/SPEC.md`](docs/SPEC.md) | especificação técnica: requisitos, critérios de aceite e o plano por questão |
| [`docs/adr/`](docs/adr/) | as 8 decisões de arquitetura, cada uma com a alternativa descartada |
| [`entregaveis/Q2_schema/perfil.md`](entregaveis/Q2_schema/perfil.md) | perfilamento das 24 tabelas: grão, tipos inferidos, nulos, e as 37 chaves estrangeiras |
| [`entregaveis/Q3_carga/relatorio_carga.md`](entregaveis/Q3_carga/relatorio_carga.md) | relatório da carga: linhas por tabela e as três contagens independentes |
| [`powerbi/MODELO.md`](powerbi/MODELO.md) | star schema da camada gold, relacionamentos e medidas |
| `RESPOSTA.md` de cada questão | resultado, conformidade com a premissa e a leitura de engenharia |

---

**Autor:** [Breno Teodomiro](https://www.linkedin.com/in/breno-teodomiro-power-bi/) · Processo Seletivo Lighthouse 2026 — Indicium
