# Especificação técnica

Design de implementação por questão. As respostas e premissas estão em [`MAPA_QUESTOES.md`](MAPA_QUESTOES.md); aqui está **como** construir.

---

## Q2 — Gerador de schema (`q2_gerar_schema.py`)

Arquivo único. Imports permitidos e **exaustivos**: `argparse`, `csv`, `dataclasses`, `datetime`, `os`, `pathlib`, `re`, `sys`, `collections`. Nada mais — `make gate-q2` faz scan por AST e falha se algo escapar.

### CLI

```
python3 q2_gerar_schema.py --entrada ./1-lh_nautical_csv --saida schema.sql
    [--schema raw] [--amostra 0] [--varchar bucket|texto]
    [--sem-fk] [--not-null] [--indices] [--relatorio perfil.md]
```

### Seções do arquivo

```
§1 CONSTANTES     FORCE_TEXT_NAMES, FK_OVERRIDES, FK_IGNORAR, VARCHAR_BUCKETS
§2 PERFILAMENTO   @dataclass PerfilColuna; perfilar_arquivo() — 1 passada, memória O(1)
§3 INFERÊNCIA     inferir_tipo(perfil) — a cascata
§4 CHAVES         inferir_pk(), inferir_fks()
§5 RENDERIZAÇÃO   render_create_table(), render_fks(), render_cabecalho()
§6 CLI            main()
```

`PerfilColuna` acumula em streaming: `n_total`, `n_vazio`, `len_max`, `tem_zero_a_esquerda`, `so_inteiro`, `so_decimal`, `escala_max`, `digitos_inteiros_max`, `maior_abs`, `so_booleano`, `so_data`, `so_timestamp`, `amostras[:5]`. **Nunca guardar a lista de valores** — `stock_movements` tem 115 mil linhas × 11 colunas.

### Cascata de inferência — a ordem é o algoritmo

```
0. n_total == n_vazio                    -> TEXT
     stock_levels.reorder_point (6.054/6.054 vazias). Sem evidência, sem palpite.
     Comentar no DDL: "coluna 100% vazia na fonte; tipo indeterminável"
1. nome em FORCE_TEXT_NAMES              -> VARCHAR(bucket)
     Anulação SEMÂNTICA: são códigos, não medidas. Ninguém soma um CPF.
     {tax_id, cpf, cnpj, phone, postal_code, barcode_ean, series, nfe_access_key,
      nfe_number, ncm_code, state_registration, sku, supplier_sku}
     Necessária porque employees.cpf e suppliers.phone NÃO têm zero à esquerda
     e escapariam da regra 2.
2. tem_zero_a_esquerda                   -> VARCHAR(bucket)
     Anulação ESTRUTURAL: '0812356442423' != 812356442423.
     Detecção: len(v) > 1 and v[0] == '0' and v[1] != '.'
3. so_booleano {TRUE,FALSE,true,false}   -> BOOLEAN
4. so_data      ^\d{4}-\d{2}-\d{2}$      -> DATE
5. so_timestamp ^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$  -> TIMESTAMP
6. so_inteiro:
     digitos_max > 18            -> TEXT      (estoura bigint => é identificador)
     maior_abs <= 2147483647     -> INTEGER
     senão                       -> BIGINT
7. so_decimal                    -> NUMERIC(p, s)
     s = escala_max ; p = digitos_inteiros_max + s + 2   (folga de 2)
8. resto                         -> VARCHAR(bucket), ou TEXT se len_max > 255
```

**Duas decisões que vão documentadas no cabeçalho do script:**

**"Vazio" é só a string vazia.** Tokens como `?`, `n/a`, `TBD`, `asdf` **não** são tratados como nulo — tratá-los seria limpeza, e a Q3 proíbe. A consequência é desejável: um token de lixo "envenena" a coluna para TEXT, que é o resultado honesto. Verificado: **nenhuma coluna numérica é envenenada** — o lixo só aparece em colunas que já são texto.

**`return_items.quantity` é NUMERIC, não INTEGER** — a fonte mistura `5` e `1.000`. A regra 7 pega sozinha. Idem `stock_movements.quantity` → `NUMERIC(11,3)`, negativa.

### VARCHAR vs TEXT

Buckets `{8, 16, 32, 64, 128, 255}`; menor bucket ≥ `len_max`; acima de 255 → `TEXT`. No PostgreSQL não há ganho de performance de `VARCHAR(n)` sobre `TEXT` — o valor de `VARCHAR(n)` é **documentar a expectativa e barrar drift na ingestão**. Flag `--varchar texto` para quem discordar.

### NOT NULL desligado por padrão

Só nas colunas de PK. Justificativa: *nulabilidade inferida de uma única extração é uma restrição falsa; o schema precisa sobreviver a um novo extrato do ERP na semana que vem*. O perfil de nulabilidade vai para o `--relatorio`, onde é informação; no DDL, seria armadilha.

### PK e FK — emitir é diferencial, não risco

**PK:** coluna `id` quando existe. Para as 3 tabelas sem surrogate, **inferir e validar**: testar unicidade da combinação das colunas `*_id` iniciais durante o perfilamento (tabelas pequenas — 1.520 / 6.054 / 2.018 linhas) e imprimir `-- PK composta inferida e validada: N linhas, N combinações distintas`. Constante `PK_COMPOSTAS` como fallback.

**FK:** convenção + anulações. Para toda coluna `*_id` que não seja PK, casar o maior sufixo do radical contra as tabelas singularizadas (`categories→category`, `fiscal_invoices→fiscal_invoice`). Anulações:

```python
FK_OVERRIDES = {
    ("orders", "salesperson_id"):            ("employees", "id"),
    ("purchase_orders", "buyer_id"):         ("employees", "id"),
    ("return_items", "exchange_variant_id"): ("product_variants", "id"),
}
FK_IGNORAR = {("stock_movements", "reference_id")}  # polimórfica: ora orders, ora returns
```

**Por que emitir FK não cria risco de ordem de carga:**
1. As FKs saem em bloco `ALTER TABLE ... ADD CONSTRAINT` **no fim do arquivo**, depois de todos os `CREATE TABLE`.
2. São declaradas **`DEFERRABLE INITIALLY IMMEDIATE`**. O loader da Q3 abre transação, roda `SET CONSTRAINTS ALL DEFERRED`, carrega em qualquer ordem, e o PostgreSQL valida tudo no `COMMIT`.

A integridade é perfeita (37/37, zero órfãos), então as constraints passam. `--sem-fk` fica disponível como escape.

### Layout do `schema.sql`

Cabeçalho com fonte, data, versão e convenções. `BEGIN` … `COMMIT`. Tabelas em ordem alfabética, FKs em `§2`, índices opcionais em `§3`. **Comentário inline por coluna com a evidência que motivou o tipo** (`-- 34.365 valores, todos '001'; zero à esquerda -> VARCHAR`) — é isso que transforma um DDL em documento.

Identificadores sempre entre aspas duplas: protege contra `number`, `value`, `action`, `series`, `total`, `status`, `method`, `currency`, `notes`, `reason`, `role`, `name`. Ler cabeçalhos com `encoding="utf-8-sig"` (BOM defensivo).

---

## Q3 — Loader (`q3_carregar_csvs.py`)

### Driver: psycopg 3

`cursor.copy()` como context manager aceitando `write(bytes)` em streaming; psycopg2 está em modo manutenção. Documentar no README o fallback `psycopg2.copy_expert()`.

### COPY, e o argumento não é velocidade

| Método | 433.424 linhas | Fidelidade |
|---|---|---|
| `executemany` | minutos | Python parseia e re-serializa cada valor |
| `execute_values` | ~10-20 s | idem; NULL vs `''` vira código manual |
| **`COPY ... FROM STDIN`** | **poucos segundos** | **os bytes do arquivo vão direto ao parser do servidor** |

O enunciado diz *"não faça tratamentos"*. Com COPY em streaming de bytes, **o Python nunca decodifica, interpreta ou reserializa um único valor**: sem round-trip por `float64` (que poderia virar `2398.41` em `2398.4100000000001`), sem reinterpretação de acentos, sem decisão sobre `?` ou `asdf`. É a resposta mais forte possível à premissa.

```python
colunas = ", ".join(f'"{c}"' for c in cabecalho_do_csv)
sql = (f'COPY "{schema}"."{tabela}" ({colunas}) FROM STDIN '
       f"WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8')")
with open(caminho, "rb") as fh, cur.copy(sql) as cp:
    while (bloco := fh.read(1 << 20)):
        cp.write(bloco)
```

### Vazio vs NULL é bijetivo aqui

`NULL ''` em `FORMAT csv` converte campo **não-aspado** vazio em NULL e mantém campo **aspado** vazio (`""`) como string vazia. Como **não existe um único caractere `"` em nenhum dos 24 arquivos** (verificado), a fonte não consegue representar "string vazia" distinta de "ausente" — logo o mapeamento não perde informação. Documentar isso fecha a questão antes de ela ser levantada.

### Os 7 arquivos CRLF

`COPY ... FORMAT csv` aceita `\n` e `\r\n` nativamente. Ainda assim, **pré-voo**: ler os primeiros 64 KB e contar `\r\n` vs `\n` isolados; se algum arquivo for **misto**, cair para gerador que normaliza só o terminador de registro. Registrar a coluna "terminador" no relatório. Normalizar separador de registro é decodificação de formato, não tratamento de dado.

### Transação única e idempotência

```
BEGIN
SET datestyle = 'ISO, YMD'
SET client_encoding = 'UTF8'
SET CONSTRAINTS ALL DEFERRED
TRUNCATE t1..t24 RESTART IDENTITY CASCADE
COPY × 24   (ordem topológica — cinto e suspensório)
verificar contagens
COMMIT      (aqui o PostgreSQL valida as 37 FKs de uma vez)
ANALYZE
```

Falha em qualquer ponto → `ROLLBACK`. Rodar duas vezes produz o mesmo resultado. Modo `--dry-run` confere cabeçalho × coluna e conta linhas sem escrever.

**Ordem topológica:** não hardcodar — ler o grafo de `information_schema.referential_constraints`, ignorar auto-referências (`categories.parent_category_id`) e aplicar Kahn. Se sobrar ciclo, ordem alfabética + constraints diferidas resolvem.

### Relatório de verificação

Contar linhas do CSV **pelos bytes** (`sum(bloco.count(b"\n"))`, ajustando newline final ausente), não pelo `csv.reader` — assim as duas contagens são independentes. Divergência levanta exceção **antes** do COMMIT. O relatório é a prova de que 251.864 não foi digitado à mão.

---

## Q1 / Q4 / Q5 — SQL

Ver [`MAPA_QUESTOES.md`](MAPA_QUESTOES.md) para premissas e respostas. Pontos de implementação:

**Q1** — uma consulta principal com as 5 estatísticas, seguida de apêndice `-- DIAGNÓSTICO` com 6 consultas curtas (nulos por coluna, nulos por canal, mix de status, cerca de Tukey, datas futuras, colapso de carimbos). Todas **só em `orders`**. Isso transforma a Q1.3 de opinião em evidência numerada.

**Q4** — três CTEs no mesmo grão, junção 1:1:
- `pedidos_por_cliente`: **nenhum join** — é o que impede o fan-out. `SUM(total)`, `COUNT(*)`, ticket.
- `categorias_por_cliente`: a cadeia de 3 saltos até `products.category_id`.
- `top10_fieis`: `WHERE diversidade >= 13` **antes** do `ORDER BY ticket DESC, customer_id ASC LIMIT 10`.

Segunda consulta usa `top10_fieis` como **tabela dirigente** (semi-join), com `COUNT(DISTINCT customer_id) = 10` embutido como asserção.

Quatro erros que destroem o número, e que a Q4.2 deve citar: somar `total` depois de juntar `order_items` (infla ~3×); qualquer `JOIN payments` (infla ~R$ 200 mi); `COUNT(*)` como frequência dentro da CTE juntada (conta itens, não pedidos); aplicar o filtro de diversidade depois do `LIMIT`.

**Q5** — `generate_series` sobre `MIN`/`MAX` das vendas POS; `CASE` sobre `EXTRACT(ISODOW)` para os nomes em pt-BR; `LEFT JOIN` do calendário para as vendas; `COALESCE(valor, 0)`.

Usar `ISODOW` (1=Seg…7=Dom) e não `DOW` — o `ORDER BY` já sai na ordem da semana brasileira. **Não usar `to_char(d,'TMDay')`**: depende de `lc_time`, devolve `'Monday   '` em servidor padrão (inglês, preenchido até 9 caracteres) e nunca a forma `-feira`.

Incluir no mesmo arquivo a **consulta do estagiário** (média só sobre dias com venda) para a comparação lado a lado — é a alma da questão.

---

## Q6 / Q7 — Python

**Q6**, núcleo que precisa estar certo:

```python
serie = (df_alvo.groupby(df_alvo["data_pedido"].dt.to_period("M"))["quantidade"].sum()
         # CRÍTICO: índice mensal COMPLETO. Sem isso "os últimos 3 meses" pode
         # pular um mês de venda zero e a MM3 sai errada.
         .reindex(pd.period_range("2020-01", "2025-12", freq="M"), fill_value=0)
         .astype("float64"))

treino = serie.loc[:"2025-12"]        # corte duro ANTES de qualquer cálculo
ma3    = treino.iloc[-3:].mean()      # (34 + 60 + 22) / 3 = 38.666...
previsao = pd.Series(ma3, index=pd.period_range("2026-01", "2026-03", freq="M"))
soma = int(round(previsao.sum()))     # 116
```

O `period_range` do treino termina em `2025-12` e não além, para que mês vazio de 2026 não vaze para a janela. A série real do teste vem de objeto separado.

O **dataset unificado** que o enunciado pede (grão: linha de item) é salvo em Parquet e reaproveitado pela Q7 e pela camada gold.

**Q7**, numpy puro — sem sklearn. `cosine_similarity` sobre densa 2000×500 é literalmente `Xn.T @ Xn` após normalizar colunas em L2; escrever a métrica explicitamente demonstra entendê-la, que é o critério declarado do Tech Lead. Deixar bloco opcional que assere `np.allclose` contra sklearn.

```python
matriz = (pd.crosstab(df["customer_id"], df["product_id"]) > 0).astype("float64")
A = matriz.to_numpy()
normas = np.linalg.norm(A, axis=0)
normas[normas == 0] = 1.0            # guarda para produto sem comprador (cold start)
S = (A / normas).T @ (A / normas)    # 500×500, simétrica, diagonal = 1
np.fill_diagonal(S, np.nan)          # descarta o próprio item
```

Nunca agregar por nome — só por `product_id`. Na renderização, rótulo é `nome` quando único e `nome (id=X)` quando duplicado. Se um nome-lixo caísse no top-5, **exibir com marca de alerta**, nunca remover em silêncio: remover seria "limpar" um resultado.

---

## Camada gold

**Dimensões:** `dim_data` (2.557 dias, com `eh_futuro` para `data > 2026-08-15`), `dim_cliente` (com `flag_elite` dos 10 da Q4), `dim_produto` (com `nome_exibicao` e `flag_nome_suspeito`), `dim_variante`, `dim_local`, `dim_canal`, `dim_status_pedido` (com `eh_receita_efetivada` — a dimensão que resolve toda a ambiguidade de status via slicer).

**Fatos:** `fct_item_pedido` (147.320, o fato principal), `fct_pedido` (48.998, só para ticket médio e contagem — evita fan-out), `fct_venda_diaria_pos` (denso via `dim_data`, alimenta a Q5), `fct_pagamento` (**isolado**, nunca relacionado a `fct_item_pedido`), `fct_estoque_atual`, `fct_devolucao`, `fct_previsao_bussola`, `fct_similaridade_produto`.

**Rateio de desconto** (a definição de margem):

```sql
desconto_rateado = o.discount_amount
                 * (oi.line_total / NULLIF(SUM(oi.line_total) OVER (PARTITION BY oi.order_id), 0))
margem_bruta     = oi.line_total - (oi.quantity * pv.cost_price) - desconto_rateado
```

Validação obrigatória: `SUM(desconto_rateado)` por pedido bate com `orders.discount_amount` ao centavo. Usar `numeric`, nunca `float`; absorver o resíduo de arredondamento na maior linha do pedido.

Referências do dataset: `line_total` total = R$ 1.437.204.604,96 · margem bruta antes de desconto = R$ 611.945.739,58 (**42,58%**) · desconto total = R$ 30.717.403,16 → margem líquida ≈ 40,4%.

**11 medidas DAX:** Receita Bruta · Receita Efetivada · Margem Bruta R$ · % Margem · Ticket Médio (sempre de `fct_pedido`) · Nº Pedidos · Taxa de Cancelamento · **Média de Venda por Dia POS** (denominador é o calendário, não os dias com venda — a medida da Q5) · Dias sem Venda · Diversidade de Categorias · Taxa de Devolução.

**5 páginas:** Sumário Executivo (com a área pós-15/08/2026 sombreada e rotulada "dados futuros — 8,7% da base") · Vendas & Margem · Clientes/Q4 · Sazonalidade/Q5 (as duas séries lado a lado, com e sem calendário — o visual mais didático do painel) · Previsão & Recomendação/Q6-Q7.

Todo título é **frase de conclusão**, não rótulo: *"Quinta-feira é o pior dia — mas por apenas 10%"* em vez de *"Média por dia da semana"*.
