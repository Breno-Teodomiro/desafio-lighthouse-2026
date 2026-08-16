# Guia de submissão — Desafio Lighthouse 2026

> ⚠️ **TENTATIVA ÚNICA. Sem autosave. Sem edição após enviar.**
> Prazo: **17/08/2026, 08h**.
>
> Monte todas as respostas **fora do formulário** (este documento), confira o
> checklist do fim, e só então preencha e envie.

---

## Mapa: campo do formulário → arquivo

| Campo | O que enviar | Origem |
|---|---|---|
| **1.1** Código SQL | `entregaveis/Q1_eda/q1_eda_orders.sql` | upload |
| **1.2** Valor médio de `total` | **R$ 28.704,99** | resposta curta |
| **1.3** Interpretação | seção *Q1.3* de `entregaveis/Q1_eda/RESPOSTA.md` | texto |
| **2.1** Código Python | `entregaveis/Q2_schema/q2_gerar_schema.py` | upload |
| **2.2** `schema.sql` | `entregaveis/Q2_schema/schema.sql` | upload |
| **3.1** Código Python | `entregaveis/Q3_carga/q3_carregar_csvs.py` | upload |
| **3.2** Total de linhas | **251.864** | resposta curta |
| **4.1** Código SQL | `entregaveis/Q4_clientes/q4_clientes_elite.sql` | upload |
| **4.2** Explicação | seção *Q4.2* de `entregaveis/Q4_clientes/RESPOSTA.md` | texto |
| **5.1** Código SQL | `entregaveis/Q5_calendario/q5_dim_calendario.sql` | upload |
| **5.2** Explicação | seção *Q5.2* de `entregaveis/Q5_calendario/RESPOSTA.md` | texto |
| **6.1** Código Python | `entregaveis/Q6_previsao/q6_previsao_demanda.py` | upload |
| **6.2** Soma da previsão | **116** | resposta curta |
| **6.3** Explicação | seção *Q6.3* de `entregaveis/Q6_previsao/RESPOSTA.md` | texto |
| **7.1** Código Python | `entregaveis/Q7_recomendacao/q7_recomendacao.py` | upload |
| **7.2** Produto mais similar | **Motor de Popa 5331** | resposta curta |
| **7.3** Explicação | seção *Q7.3* de `entregaveis/Q7_recomendacao/RESPOSTA.md` | texto |
| **Material complementar** | **`.pbix` exportado do PBIP** + PDF + link do repositório | upload · **obrigatório** |

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

## ⛔ Bloqueador: o dashboard precisa ser aberto e exportado

**Esta é a única pendência que exige ação manual, e ela é obrigatória.**

O projeto Power BI foi gerado em `powerbi/lh_nautical.pbip` (15 tabelas, 19 medidas, 16 relacionamentos, 5 páginas, 48 visuais). Ele foi validado por script — todas as 65 referências a campos resolvem contra o modelo —, **mas não foi aberto no Power BI Desktop**, porque o Desktop não está instalado na máquina onde o projeto foi construído.

**Passos:**

1. Regenerar os dados, se necessário: `make powerbi`
2. Abrir `powerbi/lh_nautical.pbip` no Power BI Desktop
   *(Arquivo → Opções → Recursos de Versão Prévia → **Power BI Project (.pbip) save option** ligado)*
3. Se o parâmetro `PastaDados` não apontar para a pasta certa, ajustar em *Transformar dados → Parâmetros*
4. **Conferir os números contra a tabela de referência abaixo**
5. Ajustar posicionamento e formatação dos visuais onde estiver feio — o layout foi escrito às cegas
6. `Arquivo → Salvar como → .pbix`
7. `Arquivo → Exportar → PDF`

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
- [ ] Textos de 1.3, 4.2, 5.2, 6.3 e 7.3 colados dos `RESPOSTA.md`
- [ ] **A resposta da Q1 não menciona 2027** — `orders` termina em 2026-12-31
- [ ] **`.pbix` exportado e anexado** ⛔ *obrigatório*
- [ ] PDF do dashboard anexado
- [ ] Link do repositório incluído no campo de notas
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
