# Guia de submissão — Desafio Lighthouse 2026

> ⚠️ **TENTATIVA ÚNICA. Sem autosave. Sem edição após enviar.**
> Prazo: **17/08/2026, 08h**.
>
> Monte todas as respostas **fora do formulário** (este documento), confira o
> checklist do fim, e só então preencha e envie.

---

## Mapa: campo do formulário → o que fazer

Cada linha é um campo. **Anexo** = subir arquivo; o caminho é a partir da raiz
do repositório. **Curta** = digitar. **Texto** = colar do
[`RESPOSTAS-PARA-O-FORMULARIO.md`](RESPOSTAS-PARA-O-FORMULARIO.md).

| Campo | Tipo | O que enviar |
|---|---|---|
| **1.1** Código SQL da EDA | 📎 anexo | `entregaveis/Q1_eda/q1_eda_orders.sql` |
| **1.2** Valor médio de `total` | ⌨ curta | **28.704,99** |
| **1.3** Interpretação | 📋 texto | § **1.3** do consolidado |
| **2.1** Código Python do schema | 📎 anexo | `entregaveis/Q2_schema/q2_gerar_schema.py` |
| **2.2** Arquivo `schema.sql` | 📎 anexo | `entregaveis/Q2_schema/schema.sql` |
| **3.1** Código Python da carga | 📎 anexo | `entregaveis/Q3_carga/q3_carregar_csvs.py` |
| **3.2** Total de linhas carregadas | ⌨ curta | **251.864** |
| **4.1** Código SQL dos clientes | 📎 anexo | `entregaveis/Q4_clientes/q4_clientes_elite.sql` |
| **4.2** Explicação | 📋 texto | § **4.2** do consolidado |
| **5.1** Código SQL do calendário | 📎 anexo | `entregaveis/Q5_calendario/q5_dim_calendario.sql` |
| **5.2** Explicação | 📋 texto | § **5.2** do consolidado |
| **6.1** Código Python da previsão | 📎 anexo | `entregaveis/Q6_previsao/q6_previsao_demanda.py` |
| **6.2** Soma da previsão | ⌨ curta | **116** |
| **6.3** Explicação | 📋 texto | § **6.3** do consolidado |
| **7.1** Código Python da recomendação | 📎 anexo | `entregaveis/Q7_recomendacao/q7_recomendacao.py` |
| **7.2** Produto mais similar | ⌨ curta | **Motor de Popa 5331** |
| **7.3** Explicação | 📋 texto | § **7.3** do consolidado |
| **Material complementar** ⛔ | 📎 anexo | `powerbi/lh_nautical.pbix` · `powerbi/lh_nautical.pdf` |
| Campo de notas / links | ⌨ curta | os dois links abaixo |

### Os 8 anexos de código, na ordem

```
entregaveis/Q1_eda/q1_eda_orders.sql
entregaveis/Q2_schema/q2_gerar_schema.py
entregaveis/Q2_schema/schema.sql
entregaveis/Q3_carga/q3_carregar_csvs.py
entregaveis/Q4_clientes/q4_clientes_elite.sql
entregaveis/Q5_calendario/q5_dim_calendario.sql
entregaveis/Q6_previsao/q6_previsao_demanda.py
entregaveis/Q7_recomendacao/q7_recomendacao.py
```

Mais os **dois do material complementar**:

```
powerbi/lh_nautical.pbix     9,2 MB  ⛔ obrigatório
powerbi/lh_nautical.pdf      676 KB  · 5 páginas
```

### Links para o campo de notas

```
Repositório: https://github.com/Breno-Teodomiro/desafio-lighthouse-2026
Dashboard:   https://app.powerbi.com/view?r=eyJrIjoiMDY4MDQxM2ItYWI4Ni00ZjQ5LWJmOGMtMTlhNDgwNDAzNjQzIiwidCI6ImMyMGU3MTg4LTNkMzEtNGM1ZC05YWNlLTE4MzQyM2E2MGMxZCJ9
```

**Perguntas finais (opinião, sem resposta certa):**
- *Em qual questão teve mais facilidade?* — sugestão: **Questão 1 (EDA)**, por ser a mais direta.
- *Em qual mais gostou de trabalhar?* — sugestão: **Questão 5 (calendário)**, por ser a única em que o método muda a decisão de negócio.

---

## As 4 respostas objetivas

Todas confirmadas por **dois caminhos independentes** (`tests/verificar_respostas.py`, 46 conferências).

| Questão | Resposta |
|---|---|
| **1.2** | **R$ 28.704,99** *(exato: 28704,992077227642)* |
| **3.2** | **251.864** *(2.000 + 48.998 + 147.320 + 53.546)* |
| **6.2** | **116** |
| **7.2** | **Motor de Popa 5331** |

### Cuidados ao digitar

- **6.2 é 116, não 117.** O enunciado pede *"a **soma total** da previsão arredondada"* — arredonda-se a soma (116,0000). Arredondar cada mês antes de somar daria 39 × 3 = 117.
- **7.2 é o nome, não o id.** "Motor de Popa 5331" (`product_id` 389). Não confundir com o item de **referência**, que é "Motor de Popa 1949".
- **1.2**: se o campo aceitar só número, use `28704.99`.

---

## ⛔ O que falta: exportar o `.pbix`

O dashboard está pronto — 5 páginas, 21 componentes em HTML gerado por DAX,
13 deles filtrando a página ao clique. Falta só tirar os arquivos de dentro
dele.

**Na ordem:**

1. ~~Abrir o `.pbip` e conferir as telas~~ ✅
2. ~~`Arquivo → Salvar como → .pbix`~~ ✅ `powerbi/lh_nautical.pbix` (9,2 MB)
3. ~~`Arquivo → Exportar → PDF`~~ ✅ `powerbi/lh_nautical.pdf` (5 páginas)
4. ~~Publicar no Service~~ ✅ link atualizado
5. **Preencher o formulário** pelo mapa do topo deste documento ← falta só isto

> ⚠️ **Depois de ajustar algo à mão no Desktop, não rode `make powerbi` nem
> `powerbi/gerar_html_dax.py`.** Os dois regravam o projeto a partir do script
> e desfazem o ajuste. O PBIP no disco é o artefato canônico desde 16/08.

O visual **HTML Content (lite)** fica embutido no `.pbix`, então quem abrir o
arquivo não precisa instalar nada. Ele é a edição **certificada** — a que é
aceita em *Publicar na web*.

### Números que o dashboard deve reproduzir

| Medida | Valor |
|---|---|
| Receita Bruta (todos os status) | R$ 1.406.487.201,80 |
| Receita Efetivada (`paid` + `confirmed`) | R$ 1.199.367.079,54 |
| Nº Pedidos | 48.998 |
| Ticket Médio | R$ 28.704,99 |
| Receita de Itens | R$ 1.437.204.604,96 |
| Margem Bruta | R$ 611.945.739,58 · **42,58%** |
| Margem Líquida | R$ 581.228.336,42 · **40,44%** |
| Média de Venda por Dia POS — Quinta | R$ 157.154,32 |
| Média por Dia (só dias com venda) — Segunda | R$ 161.335,26 |
| Dias sem Venda | 78 |

**Se algum número divergir, o problema está no modelo, não nos dados** — os dados foram conferidos 46 vezes.

> **Plano B, se o PBIP não abrir:** os Parquets em `dados/gold/` estão prontos e íntegros. Criar um `.pbix` novo, importar as 14 tabelas, recriar os relacionamentos listados em `powerbi/MODELO.md` e colar as medidas de `powerbi/sm_lh_nautical.SemanticModel/definition/tables/_Medidas.tmdl`. É trabalhoso, mas nada se perde.

---

## O que dá diferencial, e por quê

O Tech Lead fictício declarou valorizar **organização e explicação acima de código complexo**. Os pontos abaixo existem por causa disso — vale citá-los ao preencher os campos de texto.

1. **A Q2 tem gate automático da premissa eliminatória.** `tests/gate_stdlib.py` percorre a árvore sintática e confere cada módulo contra `sys.stdlib_module_names`. Procurar a string "pandas" não pegaria `import numpy as np` nem um import escondido dentro de função.

2. **A Q3 responde "não faça tratamentos" por construção, não por disciplina.** `COPY ... FROM STDIN` com bytes crus: o Python nunca decodifica nem reserializa um valor. E o `COMMIT` valida as 37 FKs de uma vez — o que prova de graça que a integridade referencial da base é perfeita.

3. **Três contagens independentes** (bytes do arquivo, `rowcount` do `COPY`, `SELECT count(*)`) precisam concordar antes do `COMMIT`. É o que torna 251.864 uma verificação, e não uma digitação.

4. **A Q4 mede os erros em vez de descrevê-los.** O apêndice do SQL mostra que juntar `order_items` infla o faturamento 3,67× e juntar `payments` infla 9,3%.

5. **A Q5 roda as duas médias lado a lado.** O argumento não é "o calendário é importante" — é *"o diagnóstico troca de dia, e o Sr. Almir fecharia a loja errada"*.

6. **A Q6 mostra que o baseline pedido perde para copiar o ano anterior** (MAE 25,0 contra 30,33). E corrige a explicação intuitiva: não é "baixa prevendo pico" — out–dez é a parte **alta** da série. As causas são a tendência (+82%) e dez/2025 ter sido um ponto fora da curva.

7. **A Q7 prova as próprias fragilidades.** Agrupar por nome faz `asdf` subir a 1º; 4 de 5 recortes de status invertem a resposta; os três primeiros estão a 2,40/2,39/2,38 sigma — indistinguíveis. E o bônus de cesta mostra que a pergunta da Marina tem outra resposta: Tinta Antifouling.

8. **Toda ambiguidade do enunciado está documentada com o cenário alternativo**, em vez de resolvida em silêncio: os dois `product_id` da Bússola, os três esquemas de média móvel, o filtro de status da Q7.

---

## Checklist final

Antes de clicar em enviar:

- [ ] Os 8 arquivos de código estão anexados (2 SQL de Q1/Q4/Q5 + Q2 py + schema.sql + Q3 py + Q6 py + Q7 py)
- [ ] `schema.sql` é o **gerado**, não uma versão editada à mão
- [ ] **1.2 = 28.704,99**
- [ ] **3.2 = 251.864**
- [ ] **6.2 = 116** *(não 117)*
- [ ] **7.2 = Motor de Popa 5331** *(não "1949", que é a referência)*
- [ ] Textos de 1.3, 4.2, 5.2, 6.3 e 7.3 colados de `RESPOSTAS-PARA-O-FORMULARIO.md`
- [ ] **A resposta da Q1 não menciona 2027** — `orders` termina em 2026-12-31
- [ ] **`.pbix` exportado e anexado** ⛔ *obrigatório*
- [ ] PDF do dashboard anexado
- [ ] Link do repositório incluído no campo de notas
- [ ] Link do dashboard publicado incluído no campo de notas
- [ ] Dashboard **republicado** com a versão final
- [ ] Repositório **não contém** `Formulario_de_Questoes.md`, `Desafio_Lighthouse.md`, o PDF do edital, os CSVs nem o `.env`

**Conferência do último item:**

```bash
git ls-files | grep -iE "formulario|desafio_lighthouse|edital|\.env$|lh_nautical_csv" && echo "PARE — material sensível versionado" || echo "ok, nada sensível no git"
```

---

## Como reproduzir tudo do zero

```bash
make setup      # dependências
make db         # gera schema.sql (Q2) e aplica no banco
make carga      # carrega os 24 CSVs (Q3) — 433.424 linhas, ~17 s
make questoes   # roda as 7 questões
make powerbi    # silver -> gold -> Parquet -> PBIP
make check      # gate stdlib + ruff + mypy + validação do PBIP
.venv/bin/python tests/verificar_respostas.py   # as 46 conferências adversariais
```
