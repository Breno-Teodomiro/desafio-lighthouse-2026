# Relatório de perfilamento — camada raw

Gerado por `q2_gerar_schema.py` em 2026-08-15 23:44.

**24 tabelas · 433.424 linhas · 37 chaves estrangeiras**

## Visão geral

| Tabela | Linhas | Colunas | Terminador | Chave primária |
|---|---:|---:|---|---|
| `addresses` | 3.998 | 12 | LF | `id` |
| `attributes` | 8 | 3 | LF | `id` |
| `brands` | 12 | 6 | LF | `id` |
| `categories` | 14 | 7 | LF | `id` |
| `customers` | 2.000 | 11 | LF | `id` |
| `employees` | 15 | 11 | LF | `id` |
| `fiscal_invoices` | 34.365 | 11 | CRLF | `id` |
| `goods_receipt_items` | 4.733 | 4 | LF | `id` |
| `goods_receipts` | 1.548 | 6 | LF | `id` |
| `locations` | 6 | 14 | LF | `id` |
| `order_items` | 147.320 | 8 | CRLF | `id` |
| `orders` | 48.998 | 13 | CRLF | `id` |
| `payments` | 53.546 | 9 | CRLF | `id` |
| `product_suppliers` | 1.520 | 8 | LF | `product_variant_id`. `supplier_id` |
| `product_variants` | 1.009 | 12 | LF | `id` |
| `products` | 500 | 10 | LF | `id` |
| `purchase_order_items` | 6.059 | 6 | LF | `id` |
| `purchase_orders` | 2.000 | 13 | LF | `id` |
| `return_items` | 1.384 | 7 | CRLF | `id` |
| `returns` | 980 | 10 | CRLF | `id` |
| `stock_levels` | 6.054 | 5 | LF | `product_variant_id`. `location_id` |
| `stock_movements` | 115.312 | 11 | CRLF | `id` |
| `suppliers` | 25 | 12 | LF | `id` |
| `variant_attribute_values` | 2.018 | 3 | LF | `product_variant_id`. `attribute_id` |

## Colunas

`% preenchido` é informativo: **não** vira NOT NULL no DDL. Ver a nota
no cabeçalho do `schema.sql`.

### `addresses`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 3998 valores inteiros, máximo 3998 |
| `customer_id` | `INTEGER` | 100.0% | 4 | 3998 valores inteiros, máximo 2000 |
| `address_type` | `VARCHAR(16)` | 100.0% | 9 | 3998 valores textuais; len max 9 |
| `postal_code` | `VARCHAR(16)` | 100.0% | 9 | código de negócio, não medida (len max 9); aritmética não se aplica |
| `street` | `VARCHAR(64)` | 100.0% | 35 | 3998 valores textuais; len max 35 |
| `number` | `INTEGER` | 100.0% | 3 | 3998 valores inteiros, máximo 999 |
| `complement` | `VARCHAR(8)` | 41.3% | 8 | 1652 valores textuais; len max 8 |
| `district` | `VARCHAR(64)` | 100.0% | 33 | 3998 valores textuais; len max 33 |
| `city` | `VARCHAR(32)` | 100.0% | 27 | 3998 valores textuais; len max 27 |
| `state` | `VARCHAR(8)` | 100.0% | 2 | 3998 valores textuais; len max 2 |
| `country` | `VARCHAR(8)` | 100.0% | 2 | 3998 valores textuais; len max 2 |
| `is_primary` | `BOOLEAN` | 100.0% | 5 | 3998 valores, todos em {TRUE, FALSE} |

### `attributes`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 1 | 8 valores inteiros, máximo 8 |
| `name` | `VARCHAR(16)` | 100.0% | 10 | 8 valores textuais; len max 10 |
| `data_type` | `VARCHAR(8)` | 100.0% | 7 | 8 valores textuais; len max 7 |

### `brands`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 2 | 12 valores inteiros, máximo 12 |
| `name` | `VARCHAR(16)` | 100.0% | 14 | 12 valores textuais; len max 14 |
| `country` | `VARCHAR(8)` | 58.3% | 2 | 7 valores textuais; len max 2 |
| `is_active` | `BOOLEAN` | 100.0% | 4 | 12 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 12 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 12 valores, todos YYYY-MM-DD HH:MM:SS |

### `categories`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 2 | 14 valores inteiros, máximo 14 |
| `name` | `VARCHAR(32)` | 100.0% | 20 | 14 valores textuais; len max 20 |
| `slug` | `VARCHAR(32)` | 100.0% | 20 | 14 valores textuais; len max 20 |
| `parent_category_id` | `INTEGER` | 78.6% | 1 | 11 valores inteiros, máximo 3 |
| `is_active` | `BOOLEAN` | 100.0% | 4 | 14 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 14 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 14 valores, todos YYYY-MM-DD HH:MM:SS |

### `customers`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 2000 valores inteiros, máximo 2000 |
| `person_type` | `VARCHAR(8)` | 100.0% | 2 | 2000 valores textuais; len max 2 |
| `legal_name` | `VARCHAR(32)` | 100.0% | 32 | 2000 valores textuais; len max 32 |
| `trade_name` | `VARCHAR(32)` | 27.8% | 27 | 555 valores textuais; len max 27 |
| `tax_id` | `VARCHAR(16)` | 100.0% | 14 | código de negócio, não medida (len max 14); aritmética não se aplica |
| `state_registration` | `VARCHAR(16)` | 39.5% | 10 | código de negócio, não medida (len max 10); aritmética não se aplica |
| `email` | `VARCHAR(64)` | 99.8% | 49 | 1996 valores textuais; len max 49 |
| `phone` | `VARCHAR(16)` | 99.8% | 14 | código de negócio, não medida (len max 14); aritmética não se aplica |
| `is_active` | `BOOLEAN` | 100.0% | 5 | 2000 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 2000 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 2000 valores, todos YYYY-MM-DD HH:MM:SS |

### `employees`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 2 | 15 valores inteiros, máximo 15 |
| `full_name` | `VARCHAR(32)` | 100.0% | 25 | 15 valores textuais; len max 25 |
| `cpf` | `VARCHAR(16)` | 100.0% | 11 | código de negócio, não medida (len max 11); aritmética não se aplica |
| `email` | `VARCHAR(64)` | 100.0% | 46 | 15 valores textuais; len max 46 |
| `role` | `VARCHAR(16)` | 100.0% | 11 | 15 valores textuais; len max 11 |
| `primary_location_id` | `INTEGER` | 100.0% | 1 | 15 valores inteiros, máximo 6 |
| `hire_date` | `DATE` | 100.0% | 10 | 15 valores, todos YYYY-MM-DD sem componente de hora |
| `termination_date` | `DATE` | 13.3% | 10 | 2 valores, todos YYYY-MM-DD sem componente de hora |
| `is_active` | `BOOLEAN` | 100.0% | 5 | 15 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 15 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 15 valores, todos YYYY-MM-DD HH:MM:SS |

### `fiscal_invoices`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 5 | 34365 valores inteiros, máximo 35079 |
| `order_id` | `INTEGER` | 100.0% | 5 | 34365 valores inteiros, máximo 50000 |
| `nfe_number` | `VARCHAR(16)` | 100.0% | 12 | código de negócio, não medida (len max 12); aritmética não se aplica |
| `nfe_access_key` | `VARCHAR(64)` | 100.0% | 44 | código de negócio, não medida (len max 44); aritmética não se aplica |
| `series` | `VARCHAR(8)` | 100.0% | 3 | código de negócio, não medida (len max 3); aritmética não se aplica |
| `issued_at` | `TIMESTAMP` | 100.0% | 19 | 34365 valores, todos YYYY-MM-DD HH:MM:SS |
| `status` | `VARCHAR(16)` | 100.0% | 10 | 34365 valores textuais; len max 10 |
| `total_amount` | `NUMERIC(10,2)` | 100.0% | 9 | 34365 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga) |
| `xml_storage_uri` | `VARCHAR(128)` | 100.0% | 69 | 34365 valores textuais; len max 69 |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 34365 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 34365 valores, todos YYYY-MM-DD HH:MM:SS |

### `goods_receipt_items`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 4733 valores inteiros, máximo 4733 |
| `goods_receipt_id` | `INTEGER` | 100.0% | 4 | 4733 valores inteiros, máximo 1548 |
| `purchase_order_item_id` | `INTEGER` | 100.0% | 4 | 4733 valores inteiros, máximo 6059 |
| `quantity_received` | `NUMERIC(7,3)` | 100.0% | 6 | 4733 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga) |

### `goods_receipts`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 1548 valores inteiros, máximo 1548 |
| `purchase_order_id` | `INTEGER` | 100.0% | 4 | 1548 valores inteiros, máximo 2000 |
| `received_by_employee_id` | `INTEGER` | 100.0% | 2 | 1548 valores inteiros, máximo 15 |
| `received_at` | `TIMESTAMP` | 100.0% | 19 | 1548 valores, todos YYYY-MM-DD HH:MM:SS |
| `notes` | `VARCHAR(16)` | 5.0% | 15 | 77 valores textuais; len max 15 |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 1548 valores, todos YYYY-MM-DD HH:MM:SS |

### `locations`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 1 | 6 valores inteiros, máximo 6 |
| `name` | `VARCHAR(16)` | 100.0% | 16 | 6 valores textuais; len max 16 |
| `location_type` | `VARCHAR(16)` | 100.0% | 9 | 6 valores textuais; len max 9 |
| `postal_code` | `VARCHAR(16)` | 100.0% | 9 | código de negócio, não medida (len max 9); aritmética não se aplica |
| `street` | `VARCHAR(32)` | 100.0% | 24 | 6 valores textuais; len max 24 |
| `number` | `INTEGER` | 100.0% | 3 | 6 valores inteiros, máximo 381 |
| `complement` | `VARCHAR(8)` | 50.0% | 7 | 3 valores textuais; len max 7 |
| `district` | `VARCHAR(32)` | 100.0% | 27 | 6 valores textuais; len max 27 |
| `city` | `VARCHAR(32)` | 100.0% | 18 | 6 valores textuais; len max 18 |
| `state` | `VARCHAR(8)` | 100.0% | 2 | 6 valores textuais; len max 2 |
| `country` | `VARCHAR(8)` | 100.0% | 2 | 6 valores textuais; len max 2 |
| `is_active` | `BOOLEAN` | 100.0% | 4 | 6 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 6 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 6 valores, todos YYYY-MM-DD HH:MM:SS |

### `order_items`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 6 | 147320 valores inteiros, máximo 150321 |
| `order_id` | `INTEGER` | 100.0% | 5 | 147320 valores inteiros, máximo 50000 |
| `product_variant_id` | `INTEGER` | 100.0% | 4 | 147320 valores inteiros, máximo 1009 |
| `quantity` | `INTEGER` | 100.0% | 2 | 147320 valores inteiros, máximo 10 |
| `unit_price` | `NUMERIC(8,2)` | 100.0% | 7 | 147320 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga) |
| `icms_rate` | `NUMERIC(6,2)` | 100.0% | 5 | 147320 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga) |
| `ipi_rate` | `NUMERIC(6,2)` | 100.0% | 5 | 147320 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga) |
| `line_total` | `NUMERIC(9,2)` | 100.0% | 8 | 147320 valores decimais; até 5 dígitos inteiros e 2 decimais (+2 de folga) |

### `orders`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 5 | 48998 valores inteiros, máximo 50000 |
| `order_number` | `VARCHAR(16)` | 100.0% | 9 | 48998 valores textuais; len max 9 |
| `channel` | `VARCHAR(16)` | 100.0% | 9 | 48998 valores textuais; len max 9 |
| `customer_id` | `INTEGER` | 100.0% | 4 | 48998 valores inteiros, máximo 2000 |
| `salesperson_id` | `INTEGER` | 50.8% | 2 | 24867 valores inteiros, máximo 10 |
| `location_id` | `INTEGER` | 100.0% | 1 | 48998 valores inteiros, máximo 6 |
| `status` | `VARCHAR(16)` | 100.0% | 9 | 48998 valores textuais; len max 9 |
| `subtotal` | `NUMERIC(10,2)` | 100.0% | 9 | 48998 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga) |
| `discount_amount` | `NUMERIC(9,2)` | 100.0% | 8 | 48998 valores decimais; até 5 dígitos inteiros e 2 decimais (+2 de folga) |
| `total` | `NUMERIC(10,2)` | 100.0% | 9 | 48998 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga) |
| `placed_at` | `TIMESTAMP` | 100.0% | 19 | 48998 valores, todos YYYY-MM-DD HH:MM:SS |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 48998 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 48998 valores, todos YYYY-MM-DD HH:MM:SS |

### `payments`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 5 | 53546 valores inteiros, máximo 54635 |
| `order_id` | `INTEGER` | 100.0% | 5 | 53546 valores inteiros, máximo 50000 |
| `method` | `VARCHAR(16)` | 100.0% | 13 | 53546 valores textuais; len max 13 |
| `installments` | `INTEGER` | 100.0% | 2 | 53546 valores inteiros, máximo 12 |
| `amount` | `NUMERIC(10,2)` | 100.0% | 9 | 53546 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga) |
| `status` | `VARCHAR(8)` | 100.0% | 8 | 53546 valores textuais; len max 8 |
| `paid_at` | `TIMESTAMP` | 77.0% | 19 | 41219 valores, todos YYYY-MM-DD HH:MM:SS |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 53546 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 53546 valores, todos YYYY-MM-DD HH:MM:SS |

### `product_suppliers`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `product_variant_id` | `INTEGER` | 100.0% | 4 | 1520 valores inteiros, máximo 1009 |
| `supplier_id` | `INTEGER` | 100.0% | 2 | 1520 valores inteiros, máximo 25 |
| `supplier_sku` | `VARCHAR(16)` | 98.2% | 13 | código de negócio, não medida (len max 13); aritmética não se aplica |
| `last_quoted_cost` | `NUMERIC(8,2)` | 100.0% | 7 | 1520 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga) |
| `lead_time_days` | `INTEGER` | 100.0% | 2 | 1520 valores inteiros, máximo 45 |
| `is_preferred` | `BOOLEAN` | 100.0% | 5 | 1520 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 1520 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 1520 valores, todos YYYY-MM-DD HH:MM:SS |

### `product_variants`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 1009 valores inteiros, máximo 1009 |
| `product_id` | `INTEGER` | 100.0% | 3 | 1009 valores inteiros, máximo 500 |
| `sku` | `VARCHAR(16)` | 100.0% | 10 | código de negócio, não medida (len max 10); aritmética não se aplica |
| `barcode_ean` | `VARCHAR(16)` | 84.4% | 13 | código de negócio, não medida (len max 13); aritmética não se aplica |
| `sale_price` | `NUMERIC(8,2)` | 100.0% | 7 | 1009 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga) |
| `cost_price` | `NUMERIC(8,2)` | 100.0% | 7 | 1009 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga) |
| `weight_kg` | `NUMERIC(7,3)` | 100.0% | 6 | 1009 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga) |
| `icms_rate` | `NUMERIC(6,2)` | 100.0% | 5 | 1009 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga) |
| `ipi_rate` | `NUMERIC(6,2)` | 100.0% | 5 | 1009 valores decimais; até 2 dígitos inteiros e 2 decimais (+2 de folga) |
| `is_active` | `BOOLEAN` | 100.0% | 5 | 1009 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 1009 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 1009 valores, todos YYYY-MM-DD HH:MM:SS |

### `products`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 3 | 500 valores inteiros, máximo 500 |
| `name` | `VARCHAR(32)` | 100.0% | 23 | 500 valores textuais; len max 23 |
| `description` | `VARCHAR(64)` | 98.0% | 48 | 490 valores textuais; len max 48 |
| `brand_id` | `INTEGER` | 100.0% | 2 | 500 valores inteiros, máximo 12 |
| `category_id` | `INTEGER` | 100.0% | 2 | 500 valores inteiros, máximo 14 |
| `ncm_code` | `VARCHAR(8)` | 100.0% | 8 | código de negócio, não medida (len max 8); aritmética não se aplica |
| `unit_of_measure` | `VARCHAR(8)` | 100.0% | 2 | 500 valores textuais; len max 2 |
| `is_active` | `BOOLEAN` | 100.0% | 5 | 500 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 500 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 500 valores, todos YYYY-MM-DD HH:MM:SS |

### `purchase_order_items`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 6059 valores inteiros, máximo 6059 |
| `purchase_order_id` | `INTEGER` | 100.0% | 4 | 6059 valores inteiros, máximo 2000 |
| `product_variant_id` | `INTEGER` | 100.0% | 4 | 6059 valores inteiros, máximo 1009 |
| `quantity_ordered` | `INTEGER` | 100.0% | 2 | 6059 valores inteiros, máximo 50 |
| `unit_cost` | `NUMERIC(8,2)` | 100.0% | 7 | 6059 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga) |
| `line_total` | `NUMERIC(10,2)` | 100.0% | 9 | 6059 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga) |

### `purchase_orders`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 2000 valores inteiros, máximo 2000 |
| `po_number` | `VARCHAR(16)` | 100.0% | 9 | 2000 valores textuais; len max 9 |
| `supplier_id` | `INTEGER` | 100.0% | 2 | 2000 valores inteiros, máximo 25 |
| `buyer_id` | `INTEGER` | 100.0% | 2 | 2000 valores inteiros, máximo 13 |
| `destination_location_id` | `INTEGER` | 100.0% | 1 | 2000 valores inteiros, máximo 6 |
| `status` | `VARCHAR(32)` | 100.0% | 18 | 2000 valores textuais; len max 18 |
| `currency` | `VARCHAR(8)` | 100.0% | 3 | 2000 valores textuais; len max 3 |
| `subtotal` | `NUMERIC(10,2)` | 100.0% | 9 | 2000 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga) |
| `total` | `NUMERIC(10,2)` | 100.0% | 9 | 2000 valores decimais; até 6 dígitos inteiros e 2 decimais (+2 de folga) |
| `placed_at` | `TIMESTAMP` | 100.0% | 19 | 2000 valores, todos YYYY-MM-DD HH:MM:SS |
| `expected_delivery_at` | `DATE` | 85.7% | 10 | 1713 valores, todos YYYY-MM-DD sem componente de hora |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 2000 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 2000 valores, todos YYYY-MM-DD HH:MM:SS |

### `return_items`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 1384 valores inteiros, máximo 1409 |
| `return_id` | `INTEGER` | 100.0% | 4 | 1384 valores inteiros, máximo 1000 |
| `order_item_id` | `INTEGER` | 100.0% | 6 | 1384 valores inteiros, máximo 150286 |
| `quantity` | `NUMERIC(7,3)` | 100.0% | 5 | 1384 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga) |
| `action` | `VARCHAR(8)` | 100.0% | 8 | 1384 valores textuais; len max 8 |
| `exchange_variant_id` | `INTEGER` | 26.0% | 4 | 360 valores inteiros, máximo 1007 |
| `unit_refund_amount` | `NUMERIC(8,2)` | 100.0% | 7 | 1384 valores decimais; até 4 dígitos inteiros e 2 decimais (+2 de folga) |

### `returns`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 4 | 980 valores inteiros, máximo 1000 |
| `return_number` | `VARCHAR(16)` | 100.0% | 9 | 980 valores textuais; len max 9 |
| `order_id` | `INTEGER` | 100.0% | 5 | 980 valores inteiros, máximo 49988 |
| `customer_id` | `INTEGER` | 100.0% | 4 | 980 valores inteiros, máximo 1997 |
| `received_at_location_id` | `INTEGER` | 100.0% | 1 | 980 valores inteiros, máximo 6 |
| `status` | `VARCHAR(16)` | 100.0% | 9 | 980 valores textuais; len max 9 |
| `reason` | `VARCHAR(64)` | 99.3% | 33 | 973 valores textuais; len max 33 |
| `total_refund_amount` | `NUMERIC(9,2)` | 100.0% | 8 | 980 valores decimais; até 5 dígitos inteiros e 2 decimais (+2 de folga) |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 980 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 980 valores, todos YYYY-MM-DD HH:MM:SS |

### `stock_levels`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `product_variant_id` | `INTEGER` | 100.0% | 4 | 6054 valores inteiros, máximo 1009 |
| `location_id` | `INTEGER` | 100.0% | 1 | 6054 valores inteiros, máximo 6 |
| `quantity_on_hand` | `NUMERIC(7,3)` | 100.0% | 6 | 6054 valores decimais; até 2 dígitos inteiros e 3 decimais (+2 de folga) |
| `reorder_point` | `TEXT` | 0.0% | 0 | coluna 100% vazia na fonte (6054 linhas); tipo indeterminável |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 6054 valores, todos YYYY-MM-DD HH:MM:SS |

### `stock_movements`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 6 | 115312 valores inteiros, máximo 117427 |
| `product_variant_id` | `INTEGER` | 100.0% | 4 | 115312 valores inteiros, máximo 1009 |
| `location_id` | `INTEGER` | 100.0% | 1 | 115312 valores inteiros, máximo 6 |
| `movement_type` | `VARCHAR(16)` | 100.0% | 11 | 115312 valores textuais; len max 11 |
| `quantity` | `NUMERIC(8,3)` | 100.0% | 7 | 115312 valores decimais; até 3 dígitos inteiros e 3 decimais (+2 de folga) |
| `reference_table` | `VARCHAR(16)` | 94.9% | 14 | 109418 valores textuais; len max 14 |
| `reference_id` | `INTEGER` | 94.9% | 5 | 109418 valores inteiros, máximo 50000 |
| `employee_id` | `INTEGER` | 49.7% | 2 | 57255 valores inteiros, máximo 15 |
| `notes` | `VARCHAR(64)` | 9.9% | 34 | 11405 valores textuais; len max 34 |
| `occurred_at` | `TIMESTAMP` | 100.0% | 19 | 115312 valores, todos YYYY-MM-DD HH:MM:SS |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 115312 valores, todos YYYY-MM-DD HH:MM:SS |

### `suppliers`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `id` | `INTEGER` | 100.0% | 2 | 25 valores inteiros, máximo 25 |
| `legal_name` | `VARCHAR(32)` | 100.0% | 30 | 25 valores textuais; len max 30 |
| `trade_name` | `VARCHAR(16)` | 52.0% | 11 | 13 valores textuais; len max 11 |
| `country` | `VARCHAR(8)` | 100.0% | 2 | 25 valores textuais; len max 2 |
| `tax_id` | `VARCHAR(16)` | 100.0% | 14 | código de negócio, não medida (len max 14); aritmética não se aplica |
| `tax_id_type` | `VARCHAR(8)` | 100.0% | 4 | 25 valores textuais; len max 4 |
| `email` | `VARCHAR(32)` | 100.0% | 30 | 25 valores textuais; len max 30 |
| `phone` | `VARCHAR(16)` | 100.0% | 13 | código de negócio, não medida (len max 13); aritmética não se aplica |
| `contact_name` | `VARCHAR(32)` | 100.0% | 27 | 25 valores textuais; len max 27 |
| `is_active` | `BOOLEAN` | 100.0% | 5 | 25 valores, todos em {TRUE, FALSE} |
| `created_at` | `TIMESTAMP` | 100.0% | 19 | 25 valores, todos YYYY-MM-DD HH:MM:SS |
| `updated_at` | `TIMESTAMP` | 100.0% | 19 | 25 valores, todos YYYY-MM-DD HH:MM:SS |

### `variant_attribute_values`

| Coluna | Tipo inferido | % preenchido | len max | Evidência |
|---|---|---:|---:|---|
| `product_variant_id` | `INTEGER` | 100.0% | 4 | 2018 valores inteiros, máximo 1009 |
| `attribute_id` | `INTEGER` | 100.0% | 1 | 2018 valores inteiros, máximo 8 |
| `value` | `VARCHAR(16)` | 100.0% | 14 | 2018 valores textuais; len max 14 |

## Chaves estrangeiras

| Origem | Coluna | Destino | Como foi descoberta |
|---|---|---|---|
| `addresses` | `customer_id` | `customers.id` | convenção de nome |
| `categories` | `parent_category_id` | `categories.id` | convenção de nome |
| `employees` | `primary_location_id` | `locations.id` | convenção de nome |
| `fiscal_invoices` | `order_id` | `orders.id` | convenção de nome |
| `goods_receipt_items` | `goods_receipt_id` | `goods_receipts.id` | convenção de nome |
| `goods_receipt_items` | `purchase_order_item_id` | `purchase_order_items.id` | convenção de nome |
| `goods_receipts` | `purchase_order_id` | `purchase_orders.id` | convenção de nome |
| `goods_receipts` | `received_by_employee_id` | `employees.id` | convenção de nome |
| `order_items` | `order_id` | `orders.id` | convenção de nome |
| `order_items` | `product_variant_id` | `product_variants.id` | convenção de nome |
| `orders` | `customer_id` | `customers.id` | convenção de nome |
| `orders` | `salesperson_id` | `employees.id` | anulação explícita |
| `orders` | `location_id` | `locations.id` | convenção de nome |
| `payments` | `order_id` | `orders.id` | convenção de nome |
| `product_suppliers` | `product_variant_id` | `product_variants.id` | convenção de nome |
| `product_suppliers` | `supplier_id` | `suppliers.id` | convenção de nome |
| `product_variants` | `product_id` | `products.id` | convenção de nome |
| `products` | `brand_id` | `brands.id` | convenção de nome |
| `products` | `category_id` | `categories.id` | convenção de nome |
| `purchase_order_items` | `purchase_order_id` | `purchase_orders.id` | convenção de nome |
| `purchase_order_items` | `product_variant_id` | `product_variants.id` | convenção de nome |
| `purchase_orders` | `supplier_id` | `suppliers.id` | convenção de nome |
| `purchase_orders` | `buyer_id` | `employees.id` | anulação explícita |
| `purchase_orders` | `destination_location_id` | `locations.id` | convenção de nome |
| `return_items` | `return_id` | `returns.id` | convenção de nome |
| `return_items` | `order_item_id` | `order_items.id` | convenção de nome |
| `return_items` | `exchange_variant_id` | `product_variants.id` | anulação explícita |
| `returns` | `order_id` | `orders.id` | convenção de nome |
| `returns` | `customer_id` | `customers.id` | convenção de nome |
| `returns` | `received_at_location_id` | `locations.id` | convenção de nome |
| `stock_levels` | `product_variant_id` | `product_variants.id` | convenção de nome |
| `stock_levels` | `location_id` | `locations.id` | convenção de nome |
| `stock_movements` | `product_variant_id` | `product_variants.id` | convenção de nome |
| `stock_movements` | `location_id` | `locations.id` | convenção de nome |
| `stock_movements` | `employee_id` | `employees.id` | convenção de nome |
| `variant_attribute_values` | `product_variant_id` | `product_variants.id` | convenção de nome |
| `variant_attribute_values` | `attribute_id` | `attributes.id` | convenção de nome |

### Não declaradas de propósito

- `stock_movements.reference_id` — coluna polimórfica: o alvo depende do valor de outra coluna na mesma linha. Não há FK declarável para isso em SQL padrão.
