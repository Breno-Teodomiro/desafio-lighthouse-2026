# Questão 3 — Carregamento

**Entregáveis:** `q3_carregar_csvs.py` (Q3.1) · `relatorio_carga.md` (prova da conferência)

```bash
python3 q3_carregar_csvs.py --csv-dir ./1-lh_nautical_csv --relatorio relatorio_carga.md
python3 q3_carregar_csvs.py --csv-dir ./1-lh_nautical_csv --dry-run   # confere sem escrever
```

---

## Q3.2 — Resposta

> *Qual o total de linhas somadas das tabelas customers, orders, order_items e payments?*

| Tabela | Linhas |
|---|---:|
| `customers` | 2.000 |
| `orders` | 48.998 |
| `order_items` | 147.320 |
| `payments` | 53.546 |
| **TOTAL** | **251.864** |

Carga completa: **433.424 linhas em 24 tabelas, em 17,6 s**, transação única.

O número não foi digitado à mão. Ele é o resultado de **três contagens independentes que precisam concordar** antes do `COMMIT`:

1. **bytes** — contagem de `\n` no arquivo, sem passar pelo parser de CSV;
2. **`rowcount` do `COPY`** — o que o servidor informa ter recebido;
3. **`SELECT count(*)`** — o que está de fato nas tabelas.

Divergência em qualquer uma levanta exceção e desfaz a carga inteira. A conferência só vale porque os três caminhos são diferentes: se a validação usasse o mesmo código da carga, estaria validando a si mesma.

---

## Conformidade com a premissa

> *"Não faça tratamentos como: Remoção de nulos ou correção de caracteres especiais."*

A resposta do script a essa premissa é `COPY ... FROM STDIN` alimentado com os **bytes** do arquivo, em blocos de 1 MiB:

```python
sql = (f'COPY "{schema}"."{tabela}" ({colunas}) FROM STDIN '
       f"WITH (FORMAT csv, HEADER true, NULL '', ENCODING 'UTF8')")
with open(caminho, "rb") as fh, cur.copy(sql) as cp:
    while bloco := fh.read(1 << 20):
        cp.write(bloco)
```

O Python aqui **nunca decodifica, interpreta nem reserializa um único valor**. Os bytes saem do disco e entram no parser do servidor. Isso elimina *por construção* três classes de alteração silenciosa:

- **round-trip por float** — `2398.41` lido como `float64` e reescrito pode virar `2398.4100000000001`; aqui o texto chega intacto ao `NUMERIC`;
- **reinterpretação de encoding** — não há `str.encode`/`decode` de valor, então acento não tem por onde se corromper;
- **"limpeza" acidental** — não existe um ponto no código onde alguém *pudesse* decidir descartar um `?` ou um `asdf`.

A alternativa (`executemany`, `execute_values`) exigiria escrever à mão a regra de vazio-vs-`NULL` para cada campo — ou seja, exigiria **tratar o dado justamente onde o enunciado proíbe**. A escolha do `COPY` aqui é um argumento de fidelidade; a velocidade é consequência.

### Verificação de que nada foi tratado

Consultado no banco **depois** da carga:

| O que | Consulta | Resultado |
|---|---|---|
| Lixo textual | `legal_name IN ('TBD','Sem Nome',...)` | preservado — `TBD` e `Sem Nome` presentes |
| Zero à esquerda | `tax_id LIKE '0%'` | `00429721404` intacto |
| Série de NF-e | `SELECT DISTINCT series` | `'001'`, não `1` |
| Chave de NF-e | `length(nfe_access_key)` | 44 dígitos |
| Sinal negativo | `quantity < 0` em `stock_movements` | 103.577 de 115.312 preservadas |
| Coluna vazia | `count(reorder_point)` | 0 de 6.054 — continua vazia |

---

## Vazio vs `NULL`: por que o mapeamento não perde informação

`WITH (FORMAT csv, NULL '')` converte campo **não-aspado** vazio em `NULL` e preserva campo **aspado** vazio (`""`) como string vazia.

Isso normalmente é uma decisão arbitrária. Aqui não é: **não existe um único caractere `"` em nenhum dos 24 arquivos** — verificado varrendo os 36 MB. Logo a fonte é incapaz de representar "string vazia" como algo distinto de "ausente", e o mapeamento é bijetivo no domínio que de fato existe. Nada é descartado porque não há nada a descartar.

Essa mesma verificação sustenta a contagem por bytes: sem aspas, nenhum campo pode conter quebra de linha embutida, então contar `\n` conta registros — para LF e para CRLF igualmente.

---

## Garantias operacionais

**Transação única.** `BEGIN` → `SET datestyle`/`client_encoding`/`CONSTRAINTS ALL DEFERRED` → `TRUNCATE` → 24 × `COPY` → conferência → `COMMIT` → `ANALYZE`. Falha em qualquer ponto desfaz tudo; não existe estado meio-carregado.

**Idempotência.** `TRUNCATE ... RESTART IDENTITY` **nominal** nas 24 tabelas da camada `raw`. Rodar duas vezes produz exatamente o mesmo estado.

**As 37 chaves estrangeiras validadas de uma vez.** Com `SET CONSTRAINTS ALL DEFERRED`, o PostgreSQL adia a verificação até o `COMMIT`. O commit passou — o que é, de graça, a prova de que **a integridade referencial da base é perfeita: zero órfãos em 37 relacionamentos.**

**Ordem de carga lida do banco, não hardcodada.** As dependências vêm de `pg_constraint`, auto-referências (`categories.parent_category_id`) são ignoradas e a ordem sai por Kahn com desempate alfabético. Com as constraints diferidas isso é redundante — é cinto e suspensório, e mantém o log legível, com os pais aparecendo antes dos filhos.

**Guarda de banco compartilhado.** A instância PostgreSQL é compartilhada com outros projetos. Antes de qualquer escrita, o script consulta `SELECT current_database()` e **aborta com código 2** se não estiver em `lh_nautical`. Um `TRUNCATE` no banco errado seria irreversível; a verificação custa uma consulta.

**Pré-voo antes de abrir transação.** Cabeçalhos conferidos contra `information_schema.columns`, contagem de linhas feita, terminadores detectados. Arquivo com terminadores **mistos** aborta a carga: `COPY` aguentaria, mas mistura de CRLF e LF no mesmo arquivo indica extração corrompida e merece parar, não passar despercebido. Os 7 arquivos CRLF desta base (`fiscal_invoices`, `order_items`, `orders`, `payments`, `return_items`, `returns`, `stock_movements`) são consistentemente CRLF.

**Colunas nomeadas a partir do cabeçalho do CSV.** A carga depende do **nome** da coluna, não da posição. Se o CSV ganhar uma coluna nova amanhã, isso falha com mensagem clara em vez de deslocar valores silenciosamente para a coluna vizinha.

---

## Leitura de engenharia

1. **`raw` fiel é o começo, não o fim.** Esta camada é deliberadamente burra: espelha a fonte, lixo incluído. `TBD` em `legal_name` e `asdf` em nome de produto **têm de** chegar aqui, porque `raw` é a evidência do que o ERP entregou. A decisão sobre o que fazer com eles é da camada seguinte, e é uma decisão de negócio — não uma escolha técnica a ser tomada em silêncio dentro de um loader.

2. **Uma carga full de 433 mil linhas é aceitável porque a base é pequena.** Em 17 s, o `TRUNCATE`+`COPY` é mais simples e mais auditável que qualquer alternativa. Com 400 milhões de linhas a conversa muda para carga incremental por marca d'água, particionamento por data e `COPY` em tabela de staging com `swap` atômico. **A escolha certa aqui é função do volume, e vale registrar que ela foi feita — não herdada.**

3. **O que falta para isto virar produção:** captura de um hash por arquivo para detectar reprocessamento do mesmo extrato; uma tabela de controle de carga com data, contagem e duração por execução; e quarentena para linhas rejeitadas — que aqui não existe porque nenhuma linha foi rejeitada, mas em um ERP real existiriam.

4. **O ganho oculto do `COMMIT` que passou.** Validar 37 FKs de uma vez transformou a carga em um teste de integridade referencial da base inteira. É um efeito colateral do desenho, e é o tipo de garantia que normalmente exige uma bateria de consultas separada.
