# Questão 7 — Sistema de recomendação

**Entregável:** `q7_recomendacao.py` (Q7.1) · este documento (Q7.2, Q7.3)

```bash
python3 q7_recomendacao.py --csv-dir ./1-lh_nautical_csv --validar-sklearn
```

---

## Q7.2 — Resposta

> **O produto com maior similaridade ao "Motor de Popa 1949" é o `Motor de Popa 5331`.**

| # | `product_id` | Produto | Cosseno |
|---:|---:|---|---:|
| **1** | **389** | **Motor de Popa 5331** | **0,256553** |
| 2 | 295 | Cabo Náutico 2105 | 0,256239 |
| 3 | 75 | Vela Mestra 1913 | 0,255785 |
| 4 | 337 | Cabo Náutico 9048 | 0,239332 |
| 5 | 55 | GPS Plotter 6249 | 0,237744 |

Item de referência: `product_id` **180**, comprado por **397 clientes**.

**Validação:** a matriz de similaridade calculada à mão confere com `sklearn.metrics.pairwise.cosine_similarity` (`np.allclose` → `True`), é simétrica e tem diagonal 1.

---

## Q7.3 — Explicação

### Como a matriz foi construída

**Cadeia de chaves.** Dois joins, um motivo para cada:

```
order_items ──> orders            (para chegar em customer_id)
order_items ──> product_variants  (para subir de VARIANTE para PRODUTO)
                       └──> products
```

`order_items` não carrega `customer_id` nem `product_id`. O primeiro vem do pedido; o segundo exige passar pela variante. A pergunta da Marina é sobre **produto** ("quem compra lancha leva defensa"), não sobre variante, então esse salto é obrigatório.

**A matriz.**

```python
matriz = (pd.crosstab(df["customer_id"], df["product_id"]) > 0).astype("float64")
```

`crosstab` conta ocorrências; o `> 0` colapsa qualquer contagem em `True`. **É assim que a premissa "ignore a quantidade comprada" vira código:** um cliente que comprou 7 unidades e outro que comprou 1 são idênticos na matriz.

| Propriedade | Valor |
|---|---|
| Dimensões | **2.000 clientes × 500 produtos** |
| Valores distintos | `{0.0, 1.0}` — estritamente binária |
| Densidade | **13,55%** |
| Compradores por produto (média) | 271 |

> ⚠️ **A armadilha que muda a resposta: agrupar por nome em vez de `product_id`.**
>
> Existem **4 produtos com nome duplicado** no cadastro. Uma matriz construída sobre `df["produto"]` tem 496 colunas em vez de 500, fundindo esses homônimos — e o resultado muda:
>
> | # | Top-3 pelo caminho ERRADO (por nome) | Cosseno |
> |---:|---|---:|
> | 1 | **`asdf`** ← lixo de cadastro | 0,278886 |
> | 2 | Motor de Popa 5331 | 0,256553 |
> | 3 | Cabo Náutico 2105 | 0,256239 |
>
> O produto de nome `asdf` sobe ao 1º lugar. **Não é um sinal — é um artefato**: dois produtos de lixo, sem relação entre si, foram somados em uma coluna só, e a união dos seus compradores criou uma sobreposição artificial com o motor.
>
> A matriz é sempre construída por `product_id`. O nome só entra na hora de renderizar o ranking, e quando dois produtos compartilham o nome o rótulo recebe o id (`asdf (id=342)`) para que duas linhas não pareçam idênticas.

### O que a similaridade de cosseno significa neste contexto

Para vetores binários, o cosseno tem uma forma fechada:

```
cos(i, j) = |Ci ∩ Cj| / √(|Ci| · |Cj|)
```

— o número de clientes que compraram **ambos** os produtos, normalizado pela raiz do produto das duas popularidades. É o **coeficiente de Ochiai**.

**A normalização é o ponto inteiro da métrica.** Sem ela, o "mais similar" a qualquer produto seria sempre o mais vendido da loja, porque ele tem interseção grande com todo mundo. Dividir pelas normas responde à pergunta certa: *"a sobreposição entre esses dois públicos é maior do que se esperaria pelo tamanho deles?"*. O que se mede é **afinidade de público**, não volume.

Implementação — normalizando cada coluna em L2, o produto escalar entre duas colunas **já é** o cosseno, então a matriz inteira sai de uma multiplicação:

```python
A = matriz.to_numpy()
normas = np.linalg.norm(A, axis=0)
normas[normas == 0] = 1.0        # guarda para produto sem comprador (cold start)
S = (A / normas).T @ (A / normas)
```

**O que o cosseno NÃO significa aqui:** ele não mede co-ocorrência no mesmo carrinho. Mede sobreposição de base de clientes **ao longo de todo o histórico**. Um cliente que comprou motor em 2021 e vela em 2025 contribui para a similaridade entre motor e vela exatamente como se os tivesse levado juntos. Ver o bônus abaixo.

---

## Limitações

### 1. Não há sinal real, e dá para provar

As 499 similaridades do item de referência têm **média 0,1667** e **desvio 0,0374**. Onde estão os primeiros colocados?

| # | Produto | Cosseno | Distância da média |
|---:|---|---:|---:|
| 1 | Motor de Popa 5331 | 0,256553 | **2,40 σ** |
| 2 | Cabo Náutico 2105 | 0,256239 | 2,39 σ |
| 3 | Vela Mestra 1913 | 0,255785 | 2,38 σ |
| 4 | Cabo Náutico 9048 | 0,239332 | 1,94 σ |
| 5 | GPS Plotter 6249 | 0,237744 | 1,90 σ |

Os três primeiros estão a **2,40 / 2,39 / 2,38 desvios** — estatisticamente indistinguíveis. O gap entre 1º e 2º é de **0,000314 (0,12% relativo)**.

Com densidade de 13,55%, dois produtos quaisquer têm em média ~271 compradores cada em uma base de 2.000: **quase todo par co-ocorre por puro acaso**. A "recomendação" está lendo ruído amostral.

> **Conclusão honesta: não mandar para produção como está.** O ranking é reprodutível e a matemática está correta, mas a diferença entre o 1º e o 3º lugar não sobreviveria a uma reamostragem.

### 2. O resultado inverte com qualquer filtro de status

| Recorte | Top-1 | Cosseno |
|---|---|---:|
| **todos os status (adotado)** | **Motor de Popa 5331** | 0,25655 |
| exclui `draft` | Vela Mestra 1913 | 0,24336 |
| exclui `cancelled` | Vela Mestra 1913 | 0,25879 |
| `paid` + `confirmed` | Vela Mestra 1913 | 0,24520 |
| só `paid` | Vela Mestra 1913 | 0,20459 |

**Quatro de cinco recortes apontam outro produto.** O enunciado é explícito em todas as demais regras (linhas, colunas, valor da célula, métrica, item de referência, tamanho do ranking) e **não menciona status** — então a leitura literal, sem filtro, é a resposta principal. Mas é honesto registrar que a resposta é frágil a uma decisão que o enunciado não tomou.

Vale notar o que isso significa no negócio: um pedido `draft` é um carrinho que nunca virou compra. Incluí-lo na base de "quem comprou" é discutível — e é justamente ele que sustenta o 1º lugar.

### 3. O grão está errado para a pergunta que a Marina fez

> *"Clientes que compram lanchas quase sempre esquecem de levar a defensa."*

Isso é **associação de cesta** — itens no **mesmo pedido**. O que a matriz cliente × produto mede é sobreposição de base de clientes ao longo de anos. São perguntas diferentes, e a segunda não responde à primeira.

**O bônus no script calcula a formulação correta.** Dos **435 pedidos** que contêm o Motor de Popa 1949:

| Produto | Pedidos em comum |
|---|---:|
| **Tinta Antifouling 3228** | **11** |
| Vela Mestra 5034 | 8 |
| Motor de Popa 1376 | 8 |
| Vela Mestra 5825 | 8 |
| `asdf (id=342)` | 8 |

Também sem sinal forte — 11 em 435 pedidos é 2,5% —, mas é a **formulação correta do problema descrito**. Para a vitrine "quem comprou isso também levou", este é o número que importa, e o produto muda: **Tinta Antifouling**, não Motor de Popa.

### 4. Outras limitações

- **Cold start.** Produto novo tem vetor nulo e similaridade zero com tudo. O código tem guarda para não gerar `NaN`, mas guarda não é solução: o produto simplesmente nunca será recomendado.
- **Viés de popularidade mitigado, não eliminado.** A normalização L2 corrige a maior parte, mas produtos muito populares ainda têm mais chance de aparecer em qualquer top-N.
- **Ignora quantidade, preço, recência e devolução.** Um item comprado e **devolvido** conta como compra. Recomendar o que o cliente devolveu é pior que não recomendar nada.
- **Ignora o tempo.** Uma compra de 2020 pesa igual a uma de 2026.
- **Recomenda substitutos, não complementos.** O top-1 é outro **motor de popa** — quem acabou de comprar um motor não quer outro motor. A métrica encontra produtos com público parecido, e público parecido é justamente a definição de *concorrente*. Para cross-sell, o desejado é o oposto: itens complementares. O bônus de cesta capta isso melhor (tinta antifouling é acessório de motor).
- **Sem avaliação offline.** O correto seria segurar as últimas compras de cada cliente, prever, e medir *precision@5* contra um baseline de popularidade. **Sem essa comparação, não há como afirmar que o modelo é melhor que "recomende os 5 mais vendidos".**

---

## Leitura de engenharia

1. **O que eu entregaria de verdade para a Marina não é este ranking.** Seria o de co-ocorrência de cesta, com *lift* em vez de contagem bruta, e com um limiar mínimo de suporte para não recomendar com base em 11 pedidos. Custa as mesmas 15 linhas e responde à pergunta que ela realmente fez.

2. **O 1º lugar ser "outro motor de popa" é o achado mais informativo da questão.** Ele mostra, em um exemplo, que a métrica está funcionando exatamente como projetada e mesmo assim entregando a recomendação errada para o objetivo de negócio. É a diferença entre *"similar"* e *"complementar"* — e nenhuma quantidade de ajuste na similaridade de cosseno conserta isso, porque o problema está na escolha da métrica, não na sua implementação.

3. **A base é sintética, e a ausência de sinal provavelmente reflete isso.** Densidade de 13,55% com 500 produtos e cerca de 271 compradores por produto sugere atribuição aleatória de compras. Em base real, a densidade seria muito menor (0,1–2%) e a estrutura de co-compra seria muito mais forte. **O método está correto; o dataset é que não tem o padrão que ele procura** — e dizer isso vale mais do que apresentar um top-5 com ar de descoberta.

4. **Sobre não usar sklearn.** A biblioteca é permitida, e usá-la seria uma linha. Escrever `Xn.T @ Xn` explicitamente demonstra entender que o cosseno sobre colunas normalizadas é um produto de matrizes — e a flag `--validar-sklearn` confere o resultado contra a implementação de referência, de forma que a escolha não custa confiabilidade. Para 500×500 a diferença de desempenho é irrelevante; para 500 mil produtos, nenhuma das duas serviria e a conversa passaria a ser sobre ANN (`faiss`, `annoy`) ou fatoração matricial.

5. **Nada foi removido do resultado.** Se um nome-lixo cair no top-5, ele é **exibido com marca de alerta**, nunca descartado em silêncio: remover seria "limpar" um resultado, e o fato de `asdf` aparecer é informação sobre o cadastro que o negócio precisa ver.
