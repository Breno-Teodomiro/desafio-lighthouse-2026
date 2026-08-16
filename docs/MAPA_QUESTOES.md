# Mapa de Questões — controle de entrega

Documento de controle central. Cada questão só é marcada ✅ depois que o **gate de conformidade** passa: a premissa literal do enunciado foi respeitada E o número foi confirmado por dois caminhos independentes.

Legenda de status: ⬜ não iniciada · 🟨 em andamento · ✅ concluída e conferida

---

## Q1 — EDA · SQL

| | |
|---|---|
| **Status** | ⬜ |
| **Premissas literais** | Usar **apenas** a tabela `orders` · **Não** fazer limpeza ou tratamento · Apenas observar, agregar e descrever · Código **em SQL** |
| **Entregável** | `entregaveis/Q1_eda/q1_eda_orders.sql` + `RESPOSTA.md` |
| **Gate** | Nenhum JOIN com outra tabela. Nenhum filtro de `status`. Nenhum WHERE que descarte linha. |

**Respostas esperadas** (pré-validadas nos CSVs):

| Item | Valor |
|---|---|
| Total de linhas | **48.998** |
| `created_at` mínima | **2020-01-01 01:19:28** |
| `created_at` máxima | **2026-12-31 23:43:09** |
| `total` mínimo | **32,62** |
| `total` máximo | **127.262,02** |
| **Q1.2 — `total` médio** | **28.704,992077** → apresentar como **R$ 28.704,99** |

**Q1.3 — munição para o diagnóstico.** Tese: **estruturalmente confiável, semanticamente não pronta.**

*(a) Outliers existem estatisticamente, mas não são defeito.*
- Amplitude 32,62 → 127.262,02 (3.901×), o que parece alarmante isolado.
- Mas **média 28.704,99 ≈ mediana 25.917,84** (razão 1,11). A distribuição é quase simétrica, sem cauda pesada.
- Apenas **452 pedidos (0,92%)** acima da cerca de Tukey (82.598,99), somando **2,94% da receita**. Nenhum `total` ≤ 0.
- Veredito: tickets legítimos de alto valor (motores, eletrônica). **Não remover — segmentar.**
- Observação de faro: ticket quase simétrico é *atípico* em varejo, onde se espera log-normal com cauda longa. Sugere geração sintética e recomenda cautela ao extrapolar conclusão de negócio.

*(b) A tabela em si está limpa.*
- Única coluna nula é `salesperson_id`: 24.131 (49,2%), e **100% desses nulos são do canal `ecommerce`**. É ausência estrutural (venda sem vendedor), não falha de coleta — preencher com `COALESCE` seria inventar dado.
- Zero `id` e zero `order_number` duplicados. **Nenhum token de lixo textual em `orders`** (`?`, `n/a`, `asdf` aparecem em outras tabelas).
- `subtotal − discount_amount = total` fecha em **48.998/48.998**. `discount_amount` = 0,00 em 74,6% — plausível.

*(c) Os três bloqueadores reais.*
1. **A média mistura coisas diferentes.** Os R$ 28.704,99 somam 4 estágios do ciclo de vida. GMV bruto = **R$ 1.406.487.201,80**, dos quais **R$ 207,1 mi (14,7%)** são `cancelled` (4.847) + `draft` (2.451) e nunca viraram receita. O ticket médio realizado (`paid`) é **R$ 28.684,45**.
2. **Recorte temporal inválido.** **4.271 pedidos (8,7%)** têm `created_at` posterior a hoje (15/08/2026), indo até 31/12/2026. Qualquer YoY ou tendência que inclua 2026 lê um ano parcial. Exige data de corte explícita.
3. **Os carimbos de tempo não carregam informação.** `placed_at = created_at = updated_at` em **100%** das linhas. Não há linha do tempo do pedido: impossível medir lead time ou tempo até pagamento.

*(d) Veredito.* Confiável como **fonte**; não pronta como **base analítica**. O que falta não é limpeza de sujeira — é **política de negócio**: definir quais status contam como venda, fixar data de corte, e reconhecer que **`orders` sozinha não tem grão de produto** (mix, categoria e margem exigem `order_items → product_variants → products`).

> ⚠️ **Não escrever "2027" na resposta da Q1.** `MAX(created_at)` em `orders` é `2026-12-31 23:43:09` e **não há nenhuma linha de 2027 nesta tabela**. As datas de 2027 existem em `purchase_orders`, `stock_movements`, `returns` e `stock_levels` — fora do escopo permitido pela questão.

---

## Q2 — Schema · Python stdlib

| | |
|---|---|
| **Status** | ⬜ |
| **Premissas literais** | Todos os CSVs como fonte · **Python 3 obrigatório** · **Somente biblioteca padrão** (pandas/dask/polars = **desconsiderado**) · Destino **PostgreSQL** |
| **Entregável** | `entregaveis/Q2_schema/q2_gerar_schema.py` + `schema.sql` + `RESPOSTA.md` |
| **Gate** | Scan por AST: zero `import` fora da stdlib. Script roda com `python3 q2_gerar_schema.py` sem instalar nada. |

**Deve produzir:** 24 `CREATE TABLE` para PostgreSQL, com tipos inferidos dos dados.

**Casos que a inferência precisa acertar:**

| Situação | Colunas | Tipo correto |
|---|---|---|
| Zeros à esquerda | `customers.tax_id` (223), `addresses.postal_code` (191), `product_variants.barcode_ean` (85), `fiscal_invoices.series` (`'001'`), `employees.cpf`, telefones | `TEXT` — nunca inteiro |
| Estoura `BIGINT` | `fiscal_invoices.nfe_access_key` (44 dígitos) | `TEXT` |
| Alfanumérico misto | `suppliers.tax_id` (`FR-10771657`, `IT-515800274`) | `TEXT` |
| 100% vazia | `stock_levels.reorder_point` | fallback declarado (`TEXT` nullable) |
| Boolean | 10 colunas `is_*` com `TRUE`/`FALSE` | `BOOLEAN` |
| Timestamp | 39 colunas `YYYY-MM-DD HH:MM:SS` | `TIMESTAMP` |
| Data pura | `employees.hire_date`, `employees.termination_date`, `purchase_orders.expected_delivery_at` | `DATE` |
| Decimal | preços, custos, quantidades fracionárias | `NUMERIC` |
| PK composta (sem `id`) | `product_suppliers`, `stock_levels`, `variant_attribute_values` | PK de 2 colunas |

---

## Q3 — Carregamento · Python

| | |
|---|---|
| **Status** | ⬜ |
| **Premissas literais** | Carregar **todos** os CSVs · Python 3 · Qualquer biblioteca permitida · **Não** remover nulos nem corrigir caracteres especiais |
| **Entregável** | `entregaveis/Q3_carga/q3_carregar_csvs.py` + `relatorio_carga.md` + `RESPOSTA.md` |
| **Gate** | Contagem por tabela idêntica ao `wc -l` do CSV. Nenhuma transformação de valor. Lixo textual (`?`, `TBD`, `asdf`) preservado como está. |

**Q3.2 — resposta:**

| Tabela | Linhas |
|---|---|
| customers | 2.000 |
| orders | 48.998 |
| order_items | 147.320 |
| payments | 53.546 |
| **TOTAL** | **251.864** |

**Cuidados:** 7 arquivos são CRLF (fiscal_invoices, order_items, orders, payments, return_items, returns, stock_movements) — o `\r` não pode vazar para o último campo. String vazia deve virar `NULL` ou `''` de forma **declarada e consistente**, sem "tratar" o dado.

---

## Q4 — Clientes de elite · SQL

| | |
|---|---|
| **Status** | ⬜ |
| **Premissas literais** | Faturamento = soma de `orders.total` por cliente · Frequência = contagem de transações · Ticket médio = faturamento / frequência · Diversidade = `COUNT(DISTINCT category_id)` · **Filtro: ≥ 13 categorias** · Desempate por `customer_id` crescente |
| **Entregável** | `entregaveis/Q4_clientes/q4_clientes_elite.sql` + `RESPOSTA.md` |
| **Gate** | Nenhum JOIN com `payments`. Ticket médio calculado antes de qualquer join com itens. Top 10 exato. |

**Resposta pré-validada (literal, sem filtro de status):**

| # | customer_id | Ticket médio | Freq. | Categorias |
|---|---|---|---|---|
| 1 | **22** | 41.839,94 | 26 | 14 |
| 2 | 1477 | 41.648,30 | 22 | 14 |
| 3 | 929 | 41.645,23 | 26 | 14 |
| 4 | 1116 | 40.983,58 | 16 | 14 |
| 5 | 1691 | 40.773,56 | 20 | 14 |
| 6 | 774 | 40.340,44 | 18 | 14 |
| 7 | 1470 | 40.021,27 | 26 | 14 |
| 8 | 1599 | 39.904,66 | 25 | 14 |
| 9 | 965 | 39.841,05 | 17 | 14 |
| 10 | 1722 | 39.532,94 | 29 | 14 |

**Categoria com maior `SUM(quantity)` no grupo dos 10:** **Hélices** (id 8) com **492** itens. Vice: Coletes Salva-Vidas (393), Eletrônica Náutica (392).

**Q4.2 — pontos a explicar:**
- **Cadeia de chaves:** `orders.customer_id` → `orders.id` = `order_items.order_id` → `order_items.product_variant_id` → `product_variants.product_id` → `products.category_id` → `categories.id`. Note que **`order_items` não tem `product_id`** — a variante é obrigatória no caminho.
- **Crítica ao critério de diversidade:** ele não discrimina. Distribuição real: 11 cat → 2 clientes · 12 cat → 27 · **13 cat → 200** · **14 cat → 1.771**. Ou seja, **1.971 de 2.000 (98,5%)** passam no filtro. O que realmente ordena o ranking é só o ticket médio.
- **Como isolar os Top 10:** a contagem de itens por categoria roda em CTE que faz `INNER JOIN` contra a lista dos 10 `customer_id` já materializada, nunca refiltrando pelo critério de diversidade.
- **Risco de fan-out:** faturamento e frequência saem de `orders` puro; se calculados após o join com `order_items`, o valor de `total` se repete por linha de item e infla o faturamento em ~3×.

---

## Q5 — Dimensão de calendário · SQL

| | |
|---|---|
| **Status** | ⬜ |
| **Premissas literais** | Período entre a menor e a maior data de venda do arquivo · Loja aberta todos os dias · **Apenas `channel = 'pos'`** · Dias sem registro contam como venda = 0 · Média por dia da semana sobre **todos** os dias do calendário · Nome do dia **em português** |
| **Entregável** | `entregaveis/Q5_calendario/q5_dim_calendario.sql` + `RESPOSTA.md` |
| **Gate** | Calendário tem exatamente 2.557 dias. `COALESCE` presente. Nomes em pt-BR sem depender de `lc_time`. |

**Resposta pré-validada** — período `pos`: 2020-01-01 → 2026-12-31, **2.557 dias**, dos quais **78 sem nenhuma venda**.

| Dia | Média COM calendário (correto) | Média SEM calendário (erro do estagiário) |
|---|---|---|
| **Quinta-feira** | **R$ 157.154,32** ← pior | R$ 166.238,38 |
| Domingo | R$ 157.616,13 | R$ 162.974,19 |
| Segunda-feira | R$ 158.241,15 | R$ 161.335,26 ← "pior" |
| Sábado | R$ 164.858,27 | R$ 169.980,98 |
| Terça-feira | R$ 166.118,83 | R$ 169.841,38 |
| Sexta-feira | R$ 170.193,68 | R$ 174.987,87 |
| Quarta-feira | R$ 173.605,44 | R$ 178.481,99 |

**O argumento central da Q5.2:** o diagnóstico **troca de dia**. A quinta-feira tem 20 dias sem venda; ao ignorá-los, o denominador cai de 366 para 346 e a média sobe R$ 9 mil, tirando-a do último lugar. O Sr. Almir fecharia a loja na **segunda-feira**, que na verdade é o 3º pior dia. Ignorar os zeros não "aproxima" a média — ela deixa de ser média de faturamento por dia e vira média condicionada a ter havido venda, que é outra pergunta.

---

## Q6 — Previsão de demanda · Python

| | |
|---|---|
| **Status** | ⬜ |
| **Premissas literais** | Treino até **31/12/2025** · Teste = **1º trimestre de 2026** · Base **mensal** · Produto **"Bússola de Bordo 702"** · Baseline = **média móvel de 3 meses** · Só dados anteriores à data prevista · Métrica **MAE** · Usar products, product_variants, orders, order_items |
| **Entregável** | `entregaveis/Q6_previsao/q6_previsao_demanda.py` + `RESPOSTA.md` |
| **Gate** | Nenhum dado de 2026 entra no cálculo da previsão. Dataset unificado explícito. MAE calculado sobre os 3 meses. |

⚠️ **"Bússola de Bordo 702" existe duas vezes em `products.csv`:**

| product_id | brand_id | category_id | Descrição |
|---|---|---|---|
| **74** | 12 | 8 | Bússola magnética líquida com iluminação |
| **240** | 8 | 7 | Bússola magnética líquida com iluminação |

**Vendas mensais (unidades):**

| Cenário | out/25 | nov/25 | dez/25 | MM3 → previsão/mês | **Q1/26 previsto** | Q1/26 real |
|---|---|---|---|---|---|---|
| Só id 74 | 26 | 36 | 14 | 25,33 | **76** | 156 |
| Só id 240 | 8 | 24 | 8 | 13,33 | **40** | 51 |
| **Ambos (74+240)** | 34 | 60 | 22 | 38,67 | **116** | 207 |

**Cenário principal:** somar os dois ids — o enunciado nomeia o **produto** pelo nome, e a implementação natural (`products.name == 'Bússola de Bordo 702'`) captura os dois. Escolher um exigiria critério que o enunciado não fornece.

**Segunda ambiguidade — como ler "considerando apenas dados anteriores à data prevista":**

| Esquema | jan / fev / mar | Soma | MAE |
|---|---|---|---|
| **Estático** — MM3 de out/nov/dez-2025, constante no horizonte | 38,67 / 38,67 / 38,67 | **116** | **30,33** |
| Recursivo — realimenta as próprias previsões | 38,67 / 40,22 / 33,63 | 113 | 31,49 |
| Rolling — realimenta os reais do teste | 38,67 / 53,67 / 56,33 | 149 | 19,44 |

**Adotar o estático (116).** Quatro razões: (1) realimentar o real de janeiro faria janeiro virar treino, contradizendo o split que o próprio enunciado declara; (2) a Q6.2 diz "utilizando seu modelo **treinado**" — treina uma vez, aplica ao horizonte; (3) a janela out/nov/dez é estritamente anterior a cada data prevista, satisfazendo a trava de leakage ao pé da letra; (4) é a única leitura que responde à pergunta de negócio — a compra do trimestre é fechada em dezembro, e o comprador não pode esperar o real de janeiro. O rolling tem o menor MAE justamente porque **não é previsão, é backtest que exige conhecer o futuro**.

⚠️ **Arredondamento:** `round(116,00) = 116`, mas `round(38,67) × 3 = 117`. O enunciado pede "a **soma total** da previsão arredondada" → arredondar a soma. **Resposta: 116**, com nota de rodapé sobre o 117.

**Q6.3 / Q6.5 — o que responder:**
- **O baseline não é adequado, e há prova dura disso:** o *seasonal naive* (repetir jan/fev/mar de 2025 — 57, 32, 77) dá **MAE 25,0**, melhor que os **30,33** da MM3. Ou seja, **o baseline pedido perde para simplesmente copiar o ano anterior**. A sazonalidade domina o sinal.
- Prevê 116 contra 207 reais — subestima **44%**. A série tem pico no 1º trimestre todo ano (Q1/24: 43-52-66 · Q1/25: 57-32-77 · Q1/26: 79-68-60) e vale no meio do ano; usar meses de baixa (out–dez) para prever o pico do verão erra por construção.
- **Leakage evitado** por: corte físico do dataset em 31/12/2025 antes de qualquer estatística; janela tocando só meses de treino; sem realimentação com o real; índice mensal denso construído a partir do range de **treino**, para que mês vazio de 2026 não entre; e uso de `orders.created_at`, não `payments.paid_at` (que embutiria informação posterior ao evento previsto).
- **Limitações:** ignora tendência e sazonalidade; emite um único número para todo o horizonte, inútil para escalonar compra mês a mês; janela curta em série ruidosa (média 27,3 un./mês, desvio 18,0) — dezembro/25 = 22 puxa a média sozinho; sem intervalo de confiança; e o "produto" é mal definido (dois SKUs com o mesmo nome).
- **Próximo passo:** seasonal naive como piso, depois SARIMA ou LightGBM com features de mês/lag, avaliados em *rolling origin* de 12 janelas em vez de um split único.

---

## Q7 — Sistema de recomendação · Python

| | |
|---|---|
| **Status** | ⬜ |
| **Premissas literais** | Matriz cliente × produto **binária** (1 se comprou, 0 se não) · **Ignorar quantidade** · **Similaridade de cosseno** produto × produto · Item de referência **"Motor de Popa 1949"** · Top 5, **excluindo o próprio** · Libs: pandas, numpy, sklearn (opcional) |
| **Entregável** | `entregaveis/Q7_recomendacao/q7_recomendacao.py` + `RESPOSTA.md` |
| **Gate** | Matriz só com 0 e 1. Similaridade em nível de **produto**, não de variante. Item de referência ausente do ranking final. |

"Motor de Popa 1949" = **product_id 180** (único, sem homônimo).

**Resposta pré-validada (literal, sem filtro de status):**

| # | Produto | product_id | Cosseno |
|---|---|---|---|
| **1** | **Motor de Popa 5331** | 389 | **0,256553** |
| 2 | Cabo Náutico 2105 | 295 | 0,256239 |
| 3 | Vela Mestra 1913 | 75 | 0,255785 |
| 4 | Cabo Náutico 9048 | 337 | 0,239332 |
| 5 | GPS Plotter 6249 | 55 | 0,237744 |

⚠️ **Sensibilidade — o 1º lugar é frágil.** Gap para o 2º: **0,00031** (0,12% relativo). Qualquer filtro de status inverte:

| Recorte | Top-1 | sim. |
|---|---|---|
| **todos os status (adotado)** | **Motor de Popa 5331** | 0,256553 |
| exclui `draft` | Vela Mestra 1913 | 0,24336 |
| exclui `cancelled` | Vela Mestra 1913 | 0,25879 |
| `paid` + `confirmed` | Vela Mestra 1913 | 0,24520 |
| só `paid` | Vela Mestra 1913 | 0,20459 |

**Decisão:** o enunciado é explícito em todas as outras regras e **não menciona status** → leitura literal é a resposta principal, com a tabela acima documentada na Q7.3.

⚠️ **Armadilha de implementação:** agrupar a matriz por **nome** em vez de `product_id` funde os homônimos e faz **`asdf` subir a #1 com 0,2789** — artefato puro de juntar dois produtos de lixo sem relação. Sempre agrupar por `product_id`; mapear id→nome só na renderização.

**Q7.3 — o que responder:**
- **Construção:** join `order_items → orders` (para `customer_id`) e `order_items → product_variants → products` (para subir de variante a produto). Matriz 2.000 × 500 por presença (`crosstab > 0`), densidade **13,55%** — cada produto tem em média 271 compradores.
- **Significado do cosseno:** com vetores binários, `cos(i,j) = |Ci ∩ Cj| / √(|Ci|·|Cj|)` — clientes que compraram **ambos**, normalizado pela popularidade (coeficiente de Ochiai). Sem a normalização o campeão seria sempre o mais vendido; com ela, mede-se **afinidade de público**. Não é co-ocorrência no mesmo carrinho: é sobreposição de base de clientes ao longo de todo o histórico.
- **Não há sinal real, e dá para provar:** as 499 similaridades do item de referência têm média 0,167 e desvio 0,037. O top-1 está a **2,41 desvios**, e os três primeiros a 2,41 / 2,40 / 2,39 — **estatisticamente indistinguíveis**. Com densidade de 13,55%, quase todo par co-ocorre por acaso. Conclusão honesta: **não mandar para produção como está.**
- **Grão errado para a pergunta da Marina:** "quem comprou isso também levou" é associação **de cesta (mesmo pedido)**, não de cliente ao longo de anos. Um cliente que comprou motor em 2021 e vela em 2025 não indica cross-sell.
- **Outras limitações:** cold start (produto novo tem vetor nulo); viés de popularidade mitigado mas não eliminado; ignora quantidade, preço, recência e devolução (item devolvido conta como compra); sem avaliação offline (o correto seria segurar as últimas compras e medir precision@5 contra baseline de popularidade).
- **Bônus de alto valor (~15 linhas):** co-ocorrência no **mesmo pedido**. Dos 435 pedidos que contêm o Motor de Popa 1949, o item mais frequente junto é **Tinta Antifouling 3228** (11 pedidos). Também sem sinal forte, mas é a formulação **correta** do problema descrito pela Marina — mostrar as duas lado a lado, explicando a diferença de grão, é o que separa um 7 de um 9.

---

## Campo 20 — Material complementar

| | |
|---|---|
| **Status** | ⬜ |
| **Premissa literal** | *"O que deve ser entregue: **Dashboard** (Power BI, Looker Studio, Tableau, etc.)"* — **obrigatório** |
| **Entregável** | `powerbi/lh_nautical.pbix` + PDF exportado + link do repositório |
| **Opcionais** | Notebooks comentados, relatório PDF, documento de análises |

O enunciado sugere explicitamente três visuais: ranking de prejuízo por produto, clientes por lucro acumulado, e vendas médias por dia da semana considerando dias sem venda. As duas últimas mapeiam direto em Q4 e Q5.
