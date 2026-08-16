# Dashboard LH Nautical — modelo e leitura

Material complementar obrigatório do desafio. Projeto **PBIP** (Power BI Project), gerado por script a partir da camada `gold`.

```bash
make powerbi        # gold -> Parquet -> PBIP, e valida
```

Depois, abra `lh_nautical.pbip` no **Power BI Desktop** com o preview *Power BI Project (.pbip) save option* ligado, e exporte o `.pbix` / PDF.

---

## Por que PBIP gerado por script, e não um `.pbix` clicado

O modelo tem 15 tabelas e 19 medidas. Três razões:

1. **As colunas do TMDL são derivadas do schema real dos Parquets.** Se o `gold` mudar, o modelo muda junto — em vez de alguém descobrir meses depois que uma medida aponta para uma coluna renomeada.
2. **O projeto inteiro é texto**, versionado no git e revisável em diff. É a razão de o formato PBIP existir.
3. **Os `lineageTag` são GUIDs determinísticos** (hash do nome do objeto), então regerar não produz um diff de milhares de identificadores aleatórios.

## Por que Import de Parquet, e não conexão ao PostgreSQL

O arquivo entregue precisa abrir na máquina de quem corrige, e essa máquina não tem acesso ao PostgreSQL local deste projeto. Um relatório com conexão viva chegaria vazio e sem como atualizar.

O Parquet ainda preserva os tipos — o CSV devolveria tudo como texto e exigiria reinferência no Power Query.

A pasta de origem é um **parâmetro** (`PastaDados`): abrir o projeto em outra máquina é trocar um valor, não reescrever a origem de 14 tabelas.

---

## O modelo

```
              dim_data ──┐
           dim_cliente ──┤
           dim_produto ──┼──► fct_item_pedido    147.320 · grão: LINHA DE ITEM
             dim_local ──┤
             dim_canal ──┤
     dim_status_pedido ──┴──► fct_pedido          48.998 · grão: PEDIDO

                             fct_pagamento        53.546 · ISOLADO
                             fct_venda_diaria_pos  2.557 · grão: DIA (denso)
                             fct_previsao_bussola     84 · Q6
                             fct_similaridade_produto 499 · Q7
```

### Três decisões de modelagem que carregam o modelo

**1. Dois fatos de venda, com grãos diferentes.** `orders.total` é do grão pedido. Se morasse em `fct_item_pedido`, o valor se repetiria por item e qualquer soma inflaria **3,67×** (R$ 5,16 bi em vez de R$ 1,41 bi). Ticket médio e contagem saem sempre de `fct_pedido`; mix, categoria e margem saem sempre de `fct_item_pedido`. **Separar os grãos é o que impede o erro — nenhuma medida DAX precisa "tomar cuidado".**

Os dois fatos **não se relacionam entre si**. Conversam pelas dimensões compartilhadas.

**2. `fct_pagamento` fica isolado, sem nenhum relacionamento.** `payments` faz fan-out 2:1 — 6.999 pedidos têm dois pagamentos. Relacioná-lo faria um filtro de método de pagamento inflar o faturamento em **9,3%**. Ele existe para responder perguntas *sobre pagamento* e nada mais. A ausência do relacionamento está documentada no `relationships.tmdl` para que ninguém a "conserte".

**3. `dim_status_pedido` com `eh_receita_efetivada`.** 14,7% do GMV são pedidos `cancelled` ou `draft`. Em vez de enterrar a decisão "o que conta como receita" num `WHERE`, ela vira atributo e o leitor decide no slicer. **É a diferença entre um número que alguém precisa defender e um número que o leitor consegue interrogar.**

---

## As medidas que merecem explicação

| Medida | Por que importa |
|---|---|
| **Média de Venda por Dia POS** | A medida da Questão 5. O denominador é `COUNTROWS(fct_venda_diaria_pos)` — o fato é **denso**, então conta todos os 2.557 dias do calendário, inclusive os 78 sem venda. |
| **Média por Dia (só dias com venda)** | O erro do estagiário, reproduzido **de propósito**. Divide só pelos dias com venda. Aponta Segunda-feira; a medida correta aponta Quinta-feira. As duas lado a lado são o visual mais importante do painel. |
| **Ticket Médio** | `Receita Bruta / Nº Pedidos`, ambos de `fct_pedido`. Imune ao fan-out de itens e de pagamentos por construção. |
| **Taxa de Cancelamento** | Usa `ALL(dim_status_pedido)` no denominador, para continuar correta com o slicer de status aplicado. |
| **Margem Líquida R$** | Já traz o desconto do pedido rateado pela participação da linha. A soma do rateio reproduz `orders.discount_amount` **ao centavo** — validado no `build_silver.sql`, com o resíduo de arredondamento absorvido na maior linha de cada pedido. |

**Referências que o dashboard deve reproduzir:**

| | |
|---|---|
| GMV (todos os status) | R$ 1.406.487.201,80 |
| Receita de itens | R$ 1.437.204.604,96 |
| Margem bruta | R$ 611.945.739,58 · **42,58%** |
| Desconto | R$ 30.717.403,16 |
| Margem líquida | R$ 581.228.336,42 · **40,44%** |

---

## As 5 páginas

Todo **título de visual é uma frase de conclusão**, não um rótulo: *"Quinta-feira é o pior dia — mas por apenas 10%"* em vez de *"Média por dia da semana"*. Um rótulo obriga o leitor a descobrir sozinho o que o gráfico quer dizer, e metade descobre errado. Uma conclusão transforma o visual em evidência de uma afirmação — e deixa o leitor livre para discordar dela olhando o gráfico.

| Página | O que sustenta |
|---|---|
| **Sumário executivo** | O aviso de leitura no topo: 14,7% do GMV nunca virou receita, 8,7% dos pedidos são futuros. Cartões, série temporal, mix de status e o slicer que muda tudo. |
| **Vendas e margem** | Grão de item. Receita e margem por categoria **não seguem a mesma ordem** — a que mais vende não é a que mais dá lucro. |
| **Clientes (Q4)** | Os 10 fiéis, com a crítica ao critério em destaque: 98,5% da base passa no filtro de diversidade. O gráfico de dispersão mostra que ticket alto ≠ cliente valioso. |
| **Sazonalidade (Q5)** | As duas médias lado a lado, e ao lado a distribuição dos dias vazios que explica a inversão. Mais o achado de que dia sem venda é fenômeno de *ramp-up*. |
| **Previsão e recomendação (Q6-Q7)** | Realizado × 3 modelos na mesma série. Similaridade e co-ocorrência de cesta lado a lado, mostrando que a resposta muda com a formulação. |

---

## Validação

`tests/validar_pbip.py` roda em `make check` e confere, sem precisar do Power BI:

1. Todo JSON do relatório faz parse.
2. Toda tabela referenciada por um visual existe no modelo.
3. Toda coluna referenciada por um visual existe naquela tabela.
4. Toda medida referenciada existe em `_Medidas`.
5. Toda coluna citada em DAX existe.
6. Todo lado de todo relacionamento aponta para coluna existente.
7. Toda tabela do TMDL tem partição e Parquet correspondente.
8. As páginas de `pages.json` existem no disco.

Estado atual: **15 tabelas · 19 medidas · 16 relacionamentos · 5 páginas · 48 visuais · 65 referências, todas resolvidas.**

> ⚠️ **O que a validação NÃO cobre:** se o TMDL de fato abre no Power BI Desktop. Isso exige o Desktop, que não está instalado nesta máquina. O projeto foi gerado seguindo o formato de projetos PBIP existentes do autor (mesma versão de schema, mesmas convenções de TMDL), mas **precisa ser aberto e conferido visualmente antes da entrega** — posicionamento de visuais e formatação são o tipo de coisa que só se vê renderizada.
