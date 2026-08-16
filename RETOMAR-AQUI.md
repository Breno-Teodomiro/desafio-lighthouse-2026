# ▶ Retomar aqui

**Atualizado:** 16/08/2026 · **Prazo final: 17/08/2026 08h**

> **Vai entregar agora?** Vá direto para **[`ENTREGA.md`](ENTREGA.md)** — tem o
> mapa campo-a-campo do formulário, as 4 respostas objetivas e o checklist
> final. Este arquivo é o estado técnico do projeto.

---

## Estado: as 7 questões estão prontas ✅

| Onda | Escopo | Situação |
|---|---|---|
| 0 | Fundação, docs, ADRs | ✅ |
| 1 | **Q2** schema · **Q3** carga | ✅ |
| 2 | **Q1** EDA | ✅ |
| 3 | **Q4** clientes · **Q5** calendário | ✅ |
| 4 | **Q6** previsão · **Q7** recomendação | ✅ |
| 5 | silver + gold + **dashboard PBIP** | ✅ *(falta abrir no Desktop)* |
| 6 | Empacotamento e revisão adversarial | ✅ |

**46 conferências adversariais aprovadas** (`make verificar`): cada resposta
recalculada pela tecnologia **oposta** à do entregável — Q1/Q4/Q5 saíram em
SQL e foram refeitas em Python sobre os CSVs; Q6/Q7 saíram em pandas/numpy e
foram refeitas em SQL sobre o banco.

`make check` limpo: gate stdlib da Q2, ruff, mypy e validação do PBIP.

---

## ⛔ A única pendência: abrir o dashboard no Power BI Desktop

O projeto `powerbi/lh_nautical.pbip` foi **gerado por script e validado por
script**, mas **nunca foi aberto** — não há Power BI Desktop nesta máquina.

Isso significa que o layout dos visuais foi escrito às cegas. As referências a
campos estão todas corretas (65 conferidas), mas posicionamento, sobreposição e
formatação só se veem renderizados.

**Passos e plano B em [`ENTREGA.md`](ENTREGA.md).**

---

## As 4 respostas objetivas

| Questão | Resposta |
|---|---|
| **1.2** | **R$ 28.704,99** *(28704,992077227642)* |
| **3.2** | **251.864** |
| **6.2** | **116** *(não 117 — arredonda-se a soma, não cada mês)* |
| **7.2** | **Motor de Popa 5331** *(o item de referência é o 1949)* |

---

## Ambiente

- **PostgreSQL 18 do Windows**, banco `lh_nautical`, via rede espelhada do WSL
  (`eth0 = 192.168.0.128`). Funciona; o plano B do `psql.exe` é desnecessário.
- **`.venv` existe** com psycopg 3.3.4, pandas, numpy, sklearn, pyarrow. Fica em
  `/mnt/c`, então `uv sync` do zero leva vários minutos — não refazer sem motivo.
- **`Makefile` faz `include .env`**, então os alvos funcionam sem exportar
  variável à mão.

```bash
make setup · db · carga · questoes · powerbi · check · verificar
```

O banco está carregado: 433.424 linhas em `raw`, mais `silver` e `gold`
construídos. Os Parquets estão em `dados/gold/` (fora do git, como os CSVs).

---

## 🚫 Regras invioláveis

A instância PostgreSQL é **compartilhada com o projeto `BD_ELINSA_COSMOS_EQTL`**.

- Usar **exclusivamente** o banco `lh_nautical`; sempre `-d lh_nautical` explícito.
- Nada de `DROP` / `TRUNCATE` / `ALTER` fora dele.
- Não tocar em `postgresql.conf`, `pg_hba.conf` nem papéis globais.
- O loader da Q3, o `build_silver.sql` e o `build_gold.sql` **abortam** se
  `current_database()` não for `lh_nautical`.

---

## Achados que só apareceram na construção

Coisas que não estavam na documentação inicial e mudaram alguma resposta ou
argumento. Estão detalhadas em `docs/MAPA_QUESTOES.md`.

1. **🔴 A explicação do erro da Q6 estava errada na documentação.** Dizia que o
   modelo falha por "usar meses de baixa (out–dez) para prever o pico do verão".
   Falso: out–nov–dez vale **39,6 un./mês** contra **35,9** de jan–fev–mar — a
   janela é a parte **alta** da série; a baixa é o meio do ano (jul = 8,5).
   As causas reais da subestimação de 44% são a **tendência** (+82% de 2020 a
   2025; o Q1 saiu de 64 para 207 unidades) e **dez/2025 ter sido um ponto fora
   da curva** (22 contra média histórica de 45,6), que numa janela de 3 meses
   carrega 1/3 do peso e sozinho derruba a previsão em 24 unidades no trimestre.

2. **Não existe um único caractere `"` em nenhum dos 24 CSVs.** É isso que torna
   o mapeamento `NULL ''` bijetivo e a contagem de linhas por bytes `\n` válida.
   Se alguém questionar a carga, esta é a resposta.

3. **Os 78 dias sem venda da Q5 são fenômeno histórico:** 25 em 2020, 20, 13,
   11, 6, **1 em 2025**, 2 em 2026. Dia sem venda é característica de operação em
   *ramp-up*. Uma análise restrita a 2025 quase não sofreria o erro do estagiário.

4. **A categoria 13 se chama `SEGURANÇA` em CAIXA ALTA**, destoando das outras
   13. Inconsistência de cadastro; a `silver` normaliza.

5. **Cerca de Tukey da Q1 é 82.597,85** no banco (a nota anterior dizia
   82.598,99, de método de quartil diferente no cálculo por CSV). Os 452 pedidos
   acima dela são os mesmos; nenhuma conclusão muda.

6. **Pedidos futuros mudam com a data de referência** — 4.259 (8,69%) em
   15/08/2026. A consulta emite a data junto, senão o número não é reprodutível.

7. **`purchase_orders.expected_delivery_at` é `DATE`**, não `TIMESTAMP` — com
   `hire_date` e `termination_date`, são as 3 únicas colunas de data pura.

8. **`return_items.quantity` é `NUMERIC(7,3)`**, não inteiro: a fonte mistura
   `5` e `1.000`.

---

## Armadilhas que continuam valendo

- **"Bússola de Bordo 702" tem dois `product_id`: 74 e 240.** Q6 vale 116 / 76 / 40.
- **Q7 troca de resposta com filtro de status.** Sem filtro → *Motor de Popa 5331*;
  4 de 5 recortes → *Vela Mestra 1913*. Gap para o 2º: 0,000314 (0,12%).
- **Q4: o filtro de ≥13 categorias não filtra** — 1.971 de 2.000 (98,5%) passam.
- **Não citar "2027" na Q1** — `orders` termina em 2026-12-31.
- **`payments` faz fan-out 2:1** — join nele infla o faturamento 9,3%.
- **`order_items` não tem `product_id`** — a cadeia passa por `product_variants`.
- **Agrupar a matriz da Q7 por nome faz `asdf` subir a 1º** com 0,278886.

---

## Decisões (não relitigar)

Justificativas em `docs/adr/`.

1. **PostgreSQL do Windows** via rede espelhada. Sem DuckDB, dbt ou Docker.
2. **Medalhão em 3 schemas**: questões saem de `raw`, dashboard sai de `gold`.
3. **Power BI via PBIP/TMDL** com Import de Parquet — nunca conexão viva.
4. **Postura "literal + nota de senioridade"**: responder o que a premissa manda
   e, abaixo, o bloco *Leitura de engenharia* com o cenário corrigido.
5. **Cada questão é autocontida** — um arquivo, roda sozinho.
6. **Tudo em pt-BR.**
7. **Repositório público**; material da prova fora do git (verificado).
