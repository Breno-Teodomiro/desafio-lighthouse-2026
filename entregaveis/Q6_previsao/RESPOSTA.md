# Questão 6 — Previsão de demanda

**Entregável:** `q6_previsao_demanda.py` (Q6.1) · este documento (Q6.2, Q6.3, Q6.5)

```bash
python3 q6_previsao_demanda.py --csv-dir ./1-lh_nautical_csv
```

---

## Q6.2 — Resposta

> **A soma total da previsão para o 1º trimestre de 2026 é 116 unidades.**

| Mês | Previsto | Real | Erro absoluto |
|---|---:|---:|---:|
| 2026-01 | 38,67 | 79 | 40,33 |
| 2026-02 | 38,67 | 68 | 29,33 |
| 2026-03 | 38,67 | 60 | 21,33 |
| **SOMA** | **116,00** | **207** | — |

**MAE = 30,33 unidades/mês.**

> ⚠️ **Sobre o arredondamento.** O enunciado pede *"a **soma total** da previsão de vendas (arredondada para número inteiro)"* — arredonda-se **a soma**, não cada mês. A soma exata é 116,0000 → **116**. Arredondar cada mês antes de somar daria 39 × 3 = **117**. A leitura literal do enunciado é a primeira.

---

## Duas ambiguidades do enunciado, e como foram resolvidas

### 1. "Bússola de Bordo 702" existe duas vezes no cadastro

| `product_id` | `brand_id` | `category_id` |
|---:|---:|---:|
| **74** | 12 | 8 |
| **240** | 8 | 7 |

Mesmo nome, mesma descrição, marcas e categorias diferentes. O enunciado nomeia o produto **pelo nome**, e a implementação natural — `products.name == 'Bússola de Bordo 702'` — captura os dois. **Escolher apenas um exigiria um critério que o enunciado não fornece.**

Adotamos a soma dos dois. O script imprime os três cenários para deixar a escolha auditável:

| Cenário | MM3 | Previsão Q1 | Real Q1 | MAE |
|---|---:|---:|---:|---:|
| só `id` 74 | 25,33 | 76 | 156 | 26,67 |
| só `id` 240 | 13,33 | 40 | 51 | 5,89 |
| **ambos (adotado)** | **38,67** | **116** | **207** | **30,33** |

### 2. "Considerando apenas dados anteriores à data prevista"

Três leituras possíveis:

| Esquema | jan / fev / mar | Soma | MAE |
|---|---|---:|---:|
| **Estático** — MM3 de out/nov/dez-2025, constante no horizonte | 38,67 / 38,67 / 38,67 | **116** | **30,33** |
| Recursivo — realimenta as próprias previsões | 38,67 / 40,22 / 33,63 | 113 | 31,49 |
| Rolling — realimenta os reais do teste | 38,67 / 53,67 / 56,33 | 149 | 19,44 |

**Adotamos o estático.** Quatro razões:

1. Realimentar o real de janeiro faria janeiro **virar treino**, contradizendo o split que o próprio enunciado declara.
2. A Q6.2 pede a previsão *"utilizando seu modelo **treinado**"* — treina uma vez, aplica ao horizonte.
3. A janela out/nov/dez é **estritamente anterior** a cada data prevista, satisfazendo a trava de leakage ao pé da letra.
4. É a única leitura que responde à pergunta de negócio: a compra do trimestre é fechada em dezembro, e **o comprador não pode esperar o número real de janeiro** para decidir quanto pedir ao fornecedor.

O esquema *rolling* tem o menor MAE justamente porque **não é previsão — é backtest que exige conhecer o futuro**. Reportá-lo como resultado do modelo seria enganoso.

---

## Q6.3 — Explicação

### Como o baseline foi construído

```python
serie  = df_alvo.groupby("mes")["quantidade"].sum().reindex(indice_denso, fill_value=0)
treino = serie.loc[:"2025-12"]          # corte físico, antes de qualquer estatística
ma3    = treino.iloc[-3:].mean()        # (34 + 60 + 22) / 3 = 38,6667
previsao = pd.Series(ma3, index=pd.period_range("2026-01", "2026-03", freq="M"))
```

Quatro passos:

1. **Dataset unificado** no grão de linha de item, juntando os 4 CSVs pela cadeia `order_items → product_variants → products` e `order_items → orders`. **`order_items` não tem `product_id`** — a variante é obrigatória no caminho.
2. **Agregação mensal** por `orders.created_at` (a data em que a demanda se manifestou).
3. **Índice mensal denso.** O `reindex` é a linha mais importante: sem ele, um mês sem venda simplesmente não aparece na série, e *"os últimos 3 meses"* passaria a significar *"as últimas 3 linhas existentes"* — que podem estar espalhadas por seis meses do calendário. A média sairia errada **sem dar nenhum sinal de que algo está errado**. Esta série tem um mês zerado (out/2020), então o risco é real, não teórico.
4. **Média das 3 últimas observações do treino**, aplicada aos 3 meses do horizonte.

### Como evitei data leakage

- **Corte físico do dataset em 2025-12** na própria construção da série, não como filtro aplicado depois. A série de treino e a série de teste são objetos separados.
- **O índice denso do treino termina em 2025-12** e não além — assim um mês vazio de 2026 não pode entrar na janela por efeito colateral do `reindex`.
- **Nenhuma realimentação** com valores reais do período de teste.
- **A janela out/nov/dez-2025 é estritamente anterior** a cada uma das três datas previstas.
- **Uso de `orders.created_at`, não de `payments.paid_at`.** É um ponto sutil: o pagamento acontece *depois* do pedido, então usar a data de pagamento embutiria informação posterior ao evento que se quer prever. A demanda se manifesta quando o pedido é feito.

### Uma limitação do modelo

**Ele emite um único número para todo o horizonte.** A previsão de janeiro, fevereiro e março é idêntica — 38,67 —, o que é inútil para escalonar a compra mês a mês, que é exatamente o problema do Sr. Almir. Um modelo que não distingue meses não pode informar uma decisão que é tomada por mês.

*(As demais limitações estão na seção Q6.5.b.)*

---

## Q6.5.a — O baseline é adequado para este produto?

> **Não. E há prova dura: o baseline pedido perde para simplesmente copiar o ano anterior.**

| Modelo | Soma Q1/2026 | MAE |
|---|---:|---:|
| Média móvel 3m (o pedido) | 116 | 30,33 |
| **Seasonal naive** (repete Q1/2025) | 166 | **25,00** ← melhor |
| Naive (repete dez/2025) | 66 | 47,00 |

O *seasonal naive* — que não tem parâmetro nenhum, só repete o mesmo trimestre do ano passado — erra **18% menos** que a média móvel. Quando um baseline perde para uma regra ainda mais simples, o problema não é falta de sofisticação: é que ele ignora a estrutura dominante da série.

### Por que o MM3 subestima em 44%

Vale desmontar aqui a explicação intuitiva, que é **errada**.

**(a) NÃO é "usou meses de baixa para prever meses de pico".** A janela out/nov/dez é, historicamente, a parte **alta** da série:

| Janela | Média histórica |
|---|---:|
| out–nov–dez | **39,6 un./mês** |
| jan–fev–mar | 35,9 un./mês |
| jul (o mínimo) | 8,5 un./mês |

A baixa desta série é o **meio do ano** — um padrão de verão do hemisfério sul, coerente com varejo náutico. A janela usada estava do lado certo do ciclo.

**(b) A causa principal é a TENDÊNCIA.** A série cresce de forma consistente, e uma média é um número plano — ela não extrapola crescimento:

| Ano | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| Total anual | 239 | 255 | 345 | 308 | 385 | **434** |

**+82% de 2020 a 2025.** E só no 1º trimestre: 64 → 79 → 90 → 86 → 161 → 166 → **207 em 2026**. A média móvel ancora num nível que a série já ultrapassou quando a previsão aterrissa.

**(c) Agravante: dez/2025 é um ponto fora da curva, e a janela curta dá a ele 1/3 do peso.**

| Dezembro | 2020 | 2021 | 2022 | 2023 | 2024 | **2025** |
|---|---:|---:|---:|---:|---:|---:|
| Unidades | 45 | 45 | 49 | 51 | 38 | **22** |

Dez/2025 vendeu **menos da metade** do dezembro típico (média 45,6). Sozinho, ele derruba a previsão em **7,9 un./mês — 24 unidades no trimestre**, mais de 20% do total previsto. Com janela de 3 meses e desvio padrão de 18,0 contra média de 27,3, um único mês atípico contamina a previsão inteira.

---

## Q6.5.b — Limitações do método

1. **Ignora tendência.** É a limitação que mais custa aqui: a série cresce 82% em 6 anos e o modelo prevê um valor plano.
2. **Ignora sazonalidade.** A amplitude sazonal é de 5,4× entre o pico (nov, 45,8) e o vale (jul, 8,5). Um modelo que não sabe em que mês está não pode acertar nenhum dos dois.
3. **Um único número para todo o horizonte** — inútil para escalonar compra mês a mês.
4. **Janela curta em série ruidosa.** Média 27,3, desvio 18,0 (CV de 66%). Um dezembro atípico move a previsão em 20%.
5. **Sem intervalo de confiança.** O comprador recebe "116" sem saber se a faixa plausível é 100–130 ou 60–200. Para decisão de estoque, a incerteza é tão acionável quanto o ponto central — é ela que dimensiona o estoque de segurança.
6. **O "produto" é mal definido.** Dois SKUs com o mesmo nome, e a resposta varia entre 40, 76 e 116 conforme a leitura. Nenhum modelo conserta um problema de cadastro.
7. **Ignora tudo que não seja o histórico da própria série:** preço, promoção, ruptura de estoque, lançamento de concorrente. Uma venda que não aconteceu por falta de estoque aparece como demanda baixa, e o modelo aprende a pedir menos — o círculo vicioso clássico de previsão sobre vendas em vez de demanda.

### Próximo passo recomendado

**Adotar o seasonal naive como piso** — ele já bate o MM3 e custa uma linha. Acima dele, um modelo que trate tendência e sazonalidade explicitamente: **Holt-Winters** (adequado ao tamanho da série — 72 pontos mensais), **SARIMA**, ou LightGBM com features de mês, lag e média móvel.

E, mais importante que a escolha do modelo: **avaliar em *rolling origin* com 12 janelas** em vez de um único split. Um MAE medido sobre 3 meses tem incerteza grande demais para ranquear modelos com confiança — a diferença entre 25,00 e 30,33 pode não sobreviver a outra janela de teste.

---

## Leitura de engenharia

1. **O maior risco desta questão não é o modelo — é o cadastro.** A resposta muda de 40 para 116 dependendo de qual `product_id` se adota, uma variação de 190%. Nenhuma melhoria de modelagem chega perto desse impacto. **Em um projeto real, a primeira entrega seria um relatório de duplicidade de cadastro, não um forecast.**

2. **Prever um produto isoladamente é a formulação errada do problema.** Com ~27 unidades/mês, a Bússola tem série curta e ruidosa demais para modelagem individual confiável. O que funciona em varejo é modelo hierárquico: prever no nível de **categoria** (onde o sinal é forte porque agrega ruído) e ratear para SKU pela participação histórica. O Sr. Almir tem 500 produtos — treinar 500 modelos independentes é caro e pior do que um modelo por categoria.

3. **O erro do modelo está enviesado numa direção só, e isso importa mais que o MAE.** As três previsões subestimam. Para decisão de estoque, subestimar é o erro caro — foi exatamente o que causou a ruptura de Coletes Salva-Vidas descrita no cenário. **MAE trata os dois erros como iguais, e o negócio não.** A métrica adequada seria assimétrica (*pinball loss* sobre um quantil alto), ou o modelo deveria prever um quantil 0,8 em vez da média.

4. **O dataset unificado foi salvo em Parquet** (`--parquet`) e é reaproveitado pela Q7 e pela camada `gold`. Construir a mesma junção três vezes em três arquivos seria convite a três resultados diferentes.
