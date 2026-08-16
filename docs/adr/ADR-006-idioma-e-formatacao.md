# ADR-006 — Idioma pt-BR e convenções de formatação

**Data:** 15/08/2026 · **Status:** aceito

## Contexto

O desafio é brasileiro, os avaliadores são brasileiros, e a Q5 exige explicitamente nomes de dia da semana **em português**. O dataset também é brasileiro: CPF, CNPJ, NCM, ICMS, IPI, NF-e.

## Decisão

- **Tudo em pt-BR:** nomes de arquivo, comentários, docstrings, mensagens de log, documentação, commits e rótulos do dashboard.
- **Identificadores de banco em pt-BR** nas camadas `silver` e `gold` (`dim_calendario`, `fato_vendas`). O schema `raw` **mantém os nomes originais em inglês** dos CSVs.
- **Números:** ponto decimal no código e no banco; formato brasileiro (`R$ 28.704,99`) apenas na camada de apresentação.
- **Datas:** ISO (`YYYY-MM-DD`) no código e no banco; `DD/MM/AAAA` na apresentação.
- **Dias da semana em português sem depender de `lc_time`** — mapeamento explícito por `EXTRACT(DOW)`, porque o locale do servidor não é garantido no ambiente do avaliador.

## Justificativa

Manter `raw` em inglês preserva a rastreabilidade direta com os CSVs de origem e com o `schema.sql` gerado pela Q2 — renomear ali quebraria a correspondência um-para-um que a questão pede.

O mapeamento manual dos dias evita a dependência mais frágil da Q5: `TO_CHAR(data, 'Day')` devolve inglês em servidor com locale padrão, e a premissa exige português. Um `CASE` explícito é determinístico em qualquer instalação.

## Consequências

- Há troca de idioma na fronteira `raw` → `silver`, documentada em `docs/DICIONARIO_DADOS.md`.
- Formatação brasileira exige função de apresentação dedicada; nunca formatar no meio do cálculo.
