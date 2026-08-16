# ADR-008 — Sem dbt: SQL puro versionado, com a disciplina do dbt reproduzida à mão

**Data:** 16/08/2026 · **Status:** aceito
*(registra formalmente uma decisão tomada na Onda 0 e até aqui documentada só
de passagem em `docs/PLANO_ONDAS.md` e no `CLAUDE.md`)*

## Contexto

A proposta inicial deste projeto era **DuckDB + dbt** — a escolha que eu faria
para um pipeline analítico de verdade, e que o Breno havia aceitado. Duas
leituras do enunciado a derrubaram.

**Primeira: o motor não é livre.** A Questão 2 pede um script que gere DDL
**para PostgreSQL**, e a Questão 3 pede a carga **num banco PostgreSQL**. Não é
sugestão, é o enunciado. Com Q2 e Q3 presas ao PostgreSQL, rodar Q1/Q4/Q5 em
DuckDB criaria duas fontes de verdade para os mesmos números — e a primeira
divergência de arredondamento entre os dois motores custaria mais tempo do que
o DuckDB economizaria.

**Segunda, e decisiva: o artefato avaliado é o arquivo, não o resultado.** O
formulário tem campos de upload para *"o código SQL utilizado"* e *"o código
Python utilizado"*. Quem corrige abre um arquivo e lê. Um modelo dbt não é um
arquivo SQL — é um `.sql` com `{{ ref() }}`, `{{ config() }}` e `{{ source() }}`
que **não roda** se colado num cliente PostgreSQL. Entregar isso obrigaria o
avaliador a instalar dbt, criar um `profiles.yml` e apontá-lo para um banco que
ele não tem, só para ver se a consulta da Questão 4 está certa.

## Decisão

**Sem dbt e sem DuckDB.** PostgreSQL local como banco canônico, SQL puro em
arquivos versionados sob `sql/{raw,silver,gold,testes}`, e cada questão como um
arquivo autocontido que roda sozinho.

## Justificativa

O que o dbt entrega é **governança**: separação staging → marts, testes de
dados, documentação gerada, lineage. Nada disso foi abandonado — só foi
implementado sem a ferramenta:

| O que o dbt daria | Como está resolvido aqui |
|---|---|
| `staging` → `intermediate` → `marts` | medalhão em 3 schemas (ADR-002), um arquivo SQL por camada |
| `dbt test` (not_null, unique, relationships) | `sql/testes/` + as 37 FKs validadas no `COMMIT` da carga + 46 conferências adversariais em `tests/verificar_respostas.py` |
| `dbt docs` | `docs/DICIONARIO_DADOS.md`, `docs/QUALIDADE_DADOS.md`, `powerbi/MODELO.md` |
| lineage | `docs/MAPA_QUESTOES.md` liga cada número à sua origem |
| idempotência | cada script é `DROP ... CREATE`, roda quantas vezes quiser |

A conferência adversarial, aliás, é **mais forte** do que um `dbt test`
convencional: cada resposta é recalculada pela tecnologia **oposta** à do
entregável — Q1/Q4/Q5 saem em SQL e são refeitas em Python sobre os CSVs;
Q6/Q7 saem em pandas e são refeitas em SQL sobre o banco. Um `not_null` não
pega erro de lógica de negócio; recalcular por outro caminho pega.

E há o critério explícito do avaliador: o Tech Lead fictício declara valorizar
**organização e explicação acima de código complexo**. Uma camada de
ferramenta que ele não pediu, que ele teria de instalar para ler a resposta,
tem chance real de contar contra — não a favor.

## Consequências

- **Duplicação proposital entre os entregáveis.** Cada questão repete a leitura
  dos CSVs em vez de importar um módulo comum. É o preço de "roda sozinho", e
  está registrado na ADR-005.
- **Sem `dbt build` para orquestrar.** O `Makefile` faz esse papel: `make db`,
  `carga`, `questoes`, `powerbi`, `check`, `verificar`.
- **Sem lineage automático.** Se um modelo mudar, a atualização de
  `docs/MAPA_QUESTOES.md` é manual — aceitável num projeto de 7 questões e
  prazo de dias, insustentável num de centenas de modelos.
- **A decisão não se generaliza.** Num pipeline de produção com muitos modelos
  e mais de uma pessoa mexendo, a conclusão se inverte e o dbt volta a ganhar.
  O que decide aqui é que o **artefato avaliado é o arquivo**, e essa é uma
  restrição do desafio, não uma opinião sobre a ferramenta.
