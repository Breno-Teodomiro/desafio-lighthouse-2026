---
name: armadilhas-dados-lh-nautical
description: Armadilhas do dataset LH Nautical que mudam respostas ou quebram pipelines — verificadas nos 24 CSVs
metadata: 
  node_type: memory
  type: project
  originSessionId: 6b5a842b-ad32-4804-ad5b-7c30614dea9c
  modified: 2026-08-16T01:12:58.439Z
---

Achados do perfilamento completo dos 24 CSVs da LH Nautical (433.424 linhas). A integridade referencial é perfeita (37/37 FKs sem órfãos) e a aritmética fecha ao centavo — a sujeira está nos tipos, nos textos e nas ambiguidades do enunciado.

**Mudam a resposta de uma questão:**
- **"Bússola de Bordo 702" tem dois `product_id`: 74 e 240**, com marcas e categorias diferentes mas descrição idêntica. A Q6 muda de 116 para 76 ou 40 dependendo de como se resolve.
- **A Q7 muda com filtro de status**: sem filtro o top-1 é *Motor de Popa 5331*; com `status='paid'` vira *Vela Mestra 1913*. O primeiro lugar vence por 0,0003 (4ª casa decimal).
- **Só existem 14 categorias** e 1.971 de 2.000 clientes compraram de ≥13 — o "filtro de elite" da Q4 deixa passar 98,5% da base.

**Quebram pipeline:**
- **`payments` faz fan-out 2:1** — 6.999 pedidos têm 2 pagamentos. JOIN com payments duplica faturamento.
- **`order_items` não tem `product_id`** — a cadeia obrigatória é `order_items.product_variant_id → product_variants.product_id → products.category_id`.
- **Colunas que devem ser TEXT** (zeros à esquerda ou estouram int64): `customers.tax_id`, `suppliers.tax_id` (contém `FR-10771657`), `product_variants.barcode_ean`, `fiscal_invoices.series` (`'001'`), `fiscal_invoices.nfe_access_key` (44 dígitos), `addresses.postal_code`, `employees.cpf`, telefones.
- **`stock_levels.reorder_point` é 100% vazia** — inferência de tipo precisa de fallback.
- **7 dos 24 CSVs são CRLF**: fiscal_invoices, order_items, orders, payments, return_items, returns, stock_movements.
- **`stock_movements.quantity` é negativa em 103.577 de 115.312 linhas** por convenção de sinal — rejeitar negativos apaga 90% da tabela.
- **`purchase_orders` mistura BRL/USD/EUR sem tabela de câmbio** — soma de gasto de compra é inválida sem fonte externa.
- Nulos aparecem como string vazia **e** como lixo textual: `?`, `??`, `-`, `--`, `—`, `...`, `n/a`, `TBD`, `TODO`, `FIXME`, `asdf`, `test`, `xxx`, `Sem Nome`.
- **Datas chegam a 2027-02-13**, não 2026 como diz o enunciado. 8,7% dos pedidos são futuros.
- `placed_at == created_at == updated_at` em 100% de `orders` — não existe ciclo de vida do pedido.

Ver também [[numeros-validados-lighthouse]].
