# Respostas em texto plano

> Mesmo conteúdo de [`RESPOSTAS-PARA-O-FORMULARIO.md`](RESPOSTAS-PARA-O-FORMULARIO.md),
> sem marcação. **Use este arquivo se o campo do formulário for texto simples** —
> ali as tabelas em Markdown virariam uma parede de `|` e os destaques
> apareceriam como `**asterisco**` literal.
>
> As tabelas viraram listas no formato `coluna: valor`, que se lê bem sem
> renderização. **Nenhum número mudou.**


---

## Campo 1.3

Tese: orders é estruturalmente confiável e semanticamente não pronta. O que falta não é limpeza de sujeira — é política de negócio.

Cada afirmação abaixo tem uma consulta correspondente no apêndice -- DIAGNÓSTICO do arquivo SQL.

(A) OUTLIERS EM TOTAL: EXISTEM ESTATISTICAMENTE, MAS NÃO SÃO DEFEITO

  - Medida: Q1 · Mediana · Q3 | Valor: 13.171,24 · 25.917,84 · 40.941,88
  - Medida: Média | Valor: 28.704,99
  - Medida: Razão média / mediana | Valor: 1,108
  - Medida: Desvio padrão | Valor: 19.425,64
  - Medida: Cerca superior de Tukey (Q3 + 1,5·IQR) | Valor: 82.597,85
  - Medida: Pedidos acima da cerca | Valor: 452 (0,92%)
  - Medida: Receita que esses 452 representam | Valor: 2,94%
  - Medida: Pedidos com total ≤ 0 | Valor: 0

A amplitude — de R$ 32,62 a R$ 127.262,02, uma razão de 3.901× — parece alarmante isolada, e é o número que normalmente motiva um "tem outlier, precisa limpar".

Mas a pergunta certa não é "existe valor extremo?" e sim "a distribuição tem cauda pesada?". Média ≈ mediana (razão 1,108) diz que não: a distribuição é quase simétrica. Os 452 pedidos acima da cerca são 0,92% das linhas e apenas 2,94% da receita — não movem nenhum agregado. E não há um único total ≤ 0, que seria o sinal real de erro de captura.

Veredito: são tickets legítimos de alto valor — motores, eletrônica náutica — em uma varejista cujo mix vai de cabo a lancha. Não remover; segmentar.

Observação de faro. Ticket quase simétrico é atípico em varejo, onde se espera distribuição log-normal com cauda longa. Isso é evidência de que a base é sintética, e recomenda cautela ao extrapolar qualquer conclusão de negócio daqui para o mundo real. Não afeta a validade técnica do exercício; afeta o peso das recomendações.

(B) QUALIDADE: A TABELA EM SI ESTÁ LIMPA

  - Verificação: Nulos nas 13 colunas | Resultado: Zero, exceto salesperson_id
  - Verificação: salesperson_id nulo | Resultado: 24.131 (49,2%)
  - Verificação: ...e 100% desses nulos estão no canal ecommerce | Resultado: pos: 0 de 14.656 sem vendedor
  - Verificação: id duplicados | Resultado: 0 (48.998 distintos)
  - Verificação: order_number duplicados | Resultado: 0 (48.998 distintos)
  - Verificação: subtotal − discount_amount = total | Resultado: 48.998 de 48.998
  - Verificação: Tokens de lixo (?, n/a, asdf) | Resultado: nenhum em orders

O único nulo da tabela é estrutural, não uma falha de coleta: venda de e-commerce não tem vendedor atribuído porque não houve atendente. A prova é o Diagnóstico 2 — nenhum pedido pos tem salesperson_id nulo, e 70,3% dos ecommerce têm. Preencher isso com COALESCE seria inventar dado; o tratamento correto é ler NULL aqui como "venda sem vendedor" e nada mais.

A aritmética interna fecha em 100% das linhas, e as duas chaves candidatas são únicas. Estruturalmente, não há o que consertar.

(C) OS TRÊS BLOQUEADORES REAIS

1. A média mistura quatro coisas diferentes.

  - Status: paid | Pedidos: 34.365 | %: 70,1% | Soma de total: R$ 985.741.294,26 | Ticket médio: R$ 28.684,45
  - Status: confirmed | Pedidos: 7.335 | %: 15,0% | Soma de total: R$ 213.625.785,28 | Ticket médio: R$ 29.124,17
  - Status: cancelled | Pedidos: 4.847 | %: 9,9% | Soma de total: R$ 137.418.441,62 | Ticket médio: R$ 28.351,24
  - Status: draft | Pedidos: 2.451 | %: 5,0% | Soma de total: R$ 69.701.680,64 | Ticket médio: R$ 28.438,06

Os R$ 28.704,99 somam quatro estágios do ciclo de vida do pedido. R$ 207,1 milhões (14,7% do GMV) são cancelled + draft e nunca viraram receita. O ticket médio realizado é R$ 28.684,45.

A diferença entre os dois números é pequena — 0,07% — e é exatamente por isso que o problema é perigoso: ele não aparece no ticket médio, mas infla o faturamento total em 14,7%. Quem responder "qual foi nosso faturamento?" com SUM(total) erra em R$ 207 milhões.

2. O recorte temporal é inválido para série temporal.

created_at vai até 31/12/2026, e 4.259 pedidos (8,69%) têm data posterior a hoje (referência: 15/08/2026). A distribuição anual é monotonicamente crescente — 4.466 pedidos em 2020 até 10.268 em 2026 — o que faz 2026 parecer o melhor ano da série quando na verdade é um ano ainda não vivido.

Qualquer YoY, tendência ou média móvel que inclua 2026 está lendo dado futuro como se fosse realizado. Exige data de corte explícita antes de qualquer análise temporal.

3. Os carimbos de tempo não carregam informação.

placed_at = created_at = updated_at em 48.998 de 48.998 linhas (100%).

Não existe linha do tempo do pedido. É impossível medir lead time, tempo até o pagamento, tempo até a expedição ou qualquer intervalo entre eventos. Isso não é sujeira — as colunas estão preenchidas e são válidas. É ausência de sinal, e limita o que a tabela consegue responder: toda pergunta sobre duração está fora de alcance.

(D) VEREDITO: PRONTA PARA ANÁLISE, OU EXIGE TRATAMENTO?

Não exige tratamento prévio no sentido de limpeza — não há nulo espúrio para imputar, duplicata para remover, tipo para corrigir nem outlier para descartar. Uma rotina de data cleaning rodando aqui não teria o que fazer.

Exige três definições de negócio antes do primeiro gráfico:

1. Quais status contam como venda? Sem isso, todo número de faturamento é ambíguo em 14,7%.
2. Qual é a data de corte? Sem isso, toda série temporal inclui 8,7% de futuro.
3. Qual é a pergunta? Se envolver duração, orders não responde.

E exige relacionamento com outras tabelas para quase tudo que interessa. É o ponto mais importante do diagnóstico: orders não tem grão de produto. Ela sabe quanto cada pedido custou, mas não o que foi vendido. Mix de produto, categoria, margem, curva ABC e análise de cesta são todos impossíveis a partir daqui — dependem de order_items → product_variants → products → categories, e order_items sequer tem product_id (a variante é obrigatória no caminho).

Resumo em uma frase: orders é confiável como fonte e insuficiente como base analítica — não por defeito dos dados, mas por escopo da tabela.

---


---

## Campo 4.2

1. COMO CHEGUEI NAS CATEGORIAS MAIS VENDIDAS: O MAPEAMENTO DA CADEIA DE CHAVES

orders sabe quanto cada pedido custou, mas não o que foi vendido. Chegar em categoria exige quatro saltos:

    orders.customer_id
      └─ orders.id ──────────────── order_items.order_id
           └─ order_items.product_variant_id ── product_variants.id
                └─ product_variants.product_id ── products.id
                     └─ products.category_id ─── categories.id

O salto que costuma ser pulado é o segundo: order_items não tem product_id. Ela referencia a variante, não o produto. Quem tenta juntar order_items direto em products não encontra chave, e a saída improvisada — casar por nome, ou assumir que product_variant_id é product_id — produz um número que parece razoável e está errado. product_variants é obrigatória no caminho porque é ela que carrega o product_id.

categories só entra no fim, para trocar o id pelo nome. A agregação já está fechada antes disso.

2. A LÓGICA DO FILTRO DE DIVERSIDADE MÍNIMA

    categorias_por_cliente AS (
        SELECT o.customer_id, count(DISTINCT p.category_id) AS diversidade_categorias
        FROM raw.orders o
        JOIN raw.order_items      oi ON oi.order_id = o.id
        JOIN raw.product_variants pv ON pv.id       = oi.product_variant_id
        JOIN raw.products         p  ON p.id        = pv.product_id
        GROUP BY o.customer_id
    )
    ...
    WHERE cc.diversidade_categorias >= 13   -- ANTES do ORDER BY / LIMIT
    ORDER BY pc.ticket_medio DESC, pc.customer_id ASC
    LIMIT 10

Dois pontos:

COUNT(DISTINCT category_id) é imune ao fan-out. Esta CTE precisa fazer join — é o único caminho até a categoria — e o join multiplica linhas. Mas contar valores distintos não se importa com quantas vezes cada valor apareceu, então o resultado é correto apesar da multiplicação. É por isso que a diversidade pode ser calculada no grão de item, enquanto o faturamento não pode.

O filtro vem antes do LIMIT, e a ordem importa. Filtrar depois devolveria "os que sobraram do top 10 geral", que é outra pergunta e daria menos de 10 clientes. O WHERE roda sobre o universo inteiro; o LIMIT corta o ranking já filtrado.

Desempate: ORDER BY ticket_medio DESC, customer_id ASC. Não houve empate real nesta base, mas sem o segundo critério o resultado seria não-determinístico se houvesse — e um ranking que muda de execução para execução é um ranking que não se pode auditar.

⚠️ Crítica ao critério (o achado mais relevante desta questão). O filtro de diversidade não filtra praticamente ninguém:

| Categorias distintas | Clientes | % |
|---:|---:|---:|
| 11 | 2 | 0,10% |
| 12 | 27 | 1,35% |
| 13 | 200 | 10,00% |
| 14 | 1.771 | 88,55% |

Só existem 14 categorias na loja, e 1.971 de 2.000 clientes (98,5%) compraram de 13 ou mais. O critério que a Diretoria imaginou como marca de sofisticação — "navega por diversas categorias" — é satisfeito por quase toda a base.

Na prática, o ranking é ordenado exclusivamente pelo ticket médio: os 10 selecionados teriam sido os mesmos sem o filtro. A definição de "cliente fiel" do enunciado tem dois critérios, mas apenas um deles opera.

3. COMO GARANTI QUE A CONTAGEM DE ITENS REFLETISSE APENAS OS TOP 10

A lista dos 10 é materializada em uma CTE (top10_fieis) e usada como tabela dirigente do join:

    FROM top10_fieis          t
    JOIN raw.orders           o  ON o.customer_id = t.customer_id
    JOIN raw.order_items      oi ON oi.order_id   = o.id
    JOIN raw.product_variants pv ON pv.id         = oi.product_variant_id
    JOIN raw.products         p  ON p.id          = pv.product_id

O INNER JOIN a partir de top10_fieis é o que restringe o universo. A alternativa — recalcular o critério de diversidade dentro da consulta de itens — traria de volta os 1.971 clientes que passam no filtro e inflaria a contagem em quase 200×.

A consulta seguinte no arquivo é uma asserção explícita: conta os clientes do grupo e imprime OK se forem exatamente 10. É barata e transforma uma suposição em verificação.

---


---

## Campo 5.2

POR QUE É NECESSÁRIO USAR UMA TABELA DE DATAS EM VEZ DE AGRUPAR DIRETO A TABELA DE VENDAS

Porque a tabela de vendas só sabe o que aconteceu, e a pergunta é sobre o que estava disponível.

orders contém uma linha por pedido. Um dia em que a loja abriu e não vendeu nada não gera linha nenhuma — ele não existe naquela tabela. Um GROUP BY dia_semana direto em orders só consegue enxergar os dias que produziram venda, então o denominador da média é "dias com venda", não "dias de operação".

Isso não torna a média um pouco otimista. Torna a média uma resposta para outra pergunta:

  - Correto | Fórmula: SUM(vendas) / dias_do_calendário | O que mede: Faturamento esperado de um dia de operação
  - Estagiário | Fórmula: SUM(vendas) / dias_com_venda | O que mede: Faturamento médio condicionado a ter havido venda

A segunda é uma média condicional. Ela responde "quando vendemos numa quinta, quanto vendemos?" — pergunta legítima, mas inútil para decidir se vale a pena abrir a loja. Para essa decisão, o dia de faturamento zero é exatamente o dia que mais importa, e é justamente o que some.

O calendário resolve isso invertendo quem manda no join. Ele é a tabela dirigente — a lista completa e independente dos dias de operação — e as vendas são anexadas a ele:

    FROM gold.dim_calendario c
    LEFT JOIN vendas_por_dia v ON v.data = c.data

O LEFT JOIN garante que nenhum dia do calendário desapareça, e o COALESCE transforma a ausência em zero. generate_series é a peça inteira da questão: é ela que materializa os dias que não existem em orders.

O QUE ACONTECERIA SE UM DIA DA SEMANA TIVESSE MUITOS DIAS SEM VENDA

Exatamente o que aconteceu aqui: o ranking se inverte, e a decisão de negócio muda.

O erro do estagiário não é uniforme. Ele infla cada dia da semana em proporção ao número de dias vazios daquele dia:

  - Dia: Quinta-feira | Dias sem venda: 20 | Denominador cai de…: 366 | …para: 346 | Inflação: +5,78%
  - Dia: Domingo | Dias sem venda: 12 | Denominador cai de…: 365 | …para: 353 | Inflação: +3,40%
  - Dia: Sábado | Dias sem venda: 11 | Denominador cai de…: 365 | …para: 354 | Inflação: +3,11%
  - Dia: Sexta / Quarta | Dias sem venda: 10 | Denominador cai de…: 365/366 | …para: 355/356 | Inflação: +2,8%
  - Dia: Terça | Dias sem venda: 8 | Denominador cai de…: 365 | …para: 357 | Inflação: +2,24%
  - Dia: Segunda-feira | Dias sem venda: 7 | Denominador cai de…: 365 | …para: 358 | Inflação: +1,96%

A quinta-feira tem quase três vezes mais dias vazios que a segunda (20 contra 7). Ao remover esses 20 dias do denominador, a média da quinta sobe R$ 9.084 e ela sai do último lugar. A segunda, que quase não tem dias vazios, sobe só R$ 3.094 e cai para o último lugar — sem que nada tenha mudado na realidade.

Se o erro fosse uniforme, ele seria inofensivo para o ranking. Todos os dias inflariam na mesma proporção, os valores estariam errados mas a ordem sobreviveria, e o Sr. Almir ainda tomaria a decisão certa. O que torna este erro perigoso é justamente a distribuição desigual dos dias vazios — e não há como saber que ela é desigual sem construir o calendário. O erro esconde a evidência da própria existência.

A consequência prática: o Sr. Almir fecharia a loja na segunda-feira, deixando aberta a quinta-feira — que é o dia realmente pior. Tomaria a decisão exatamente ao contrário, com base num número que parecia certo.

---


---

## Campo 6.3

COMO O BASELINE FOI CONSTRUÍDO

    serie  = df_alvo.groupby("mes")["quantidade"].sum().reindex(indice_denso, fill_value=0)
    treino = serie.loc[:"2025-12"]          # corte físico, antes de qualquer estatística
    ma3    = treino.iloc[-3:].mean()        # (34 + 60 + 22) / 3 = 38,6667
    previsao = pd.Series(ma3, index=pd.period_range("2026-01", "2026-03", freq="M"))

Quatro passos:

1. Dataset unificado no grão de linha de item, juntando os 4 CSVs pela cadeia order_items → product_variants → products e order_items → orders. order_items não tem product_id — a variante é obrigatória no caminho.
2. Agregação mensal por orders.created_at (a data em que a demanda se manifestou).
3. Índice mensal denso. O reindex é a linha mais importante: sem ele, um mês sem venda simplesmente não aparece na série, e "os últimos 3 meses" passaria a significar "as últimas 3 linhas existentes" — que podem estar espalhadas por seis meses do calendário. A média sairia errada sem dar nenhum sinal de que algo está errado. Esta série tem um mês zerado (out/2020), então o risco é real, não teórico.
4. Média das 3 últimas observações do treino, aplicada aos 3 meses do horizonte.

COMO EVITEI DATA LEAKAGE

- Corte físico do dataset em 2025-12 na própria construção da série, não como filtro aplicado depois. A série de treino e a série de teste são objetos separados.
- O índice denso do treino termina em 2025-12 e não além — assim um mês vazio de 2026 não pode entrar na janela por efeito colateral do reindex.
- Nenhuma realimentação com valores reais do período de teste.
- A janela out/nov/dez-2025 é estritamente anterior a cada uma das três datas previstas.
- Uso de orders.created_at, não de payments.paid_at. É um ponto sutil: o pagamento acontece depois do pedido, então usar a data de pagamento embutiria informação posterior ao evento que se quer prever. A demanda se manifesta quando o pedido é feito.

UMA LIMITAÇÃO DO MODELO

Ele emite um único número para todo o horizonte. A previsão de janeiro, fevereiro e março é idêntica — 38,67 —, o que é inútil para escalonar a compra mês a mês, que é exatamente o problema do Sr. Almir. Um modelo que não distingue meses não pode informar uma decisão que é tomada por mês.

(As demais limitações estão na seção Q6.5.b.)

---


---

## Campo 7.3

COMO A MATRIZ FOI CONSTRUÍDA

Cadeia de chaves. Dois joins, um motivo para cada:

    order_items ──> orders            (para chegar em customer_id)
    order_items ──> product_variants  (para subir de VARIANTE para PRODUTO)
                           └──> products

order_items não carrega customer_id nem product_id. O primeiro vem do pedido; o segundo exige passar pela variante. A pergunta da Marina é sobre produto ("quem compra lancha leva defensa"), não sobre variante, então esse salto é obrigatório.

A matriz.

    matriz = (pd.crosstab(df["customer_id"], df["product_id"]) > 0).astype("float64")

crosstab conta ocorrências; o > 0 colapsa qualquer contagem em True. É assim que a premissa "ignore a quantidade comprada" vira código: um cliente que comprou 7 unidades e outro que comprou 1 são idênticos na matriz.

  - Propriedade: Dimensões | Valor: 2.000 clientes × 500 produtos
  - Propriedade: Valores distintos | Valor: {0.0, 1.0} — estritamente binária
  - Propriedade: Densidade | Valor: 13,55%
  - Propriedade: Compradores por produto (média) | Valor: 271

⚠️ A armadilha que muda a resposta: agrupar por nome em vez de product_id.

Existem 4 produtos com nome duplicado no cadastro. Uma matriz construída sobre df["produto"] tem 496 colunas em vez de 500, fundindo esses homônimos — e o resultado muda:

| # | Top-3 pelo caminho ERRADO (por nome) | Cosseno |
|---:|---|---:|
| 1 | asdf ← lixo de cadastro | 0,278886 |
| 2 | Motor de Popa 5331 | 0,256553 |
| 3 | Cabo Náutico 2105 | 0,256239 |

O produto de nome asdf sobe ao 1º lugar. Não é um sinal — é um artefato: dois produtos de lixo, sem relação entre si, foram somados em uma coluna só, e a união dos seus compradores criou uma sobreposição artificial com o motor.

A matriz é sempre construída por product_id. O nome só entra na hora de renderizar o ranking, e quando dois produtos compartilham o nome o rótulo recebe o id (asdf (id=342)) para que duas linhas não pareçam idênticas.

O QUE A SIMILARIDADE DE COSSENO SIGNIFICA NESTE CONTEXTO

Para vetores binários, o cosseno tem uma forma fechada:

    cos(i, j) = |Ci ∩ Cj| / √(|Ci| · |Cj|)

— o número de clientes que compraram ambos os produtos, normalizado pela raiz do produto das duas popularidades. É o coeficiente de Ochiai.

A normalização é o ponto inteiro da métrica. Sem ela, o "mais similar" a qualquer produto seria sempre o mais vendido da loja, porque ele tem interseção grande com todo mundo. Dividir pelas normas responde à pergunta certa: "a sobreposição entre esses dois públicos é maior do que se esperaria pelo tamanho deles?". O que se mede é afinidade de público, não volume.

Implementação — normalizando cada coluna em L2, o produto escalar entre duas colunas já é o cosseno, então a matriz inteira sai de uma multiplicação:

    A = matriz.to_numpy()
    normas = np.linalg.norm(A, axis=0)
    normas[normas == 0] = 1.0        # guarda para produto sem comprador (cold start)
    S = (A / normas).T @ (A / normas)

O que o cosseno NÃO significa aqui: ele não mede co-ocorrência no mesmo carrinho. Mede sobreposição de base de clientes ao longo de todo o histórico. Um cliente que comprou motor em 2021 e vela em 2025 contribui para a similaridade entre motor e vela exatamente como se os tivesse levado juntos. Ver o bônus abaixo.

---
