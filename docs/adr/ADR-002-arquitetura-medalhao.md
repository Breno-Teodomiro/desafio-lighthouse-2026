# ADR-002 — Medalhão em três schemas no mesmo banco

**Data:** 15/08/2026 · **Status:** aceito

## Contexto

O desafio impõe uma tensão direta: as questões 1, 2 e 3 exigem dados **brutos, sem tratamento** ("Não faça limpeza nem tratamento dos dados", "Não faça tratamentos como: Remoção de nulos ou correção de caracteres especiais"), enquanto o dashboard obrigatório precisa de dados limpos para comunicar qualquer coisa com honestidade.

O perfilamento encontrou 22 classes distintas de sujeira — de `returns.reason` poluído de 6 para 32 valores por typos e espaçamento, até uma coluna EAV misturando números, texto e booleanos.

## Decisão

Três schemas no mesmo banco `lh_nautical`:

| Schema | Conteúdo | Consumidores |
|---|---|---|
| `raw` | Os 24 CSVs como vieram, tipos permissivos, lixo textual preservado | Q1, Q2, Q3, Q4, Q5 |
| `silver` | Tipagem forte, junk-nulls normalizados, categóricos canonizados, EAV desempacotado | Q6, Q7 e análises de apoio |
| `gold` | Star schema `dim_*` / `fato_*` e agregados | Power BI |

## Justificativa

A separação resolve a tensão sem contradizer nenhuma premissa: as respostas das questões saem de `raw`, exatamente como o enunciado manda, e o dashboard sai de `gold`.

Mais do que um arranjo de conveniência, essa separação **é o argumento da Q1.3**. A pergunta "o dataset está pronto para análises ou exigiria tratamento prévio?" ganha uma resposta demonstrável: existe um schema que é a resposta literal e outro que é a resposta útil, e a distância entre os dois está catalogada em `docs/QUALIDADE_DADOS.md`.

## Consequências

- Custo de armazenamento triplicado — irrelevante para 36 MB.
- Toda consulta precisa qualificar o schema; nunca confiar no `search_path`.
- `silver` e `gold` são **Could** no corte MoSCoW: se o prazo apertar, as 7 questões e o dashboard sobrevivem com `raw` + agregação direta.
