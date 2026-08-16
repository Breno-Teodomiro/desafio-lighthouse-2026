.DEFAULT_GOAL := help
SHELL := /bin/bash
CSV_DIR := 1-lh_nautical_csv
PGDB := lh_nautical

.PHONY: help setup db carga questoes pipeline check gate-q2 limpar

help:  ## Mostra os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:  ## Instala dependências (uv) e verifica o ambiente
	uv sync --all-extras
	@echo "--- ambiente ---"
	@uv run python -c "import psycopg, pandas, numpy, sklearn, pyarrow; print('libs OK')"
	@psql --version
	@pg_isready && echo "PostgreSQL respondendo" || echo "ATENÇÃO: PostgreSQL não está no ar"

db:  ## Cria o banco e aplica o schema gerado pela Q2
	createdb $(PGDB) 2>/dev/null || echo "banco $(PGDB) já existe"
	psql -d $(PGDB) -c "CREATE SCHEMA IF NOT EXISTS raw; CREATE SCHEMA IF NOT EXISTS silver; CREATE SCHEMA IF NOT EXISTS gold;"
	psql -d $(PGDB) -v ON_ERROR_STOP=1 -f entregaveis/Q2_schema/schema.sql
	@echo "schema aplicado"

carga:  ## Q3 — carrega os 24 CSVs em raw
	uv run python entregaveis/Q3_carga/q3_carregar_csvs.py --csv-dir $(CSV_DIR) --db $(PGDB)

questoes:  ## Executa as 7 questões e confere os números
	@echo "== Q1 =="; psql -d $(PGDB) -f entregaveis/Q1_eda/q1_eda_orders.sql
	@echo "== Q4 =="; psql -d $(PGDB) -f entregaveis/Q4_clientes/q4_clientes_elite.sql
	@echo "== Q5 =="; psql -d $(PGDB) -f entregaveis/Q5_calendario/q5_dim_calendario.sql
	@echo "== Q6 =="; uv run python entregaveis/Q6_previsao/q6_previsao_demanda.py --csv-dir $(CSV_DIR)
	@echo "== Q7 =="; uv run python entregaveis/Q7_recomendacao/q7_recomendacao.py --csv-dir $(CSV_DIR)

pipeline:  ## raw -> silver -> gold + exporta Parquet para o Power BI
	psql -d $(PGDB) -v ON_ERROR_STOP=1 -f sql/silver/build_silver.sql
	psql -d $(PGDB) -v ON_ERROR_STOP=1 -f sql/gold/build_gold.sql
	uv run python -m lh_nautical.gold.exportar_parquet --db $(PGDB) --saida dados/gold

gate-q2:  ## Prova que a Q2 usa SOMENTE a stdlib (premissa eliminatória)
	@uv run python tests/gate_stdlib.py entregaveis/Q2_schema/q2_gerar_schema.py

check: gate-q2  ## ruff + mypy + pytest + gates de conformidade
	uv run ruff check .
	uv run mypy src/ || true
	uv run pytest -q

limpar:  ## Derruba o banco (destrutivo — pede confirmação)
	@read -p "Apagar o banco $(PGDB)? [s/N] " r; [ "$$r" = "s" ] && dropdb $(PGDB) || echo "cancelado"
