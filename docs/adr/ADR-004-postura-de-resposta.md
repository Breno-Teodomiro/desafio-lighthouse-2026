# ADR-004 — Postura de resposta: literal primeiro, senioridade depois

**Data:** 15/08/2026 · **Status:** aceito

## Contexto

Várias questões trazem premissas que colidem com a boa prática de análise de dados:

- A **Q1** proíbe qualquer limpeza, então a média de `orders.total` (28.704,99) mistura 4.847 pedidos cancelados e 2.451 rascunhos.
- A **Q4** manda somar `orders.total` por cliente sem mencionar filtro de status.
- A **Q7** define a matriz como "1 se o cliente comprou ao menos uma vez" sem dizer se pedido cancelado conta como compra — e a resposta **muda** conforme a leitura: sem filtro o primeiro lugar é *Motor de Popa 5331*; com `status='paid'` vira *Vela Mestra 1913*.
- A **Q6** nomeia "Bússola de Bordo 702", que existe com **dois `product_id`** distintos.

O questionário é de tentativa única, provavelmente com gabarito numérico.

## Decisão

Toda questão entrega **primeiro o resultado da leitura literal da premissa** e, em seguida, um bloco curto intitulado **"Leitura de engenharia"** com o cenário tecnicamente correto, o número alternativo e a justificativa.

Nunca substituir silenciosamente a premissa pela boa prática.

## Justificativa

Divergir da premissa arrisca zerar a questão mesmo com a análise certa, porque o corretor pode comparar números. Omitir a crítica desperdiça o único critério que o enunciado declara explicitamente valorizar: *"Eu valorizo mais a organização e a explicação do que o código rodando sem eu entender nada."*

A ordem importa. O número oficial vem primeiro para que um gabarito automático o encontre; a análise vem depois para que um avaliador humano veja o raciocínio. Invertida, a ordem transforma rigor em aparente desobediência.

## Consequências

- Cada `RESPOSTA.md` tem duas seções obrigatórias: resposta literal e leitura de engenharia.
- Questões com ambiguidade material (Q4, Q6, Q7) carregam uma tabela de sensibilidade mostrando como o número muda sob cada leitura.
- O texto fica mais longo. Aceitável — o enunciado pede explicação, não concisão.
