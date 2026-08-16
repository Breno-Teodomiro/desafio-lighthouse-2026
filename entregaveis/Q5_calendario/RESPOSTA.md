# Questão 5 — Dimensão de calendário

**Entregável:** `q5_dim_calendario.sql` (Q5.1) · este documento (Q5.2)

```bash
psql -d lh_nautical -f q5_dim_calendario.sql
```

---

## Resposta

> **O pior dia nas lojas físicas é a QUINTA-FEIRA, com média de R$ 157.154,32 por dia.**
>
> **E o cálculo do estagiário aponta o dia errado.** Sem o calendário, a resposta seria *Segunda-feira* — que na verdade é o **3º** pior dia.

| Dia da semana | Dias no período | Dias sem venda | **Média COM calendário** | Média SEM calendário (estagiário) | Inflação |
|---|---:|---:|---:|---:|---:|
| **Quinta-feira** | 366 | **20** | **R$ 157.154,32** ← pior | R$ 166.238,38 | +5,78% |
| Domingo | 365 | 12 | R$ 157.616,13 | R$ 162.974,19 | +3,40% |
| Segunda-feira | 365 | 7 | R$ 158.241,15 | R$ 161.335,26 ← "pior" | +1,96% |
| Sábado | 365 | 11 | R$ 164.858,27 | R$ 169.980,98 | +3,11% |
| Terça-feira | 365 | 8 | R$ 166.118,83 | R$ 169.841,38 | +2,24% |
| Sexta-feira | 365 | 10 | R$ 170.193,68 | R$ 174.987,87 | +2,82% |
| Quarta-feira | 366 | 10 | R$ 173.605,44 | R$ 178.481,99 | +2,81% |

**Calendário construído:** 2.557 dias, de 01/01/2020 a 31/12/2026, **78 deles sem nenhuma venda**. Faturamento POS total: R$ 419.273.315,30 em 2.479 dias com venda.

---

## Conformidade com as premissas

| Premissa | Implementação |
|---|---|
| Período entre a menor e a maior data de venda | `min()/max()` sobre `created_at` de `orders` filtrado por `pos` — vem dos dados, não de constante digitada |
| Loja aberta todos os dias | `generate_series` gera **todos** os dias; nenhum fim de semana ou feriado é excluído |
| Apenas lojas físicas | `WHERE channel = 'pos'` |
| Dia sem registro = venda 0 | `coalesce(v.valor_venda, 0)` no `LEFT JOIN` |
| "Vendas diárias" = soma por dia | `sum(total) GROUP BY created_at::date` |
| Média sobre todos os dias do calendário | `avg()` sobre a view já densificada — o denominador é o calendário |
| Nome do dia em português | `CASE` explícito sobre `ISODOW` |

---

## Q5.2 — Explicação

### Por que é necessário usar uma tabela de datas em vez de agrupar direto a tabela de vendas

**Porque a tabela de vendas só sabe o que aconteceu, e a pergunta é sobre o que estava disponível.**

`orders` contém uma linha por pedido. Um dia em que a loja abriu e não vendeu nada **não gera linha nenhuma** — ele não existe naquela tabela. Um `GROUP BY dia_semana` direto em `orders` só consegue enxergar os dias que produziram venda, então o denominador da média é "dias com venda", não "dias de operação".

Isso não torna a média *um pouco otimista*. Torna a média **uma resposta para outra pergunta**:

| | Fórmula | O que mede |
|---|---|---|
| Correto | `SUM(vendas) / dias_do_calendário` | Faturamento esperado de um dia de operação |
| Estagiário | `SUM(vendas) / dias_com_venda` | Faturamento médio **condicionado a ter havido venda** |

A segunda é uma média condicional. Ela responde *"quando vendemos numa quinta, quanto vendemos?"* — pergunta legítima, mas inútil para decidir se vale a pena abrir a loja. Para essa decisão, **o dia de faturamento zero é exatamente o dia que mais importa**, e é justamente o que some.

O calendário resolve isso invertendo quem manda no join. Ele é a tabela dirigente — a lista completa e independente dos dias de operação — e as vendas são anexadas a ele:

```sql
FROM gold.dim_calendario c
LEFT JOIN vendas_por_dia v ON v.data = c.data
```

O `LEFT JOIN` garante que nenhum dia do calendário desapareça, e o `COALESCE` transforma a ausência em zero. **`generate_series` é a peça inteira da questão**: é ela que materializa os dias que não existem em `orders`.

### O que aconteceria se um dia da semana tivesse muitos dias sem venda

**Exatamente o que aconteceu aqui: o ranking se inverte, e a decisão de negócio muda.**

O erro do estagiário **não é uniforme**. Ele infla cada dia da semana em proporção ao número de dias vazios daquele dia:

| Dia | Dias sem venda | Denominador cai de… | …para | Inflação |
|---|---:|---:|---:|---:|
| **Quinta-feira** | **20** | 366 | 346 | **+5,78%** |
| Domingo | 12 | 365 | 353 | +3,40% |
| Sábado | 11 | 365 | 354 | +3,11% |
| Sexta / Quarta | 10 | 365/366 | 355/356 | +2,8% |
| Terça | 8 | 365 | 357 | +2,24% |
| **Segunda-feira** | **7** | 365 | 358 | **+1,96%** |

A quinta-feira tem **quase três vezes mais dias vazios que a segunda** (20 contra 7). Ao remover esses 20 dias do denominador, a média da quinta sobe R$ 9.084 e ela **sai do último lugar**. A segunda, que quase não tem dias vazios, sobe só R$ 3.094 e **cai para o último lugar** — sem que nada tenha mudado na realidade.

> **Se o erro fosse uniforme, ele seria inofensivo para o ranking.** Todos os dias inflariam na mesma proporção, os valores estariam errados mas a *ordem* sobreviveria, e o Sr. Almir ainda tomaria a decisão certa. O que torna este erro perigoso é justamente a **distribuição desigual dos dias vazios** — e não há como saber que ela é desigual sem construir o calendário. O erro esconde a evidência da própria existência.

**A consequência prática:** o Sr. Almir fecharia a loja na **segunda-feira**, deixando aberta a quinta-feira — que é o dia realmente pior. Tomaria a decisão exatamente ao contrário, com base num número que parecia certo.

---

## Duas armadilhas técnicas que o arquivo evita

**1. `to_char(data, 'TMDay')` não é usado.** É a forma "óbvia" de obter o nome do dia, e ela depende de `lc_time` do servidor. Numa instalação padrão devolve `'Monday   '` — em inglês, e preenchido com espaços até 9 caracteres. Mesmo com locale pt-BR configurado, devolve `'segunda'`, nunca a forma `'Segunda-feira'` que o enunciado pede. O `CASE` explícito é portátil, não depende de configuração da instância e entrega exatamente o formato pedido.

**2. `EXTRACT(ISODOW)`, não `EXTRACT(DOW)`.** `ISODOW` numera 1=Segunda até 7=Domingo, que já é a ordem da semana brasileira — o `ORDER BY num_dia_semana` sai correto sem nenhum `CASE` de reordenação. `DOW` numera 0=Domingo e exigiria remapeamento manual, que é uma linha a mais para errar.

**3. Agregação antes do join.** As vendas são somadas por dia **antes** de encontrar o calendário. Juntar no grão de pedido multiplicaria as linhas do calendário — um dia com 30 pedidos viraria 30 linhas de calendário — e o `avg()` final seria calculado sobre um denominador inflado.

---

## Leitura de engenharia

1. **A pergunta do Sr. Almir tem uma resposta correta e uma recomendação oposta a ela.** Sim, a quinta-feira é o pior dia. Mas a diferença entre o pior (R$ 157.154) e o melhor (R$ 173.605) é de **apenas 10,5%** — e entre a quinta e o domingo, de **0,3%**. Isso não é sazonalidade semanal; é ruído. **Não há dia da semana que justifique fechar a loja.** Fechar às quintas eliminaria R$ 57,5 milhões de faturamento anualizado para economizar um dia de custo fixo, com base numa diferença que qualquer semana atípica inverte.

2. **Os 78 dias sem venda não estão distribuídos no tempo, e isso muda a leitura.** Eles se concentram nos anos iniciais: **25 em 2020, 20 em 2021, 13 em 2022, 11 em 2023, 6 em 2024, 1 em 2025 e 2 em 2026.** Ou seja, dia sem venda é um fenômeno de **operação em ramp-up**, não uma característica atual do negócio. Nos últimos dois anos a loja praticamente não tem dias vazios. Isso significa que o erro do estagiário estaria **encolhendo com o tempo** — e uma análise feita só sobre 2025 quase não seria afetada por ele. A armadilha é histórica.

3. **O calendário desta questão está incompleto para uso real.** Ele tem dias, mas não tem **feriados**, e a premissa "a loja esteve aberta em todos os dias" é uma simplificação que o enunciado impõe. Um calendário de varejo de produção precisa de: flag de feriado nacional/estadual/municipal, flag de dia útil, indicador de véspera, e — para uma varejista náutica — marcação de **alta temporada**, que aqui provavelmente explica mais variação do que o dia da semana. A dimensão criada aqui já traz ano, mês, trimestre e fim de semana para servir ao dashboard; o resto é o próximo passo.

4. **A pergunta certa provavelmente não é "qual dia fechar".** É *"qual dia tem a pior relação entre faturamento e custo de operação?"*. Faturamento sozinho não decide fechamento: um domingo com meia equipe e faturamento 5% menor pode ser mais rentável que uma quarta cheia. Os dados de custo não estão nesta base, e é honesto dizer isso em vez de deixar a métrica de receita passar por métrica de lucro.

5. **A dimensão foi materializada em `gold`, não em `raw`.** `raw` espelha a fonte, e nenhum calendário veio de CSV. Ela é uma tabela física (não uma CTE) porque o dashboard e as demais análises a reaproveitam — e uma dimensão de datas compartilhada é o que garante que dois visuais diferentes concordem sobre quantas quintas-feiras existiram no período.
