# Relatório de carga — camada raw

Gerado por `q3_carregar_csvs.py` · 2026-08-15 23:45 · 16.0s.

**433.424 linhas carregadas em 24 tabelas.**

## Conferência por tabela

A coluna *CSV* vem da contagem de bytes `\n` no arquivo; a coluna *Banco*
vem do `rowcount` devolvido pelo `COPY`. São dois caminhos independentes —
é isso que torna a conferência uma verificação, e não uma repetição.

| Tabela | Colunas | Terminador | CSV | Banco | |
|---|---:|---|---:|---:|---|
| `addresses` | 12 | LF | 3.998 | 3.998 | ✅ |
| `attributes` | 3 | LF | 8 | 8 | ✅ |
| `brands` | 6 | LF | 12 | 12 | ✅ |
| `categories` | 7 | LF | 14 | 14 | ✅ |
| `customers` | 11 | LF | 2.000 | 2.000 | ✅ |
| `employees` | 11 | LF | 15 | 15 | ✅ |
| `fiscal_invoices` | 11 | CRLF | 34.365 | 34.365 | ✅ |
| `goods_receipt_items` | 4 | LF | 4.733 | 4.733 | ✅ |
| `goods_receipts` | 6 | LF | 1.548 | 1.548 | ✅ |
| `locations` | 14 | LF | 6 | 6 | ✅ |
| `order_items` | 8 | CRLF | 147.320 | 147.320 | ✅ |
| `orders` | 13 | CRLF | 48.998 | 48.998 | ✅ |
| `payments` | 9 | CRLF | 53.546 | 53.546 | ✅ |
| `product_suppliers` | 8 | LF | 1.520 | 1.520 | ✅ |
| `product_variants` | 12 | LF | 1.009 | 1.009 | ✅ |
| `products` | 10 | LF | 500 | 500 | ✅ |
| `purchase_order_items` | 6 | LF | 6.059 | 6.059 | ✅ |
| `purchase_orders` | 13 | LF | 2.000 | 2.000 | ✅ |
| `return_items` | 7 | CRLF | 1.384 | 1.384 | ✅ |
| `returns` | 10 | CRLF | 980 | 980 | ✅ |
| `stock_levels` | 5 | LF | 6.054 | 6.054 | ✅ |
| `stock_movements` | 11 | CRLF | 115.312 | 115.312 | ✅ |
| `suppliers` | 12 | LF | 25 | 25 | ✅ |
| `variant_attribute_values` | 3 | LF | 2.018 | 2.018 | ✅ |
| **TOTAL** | | | **433.424** | **433.424** | ✅ |

## Questão 3.2

| Tabela | Linhas |
|---|---:|
| `customers` | 2.000 |
| `orders` | 48.998 |
| `order_items` | 147.320 |
| `payments` | 53.546 |
| **TOTAL** | **251.864** |

**Resposta: 251.864**

## Garantias da carga

- Transação única: qualquer divergência de contagem levanta exceção **antes** do `COMMIT` e desfaz tudo.
- `COPY ... FROM STDIN` alimentado com bytes: nenhum valor é decodificado, interpretado ou reserializado pelo Python.
- `TRUNCATE` nominal nas 24 tabelas da camada `raw`, o que torna a carga idempotente — rodar duas vezes produz o mesmo estado.
- `SET CONSTRAINTS ALL DEFERRED`: as 37 chaves estrangeiras são validadas em bloco no `COMMIT`.
- Nenhum tratamento de dado: tokens como `?`, `n/a`, `TBD` e `asdf` estão no banco exatamente como estão na fonte.
