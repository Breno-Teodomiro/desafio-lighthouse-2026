# Questão 2 — Schema

**Entregáveis:** `q2_gerar_schema.py` (Q2.1) · `schema.sql` (Q2.2) · `perfil.md` (relatório de apoio)

```bash
python3 q2_gerar_schema.py --entrada ./1-lh_nautical_csv --saida schema.sql --relatorio perfil.md
```

Roda com o Python do sistema, sem instalar nada e sem ambiente virtual.

---

## Conformidade com a premissa eliminatória

> *"Utilize somente bibliotecas padrão do Python 3 e python puro. Soluções que utilizarem bibliotecas como pandas, dask, polars serão desconsideradas."*

Os 9 imports do script são: `__future__`, `argparse`, `collections`, `csv`, `dataclasses`, `datetime`, `pathlib`, `re`, `sys`. Todos da biblioteca padrão.

Isso não é afirmado — é **verificado por um gate automático** (`tests/gate_stdlib.py`), que percorre a árvore sintática do arquivo, coleta todo import em qualquer profundidade e confere cada módulo raiz contra `sys.stdlib_module_names`. Procurar a string `"pandas"` no arquivo não bastaria: não alcançaria `import numpy as np`, nem `__import__("polars")`, nem um import escondido dentro de uma função. O gate também rejeita carregamento dinâmico de módulo.

```
$ python3 tests/gate_stdlib.py entregaveis/Q2_schema/q2_gerar_schema.py
  Python 3.12.3 · 9 imports encontrados
  APROVADO — apenas biblioteca padrão, sem carregamento dinâmico.
```

---

## O que o script faz

Uma passada por arquivo, memória constante. `PerfilColuna` acumula apenas agregados — nunca a lista de valores, porque `stock_movements` tem 115.312 linhas por 11 colunas e materializar isso trocaria um problema resolvido por um problema de memória.

**Resultado:** 24 tabelas · 212 colunas · 433.424 linhas perfiladas · 37 chaves estrangeiras · 24 chaves primárias.

### A cascata de inferência — a ordem é o algoritmo

| # | Regra | Resultado |
|---|---|---|
| 0 | coluna 100% vazia | `TEXT`, com o motivo no comentário |
| 1 | nome é código de negócio (anulação **semântica**) | `VARCHAR(n)` |
| 2 | tem zero à esquerda (anulação **estrutural**) | `VARCHAR(n)` |
| 3 | só `TRUE`/`FALSE` | `BOOLEAN` |
| 4 | só `YYYY-MM-DD` | `DATE` |
| 5 | só `YYYY-MM-DD HH:MM:SS` | `TIMESTAMP` |
| 6 | só inteiros | `INTEGER` / `BIGINT` / `TEXT` se > 18 dígitos |
| 7 | só decimais | `NUMERIC(p,s)` dimensionado |
| 8 | resto | `VARCHAR(n)`, ou `TEXT` acima de 255 |

Distribuição obtida, conferida no catálogo do PostgreSQL depois de aplicar o DDL: 71 `VARCHAR` · 65 `INTEGER` · 37 `TIMESTAMP` · 25 `NUMERIC` · 10 `BOOLEAN` · 3 `DATE` · 1 `TEXT` = 212 colunas.

### As armadilhas que a cascata precisava acertar

| Coluna | Risco se inferido ingenuamente | Tipo emitido |
|---|---|---|
| `customers.tax_id` | `00429721404` viraria `429721404` | `VARCHAR(16)` |
| `fiscal_invoices.series` | `'001'` viraria `1` | `VARCHAR(8)` |
| `fiscal_invoices.nfe_access_key` | 44 dígitos estouram `BIGINT` | `VARCHAR(64)` |
| `suppliers.tax_id` | `FR-10771657` não é número | `VARCHAR(16)` |
| `employees.cpf` | **não tem zero à esquerda nesta extração** — escaparia da regra 2 | `VARCHAR(16)` |
| `stock_levels.reorder_point` | 6.054 de 6.054 vazias: nada a inferir | `TEXT` + comentário |
| `stock_movements.quantity` | negativa em 103.577 linhas; e é fracionária | `NUMERIC(8,3)` |
| `return_items.quantity` | a fonte mistura `5` e `1.000` | `NUMERIC(7,3)` |

**Por que existe a regra 1 além da regra 2.** A detecção de zero à esquerda é estrutural e resolve a maioria dos casos sozinha, mas `employees.cpf` e `suppliers.phone` não têm um único zero à esquerda *nesta* extração. Confiar só na evidência os transformaria em `BIGINT` por acidente da amostra, e o primeiro CPF iniciado em zero quebraria a carga seguinte. A regra 1 é uma decisão de domínio explícita: **CPF, CEP, EAN e chave de NF-e são códigos, não medidas — ninguém calcula a média de um CPF.**

### Chaves

**Primárias.** `id` quando existe (21 tabelas). As 3 tabelas associativas sem surrogate têm a PK composta **inferida e validada durante o perfilamento** — a unicidade da combinação é contada, e a constraint só é emitida se a contagem bater exatamente:

```
product_suppliers          1.520 linhas, 1.520 combinações distintas
stock_levels               6.054 linhas, 6.054 combinações distintas
variant_attribute_values   2.018 linhas, 2.018 combinações distintas
```

**Estrangeiras.** 34 por convenção de nome, 3 por anulação explícita. O casamento testa o **sufixo mais longo primeiro** — sem isso `purchase_order_item_id` casaria com `order_items` em vez de `purchase_order_items`, e `product_variant_id` procuraria uma tabela `variants` que não existe.

As 3 anulações são colunas cujo nome descreve o **papel**, não o destino: `orders.salesperson_id` → `employees`, `purchase_orders.buyer_id` → `employees`, `return_items.exchange_variant_id` → `product_variants`.

Uma coluna fica **deliberadamente sem FK**: `stock_movements.reference_id` é polimórfica — aponta ora para `orders`, ora para `returns`, conforme o valor de `reference_table` na mesma linha. Não existe FK declarável para isso em SQL padrão, e inventar uma seria simplesmente errado.

**Por que emitir FK não cria risco de ordem de carga:** elas saem em bloco `ALTER TABLE` no fim do arquivo, depois de todos os `CREATE TABLE`, e são `DEFERRABLE INITIALLY IMMEDIATE`. O carregador da Q3 abre a transação com `SET CONSTRAINTS ALL DEFERRED`, carrega em qualquer ordem e o PostgreSQL valida as 37 de uma vez no `COMMIT`. Isso foi verificado na prática: a carga passou.

---

## Duas decisões que merecem justificativa

### "Vazio" é somente a string vazia

A fonte tem tokens de lixo: `?`, `??`, `-`, `--`, `n/a`, `TBD`, `asdf`, `Sem Nome`. **Nenhum deles é tratado como nulo aqui.** Tratá-los seria limpeza de dados, e a etapa seguinte (Q3) proíbe tratamento explicitamente — o schema não pode assumir uma limpeza que a carga tem ordem de não fazer.

A consequência é desejável: um token de lixo "envenena" a coluna e a empurra para texto, que é o tipo honesto para aquele conteúdo. Verificado nesta base: **nenhuma coluna numérica é envenenada** — o lixo só aparece em colunas que já são texto por natureza.

### NOT NULL só nas colunas de chave primária

Nulabilidade inferida de uma única extração é uma restrição falsa. A coluna que veio 100% preenchida hoje pode vir com nulo no extrato da semana que vem, e aí o schema quebra na ingestão — falhando por causa de uma regra que **nós** inventamos, não que o negócio impôs.

O perfil de preenchimento vai para o `perfil.md`, onde é informação útil para quem for modelar a camada seguinte. Dentro do DDL, seria uma armadilha.

Mesmo raciocínio para `VARCHAR(n)`: no PostgreSQL não há ganho de armazenamento ou performance sobre `TEXT`. O valor de `VARCHAR(n)` é documentar a expectativa e barrar drift silencioso na ingestão. Quem discordar tem a flag `--varchar texto`.

---

## Leitura de engenharia

O que a questão pede é o correto para uma camada `raw`: um schema que **espelha a fonte**. Vale registrar o que deliberadamente *não* está aqui, porque em um projeto real seria a próxima conversa.

1. **Este schema não deveria ser o schema analítico.** Ele carrega as decisões do ERP, incluindo as ruins. `reorder_point` como `TEXT` é a resposta certa para `raw` e uma resposta péssima para uma camada de consumo — lá ela deveria ser `INTEGER` nullable, ou não existir. A separação em `raw` / `silver` / `gold` existe justamente para que a honestidade da primeira camada não contamine a usabilidade da última.

2. **`TIMESTAMP` sem fuso é uma dívida assumida.** As 37 colunas temporais não trazem informação de fuso, então `TIMESTAMPTZ` implicaria adotar um fuso que a fonte não declara. Em produção, isso é uma pergunta para o fornecedor do ERP antes de qualquer análise que cruze horários.

3. **A folga de 2 dígitos no `NUMERIC` é um palpite calibrado, não uma medida.** A extração de hoje não é o teto do domínio, e ampliar a precisão de um `NUMERIC` depois exige reescrever a tabela inteira. Dois dígitos custam quase nada e cobrem uma ordem de grandeza de crescimento.

4. **A inferência é boa porque a base é limpa.** Integridade referencial perfeita e formatos consistentes fizeram a cascata acertar nas 212 colunas. Contra um ERP real — com data em três formatos na mesma coluna e `-1` como sentinela de nulo — a cascata precisaria de amostragem estratificada e revisão humana. **Um gerador de schema é uma primeira proposta, não um oráculo**, e é assim que este deve ser lido.
