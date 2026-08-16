# Plano de Desenvolvimento — Desafio Lighthouse 2026 (LH Nautical)

## Contexto

O Desafio Técnico Lighthouse 2026 (trilha **Dados e IA**) é a etapa classificatória do processo seletivo da Indicium. O objetivo é responder **7 questões técnicas** sobre um dump relacional de 24 CSVs de uma varejista náutica fictícia (LH Nautical, 2020–2026, 433.424 linhas / 36 MB), somadas a **um dashboard obrigatório** em ferramenta de BI.

**Restrições que moldam todo o plano:**

| Restrição | Origem | Consequência |
|---|---|---|
| Prazo **17/08/2026 08h** — restam a noite de 15/08 e o dia 16/08 | Edital §3.1 + confirmação do usuário | Ondas curtas, paralelismo agressivo, escopo com corte MoSCoW explícito |
| **Tentativa única**, sem autosave, sem edição pós-envio | Edital p.10 e rodapé do formulário | Respostas montadas em rascunho versionado; conferência dupla dos números |
| Nota de corte **7,0**, classificatória | Edital §3.1 | Não basta acertar: a explicação vale tanto quanto o número |
| Nenhuma restrição de stack, ferramenta ou uso de IA | Edital (verificado: 0 ocorrências de plágio/IA/ferramenta) | Liberdade total de arquitetura |
| **Dashboard é obrigatório** e em ferramenta de BI | `Formulario_de_Questoes.md`: *"O que deve ser entregue: Dashboard (Power BI, Looker Studio, Tableau, etc.)"* | Power BI é entrega principal; notebook/PDF/HTML são complementos |
| Premissas por questão são **literais e restritivas** (ex.: Q2 proíbe pandas) | Formulário | Violar premissa = desconsiderado. Cada questão tem gate de conformidade |

O que o Tech Lead fictício declara valorizar — *"organização e explicação acima de código rodando sem eu entender"* — é o critério real de avaliação. O plano trata **documentação e rastreabilidade como entregável de primeira classe**, não como sobra.

**Resultado pretendido:** repositório público de portfólio em `git@github.com:Breno-Teodomiro/desafio-lighthouse-2026.git` contendo os 7 artefatos avaliáveis prontos para upload, o pipeline que os produz, o dashboard Power BI, e a documentação que sustenta cada decisão.

### Ponto de partida: 5 das 7 respostas já foram calculadas no planejamento

Perfilei os 24 CSVs (433.424 linhas, integridade referencial perfeita nos 37 relacionamentos, 22 classes distintas de sujeira catalogadas) e antecipei as respostas numéricas. **O plano não parte do zero — parte de números já conferidos**, o que muda a natureza da execução: de "descobrir" para "formalizar, documentar e blindar".

| Q | Resposta antecipada | Confiança |
|---|---|---|
| 1.2 | Média de `orders.total` = **R$ 28.704,99** · 48.998 linhas · 2020-01-01 01:19:28 → 2026-12-31 23:43:09 | Alta — cálculo direto |
| 3.2 | **251.864** linhas (2.000 + 48.998 + 147.320 + 53.546) | Alta — contagem direta |
| 4 | Líder cliente **22** (ticket R$ 41.839,94) · categoria campeã **Hélices** (492 itens) | Média — depende de filtro de status |
| 5 | Pior dia = **Quinta-feira** (R$ 157.154,32) | Alta — premissa é explícita |
| 6.2 | **116** unidades somando os dois ids da Bússola (76 se só o id 74) | Média — duplicidade + leitura da MM3 |
| 7.2 | **Motor de Popa 5331** (sem filtro) / *Vela Mestra 1913* (com `paid`) | **Baixa** — decidido na 4ª casa decimal |
| 2 | Script stdlib + `schema.sql` | — construção |

As duas de confiança menor (Q6.2 e Q7.2) recebem tratamento reforçado: cenário literal como resposta + tabela de sensibilidade na própria resposta dissertativa, transformando a ambiguidade do enunciado em demonstração de rigor.

---

## Decisões de arquitetura

Cada decisão vira um ADR versionado em `docs/adr/`. As sete que travam o resto:

### ADR-001 — PostgreSQL local no WSL como banco canônico ✅ *decidido*

**Você perguntou: local ou Supabase? Resposta: os dois, com papéis distintos.**

- **Trabalho/prova → PostgreSQL local no WSL** (`sudo apt install -y postgresql postgresql-contrib`, uma senha sua, ~2 min). Socket Unix local, `COPY` nativo para 433k linhas em segundos, zero dependência de rede numa prova de tentativa única. **Este é o primeiro passo da Onda 0** — vou te pedir para rodar o comando com `!`.
- **Portfólio → Supabase** publica só a camada **gold** (agregados, poucos MB) na Onda 6. Dashboard online sem arrastar 433k linhas pela rede.

Descartado usar o **PostgreSQL 18 já instalado no Windows**: o serviço está rodando e escutando em `0.0.0.0:5432`, mas o WSL está em modo NAT (`172.22.193.112`, gateway `172.22.192.1`) e o firewall do Windows bloqueia. Destravaria com uma regra de firewall em PowerShell **admin** mais provável ajuste de `pg_hba.conf` em `Program Files` (segundo elevação) e restart do serviço — dois passos privilegiados que eu não consigo diagnosticar bem de dentro do WSL. Fica como **plano B documentado**.

Descartado **DuckDB + dbt** (minha sugestão inicial, que você havia aceitado): as questões 2 e 3 exigem PostgreSQL de forma explícita, e Q1/Q4/Q5 precisam rodar no mesmo motor para coerência da entrega. dbt agregaria governança, mas as questões pedem **SQL puro e Python puro como arquivos avaliáveis** — dbt viraria uma camada que o corretor não pediu e que consome horas que não temos. A disciplina que o dbt traria (staging→marts, testes, docs) é preservada **na organização das pastas e nos testes SQL manuais**, sem a dependência.

### ADR-002 — Medalhão em três schemas no mesmo banco

| Schema | Conteúdo | Quem consome |
|---|---|---|
| `raw` | Os 24 CSVs carregados **sem nenhum tratamento**, tudo permissivo | Q2, Q3 — e **Q1, Q4, Q5**, que exigem dados brutos |
| `silver` | Tipagem forte, junk-nulls normalizados, `returns.reason` canonizado (32→6), EAV desempacotado, dedup por `tax_id` | Análises de apoio e Q6/Q7 |
| `gold` | Star schema (`dim_*` / `fato_*`) + agregados | Dashboard Power BI |

As respostas das questões saem de `raw` — é o que as premissas mandam. O dashboard sai de `gold`. Essa separação é, ela própria, o argumento da Q1.3.

### ADR-003 — Power BI via PBIP/TMDL gerado no WSL

Você já mantém PBIP em 5 projetos e tem o Desktop instalado. Eu gero do WSL o projeto inteiro em texto — modelo em **TMDL**, tema em **JSON**, dados **gold em Parquet** — e você abre no Desktop e salva o `.pbix`. Reduz seu trabalho manual de ~4h para ~40min.

O `.pbix` usa **Import mode com Parquet embutido**, nunca conexão ao Postgres: o avaliador precisa abrir o arquivo sem credencial nenhuma.

### ADR-004 — Postura "Literal + nota de senioridade" (sua escolha)

Toda questão entrega **a resposta que a premissa literal produz** (o número que um gabarito automático espera) e, logo abaixo, um bloco curto **"Leitura de engenharia"** com o cenário corrigido e o porquê. Exemplo Q1.2: a média de `total` é **R$ 28.704,99** — e essa média inclui 4.847 pedidos `cancelled` e 2.451 `draft`; filtrando `status='paid'` o número muda, e é isso que a diretoria deveria olhar.

### ADR-005 — Cada questão é um artefato autocontido e executável

O corretor faz upload de `.py` e `.sql` soltos. Então cada questão tem um arquivo único, rodável isoladamente, sem importar nada do pipeline. Duplicação controlada é aceita aqui de propósito — a alternativa (o corretor baixar o repo inteiro para rodar um script) é pior.

### ADR-006 — Idioma e formatação

Tudo em **pt-BR**: código comentado, docstrings, commits, documentação, dashboard. Números em padrão brasileiro na camada de apresentação (`R$ 28.704,99`), ponto decimal no código e no banco.

### ADR-007 — Repositório público desde o início (sua escolha)

Público como peça de portfólio, com histórico de commits limpo por onda.

---

## Arquitetura do repositório

```
desafio-lighthouse-2026/
├── README.md                      # vitrine: problema, arquitetura, resultados, como rodar
├── CLAUDE.md                      # ≤10k tokens, padrão MODELO-CLAUDE-MD.md
├── RETOMAR-AQUI.md                # estado + próximo passo (anti-perda de contexto)
├── Makefile                       # make setup | db | pipeline | questoes | check | gold
├── pyproject.toml                 # uv + hatchling, src layout
│
├── entregaveis/                   # ⭐ O QUE VAI PARA A PLATAFORMA
│   ├── Q1_eda/            q1_eda_orders.sql          + RESPOSTA.md
│   ├── Q2_schema/         q2_gerar_schema.py         + schema.sql + RESPOSTA.md
│   ├── Q3_carga/          q3_carregar_csvs.py        + relatorio_carga.md + RESPOSTA.md
│   ├── Q4_clientes/       q4_clientes_elite.sql      + RESPOSTA.md
│   ├── Q5_calendario/     q5_dim_calendario.sql      + RESPOSTA.md
│   ├── Q6_previsao/       q6_previsao_demanda.py     + RESPOSTA.md
│   ├── Q7_recomendacao/   q7_recomendacao.py         + RESPOSTA.md
│   └── FORMULARIO_PREENCHIDO.md   # rascunho literal de tudo que será colado
│
├── src/lh_nautical/               # pipeline (não é entregável, é a engenharia)
│   ├── perfilamento/  silver/  gold/  qualidade/  config.py
│
├── sql/
│   ├── raw/         # DDL gerado pela Q2
│   ├── silver/      # limpeza
│   ├── gold/        # dim_* / fato_*
│   └── testes/      # asserts de qualidade
│
├── powerbi/
│   ├── lh_nautical.pbip + .SemanticModel (TMDL) + .Report
│   ├── tema_lh_nautical.json
│   ├── medidas_dax.md
│   └── GUIA_MONTAGEM.md
│
├── dados/
│   ├── brutos/ -> ../1-lh_nautical_csv   (symlink, não versionar 36MB)
│   ├── gold/                              # Parquet para o Power BI
│   └── perfilamento/                      # relatórios de profiling
│
├── docs/
│   ├── PRD.md                     # requisitos e critérios de aceite
│   ├── SPEC.md                    # especificação técnica por questão
│   ├── PLANO_ONDAS.md             # este plano, versionado
│   ├── MAPA_QUESTOES.md           # Q → premissas → arquivo → resposta → status
│   ├── DICIONARIO_DADOS.md        # 24 tabelas, grão, PK/FK, semântica
│   ├── QUALIDADE_DADOS.md         # as 22 classes de sujeira, com evidência literal
│   ├── MODELO_DIMENSIONAL.md      # star schema + diagrama
│   ├── DECISOES_ANALITICAS.md     # cada ambiguidade do enunciado e a leitura adotada
│   ├── HISTORICO.md
│   └── adr/ADR-001..007.md
│
├── notebooks/  01_eda.ipynb  02_previsao.ipynb  03_recomendacao.ipynb
├── tests/
└── .claude/  agents/  skills/  settings.json  settings.local.json
```

---

## Arquitetura de uso do Claude (custo · qualidade · velocidade)

Você pediu explicitamente que o uso do Claude fosse planejado. Cinco mecanismos:

**1. `CLAUDE.md` com teto de 10k tokens** — seguindo seu próprio `~/.claude/MODELO-CLAUDE-MD.md`. Ele é reenviado a cada mensagem; inchá-lo é o maior desperdício recorrente. Detalhe vai para `docs/` com gatilho de uma linha.

**2. Memória persistente** — grava em `memory/` os fatos caros de redescobrir: números validados (48.998 / 251.864 / 28.704,99), as armadilhas (Bússola duplicada, 14 categorias, fan-out de payments), o modo de conexão do Postgres, e o estado da onda. Evita reler 36 MB de CSV a cada sessão.

**3. `RETOMAR-AQUI.md`** — estado + próximo passo. Retomada em ~2k tokens em vez de ~50k.

**4. Skills de projeto, copiadas e não globais** — só o necessário, em `.claude/skills/`:
`pandas-pro`, `plotly`, `python-best-practices` (de `~/.claude/skills-estacionadas/`) e `powerbi-report-design`, `semantic-model-authoring`, `pbip-tmdl-guardrails`, `dax-measure-reviewer` (de `POWERBI_DATAVIZ_WORLD_CHAMPS_BCN_2026`). Skill global custa ~1,7k tokens/sessão em todo projeto — por isso ficam locais.

**5. Roteamento de modelo por tipo de tarefa:**

| Tarefa | Modelo | Razão |
|---|---|---|
| SQL das Q1/Q4/Q5, decisões analíticas, textos dissertativos | **Opus** | Erro aqui é irrecuperável (tentativa única) |
| Loader, profiling, boilerplate, DDL, docs mecânicos | **Sonnet** | Volume alto, risco baixo |
| Revisão adversarial dos números antes do envio | **Opus** | Última linha de defesa |

**Agentes especializados** em `.claude/agents/` (padrão do seu `SCORECARD_ANS_ELINSA`):

| Agente | Escopo |
|---|---|
| `engenheiro-postgres` | schema, carga, tuning, testes SQL |
| `analista-sql` | Q1, Q4, Q5 — consultas e validação de grão |
| `cientista-dados` | Q6, Q7 — baseline, MAE, similaridade |
| `arquiteto-bi` | gold, TMDL, DAX, identidade visual |
| `revisor-qa` | verificação adversarial: confere número por número contra os CSVs |
| `redator-tecnico` | respostas dissertativas em pt-BR na voz pedida pelo Tech Lead |

**MCP:** você pediu para eu pesquisar skills e MCPs se fosse preciso. Inventariei a máquina e **não há lacuna que justifique buscar nada novo** — os 16 skills estacionados em `~/.claude/skills-estacionadas/` e os 20 de Power BI em `POWERBI_DATAVIZ_WORLD_CHAMPS_BCN_2026` cobrem todas as frentes deste projeto. O único MCP que pode entrar é o `powerbi-modeling-mcp` (`npx @microsoft/powerbi-modeling-mcp`, já usado em `PORTAL_INSIGHTSJOBSIA_PBI_EMBEDED`), e só se o TMDL escrito à mão der trabalho na Onda 5. Instalar MCP tem custo de tokens por sessão; não pago esse custo sem necessidade comprovada.

**Commit + push ao fim de cada onda** (você pediu), mensagens em pt-BR, `Co-Authored-By: Claude Opus 5`. Sem `gh` CLI na máquina — tudo por `git` sobre SSH, que já está autenticado como `Breno-Teodomiro`.

> ⚠️ `git config user.email` está como `insidhts.jobs.ia@gmail.com` (typo em "insights"). Corrijo no escopo do repositório na Onda 0 para os commits atribuírem ao seu perfil.

---

## Ondas e Sprints

Sprint = janela de calendário. Onda = incremento entregável. **Checkpoint = você revisa antes de eu seguir** (sua escolha).

### SPRINT 1 — Noite de 15/08 (~22h30 → 02h00)

**Onda 0 — Fundação** · ~50 min
Repo git + remoto + `.gitignore`; estrutura de pastas; `pyproject.toml` com uv (`psycopg[binary]`, `scikit-learn`, `matplotlib`, `pyarrow`); PostgreSQL instalado e validado; `CLAUDE.md`, `PRD.md`, `SPEC.md`, ADR-001..007; `.claude/` com agentes e skills; memória inicializada.
**Aceite:** `make setup` verde; `psql -c "select version()"` responde; primeiro push no ar.
🔒 **Checkpoint 0**

**Onda 1 — Q2 + Q3 (fundação de dados)** · ~2h30
Q2: gerador de schema em **stdlib pura** — inferência de tipo em duas passadas, proteção de zeros à esquerda, `nfe_access_key` (44 dígitos) como TEXT, fallback para `reorder_point` 100% vazia, PKs compostas nas 3 tabelas sem `id`.
Q3: loader com `COPY` via psycopg3, tratando os 7 arquivos CRLF, preservando string vazia vs NULL sem "tratar" nada, idempotente, com relatório de contagem por tabela.
**Aceite:** `schema.sql` cria as 24 tabelas sem erro; carga bate **251.864** em customers+orders+order_items+payments; nenhuma biblioteca externa no script da Q2.
🔒 **Checkpoint 1** → commit `feat(q2,q3): schema e carga`

### SPRINT 2 — Dia 16/08 manhã (~08h00 → 13h00)

**Onda 2 — Q1 (EDA)** · ~1h
SQL sobre `orders` cru; diagnóstico Q1.3 apoiado em evidência dura: outliers (`total` 32,62 → 127.262,02), 4.271 pedidos com data futura, colapso `placed_at == created_at == updated_at`, `salesperson_id` 49,2% nulo, mix de status.
**Aceite:** média confere **28.704,992077**; intervalo `2020-01-01 01:19:28` → `2026-12-31 23:43:09`.
🔒 **Checkpoint 2**

**Onda 3 — Q4 + Q5 (SQL analítico)** · ~2h30
Q4: CTEs separando ticket médio (só `orders`, sem tocar `payments` — evita fan-out 2:1) de diversidade (cadeia `order_items → product_variants → products.category_id`), filtro ≥13 de 14 categorias, desempate por `customer_id`, e a categoria campeã restrita aos 10.
> **Achado já validado:** o filtro de diversidade **não discrimina** — 1.971 dos 2.000 clientes (98,5%) compraram de ≥13 categorias, sendo 1.771 deles de todas as 14. Quem separa o ranking é exclusivamente o ticket médio. Isso entra na Q4.2 como crítica ao critério proposto, com a distribuição completa como evidência.
Q5: `generate_series` para a dimensão de datas, nomes de dia em português **sem depender de `lc_time`**, filtro `channel='pos'`, LEFT JOIN + COALESCE(0).

> **Prévia validada — a Q5 se prova sozinha.** Período `pos`: 2020-01-01 → 2026-12-31 (2.557 dias), dos quais **78 dias sem nenhuma venda**.
>
> | | Pior dia | Média |
> |---|---|---|
> | **Com** calendário completo (correto) | **Quinta-feira** | R$ 157.154,32 |
> | **Sem** calendário (erro do estagiário) | Segunda-feira | R$ 161.335,26 |
>
> **O diagnóstico troca de dia.** A quinta-feira tem 20 dias sem venda; ao ignorá-los, sua média sobe de R$ 157 mil para R$ 166 mil e ela deixa de ser a pior. Ou seja: seguindo o cálculo do estagiário, o Sr. Almir fecharia a loja **no dia errado**. Essa comparação lado a lado é a resposta da Q5.2 — com número, não com teoria.

**Aceite:** ticket médio recalculado independentemente em pandas bate com o SQL; total de dias do calendário confere com a diferença de datas (2.557).
🔒 **Checkpoint 3** → commit `feat(q1,q4,q5): análises SQL`

### SPRINT 3 — Dia 16/08 tarde (~13h00 → 18h00)

**Onda 4 — Q6 + Q7 (ciência de dados)** · ~2h30
Q6: resolver a duplicidade de "Bússola de Bordo 702" (ids **74** e **240**) — cenário principal + sensibilidade documentada; agregação mensal; média móvel de 3 meses sem vazamento; MAE contra Q1/2026; resposta inteira da Q6.2.
Q7: matriz binária cliente×produto em nível de **produto** (agregando variantes), cosseno produto×produto, top-5 excluindo o próprio "Motor de Popa 1949" (id 180).

> **Prévias já calculadas e os dois riscos que elas revelam:**
>
> **Q6 — a duplicidade é decisiva.** Vendas do trimestre de treino (out/nov/dez-2025): produto 74 = 26/36/14, produto 240 = 8/24/8. MM3 estática dá **76** unidades (só o 74), **40** (só o 240) ou **116** (somando ambos). O real do Q1/2026 é 156 / 51 / 207 — ou seja, **o baseline subestima em ~44% em qualquer cenário**, porque há tendência de alta que a média móvel não captura. Isso responde a Q6.5a ("o baseline não é adequado") com evidência numérica, não com opinião.
>
> **Q7 — a resposta muda com o filtro de status.** Sem filtro: **Motor de Popa 5331** (id 389, sim 0,2566). Com `status='paid'`: **Vela Mestra 1913** (id 75). O top-1 sem filtro vence o 2º lugar por **0,0003** — decidido na 4ª casa decimal, com a matriz a 13,6% de densidade. Como o enunciado da Q7 é explícito em tudo o mais (matriz binária, ignorar quantidade, excluir o próprio item) e **não menciona status**, o cenário literal sem filtro é o que o gabarito provavelmente espera → é a resposta principal, com a sensibilidade documentada logo abaixo. Mesmo raciocínio se aplica à Q4.
> Bônus para a Q7.3: com filtro `paid`, o produto de nome-lixo **`asdf`** (id 342) entra no top-5 — evidência concreta da limitação de recomendação por co-ocorrência sobre catálogo sujo.

**Aceite:** ambos rodam de ponta a ponta a partir dos CSVs; resultados reproduzidos por caminho independente (SQL vs pandas).
🔒 **Checkpoint 4** → commit `feat(q6,q7): previsão e recomendação`

**Onda 5 — Silver + Gold + Dashboard** · ~3h30
Silver: limpeza das 22 classes de sujeira. Gold: `dim_calendario`, `dim_cliente`, `dim_produto`, `dim_categoria`, `dim_local`, `fato_vendas`, `fato_devolucoes`, `fato_estoque` + Parquet.
Power BI: TMDL + tema + medidas DAX + 5 páginas — **Visão Executiva**, **Clientes de Elite (Q4)**, **Sazonalidade e Dia da Semana (Q5)**, **Previsão de Demanda (Q6)**, **Recomendação (Q7)**.
**Aceite:** você abre o `.pbip` no Desktop, atualiza e salva `.pbix` sem erro.
🔒 **Checkpoint 5** → commit `feat(bi): dashboard`

### SPRINT 4 — Noite de 16/08 (~18h00 → 23h00)

**Onda 6 — Empacotamento e revisão adversarial** · ~2h30
`FORMULARIO_PREENCHIDO.md` com o texto literal de cada campo; revisão adversarial dos 4 números avaliáveis (Q1.2, Q3.2, Q6.2, Q7.2) por caminho independente; export do dashboard em PDF; README de vitrine; `CHECKLIST_ENVIO.md`; publicação opcional do gold no Supabase.
**Aceite:** todo arquivo de upload existe e roda; nenhuma premissa violada (gate de conformidade por questão); checklist 100%.
🔒 **Checkpoint 6 — GO/NO-GO** → tag `v1.0-entrega`

**Reserva:** 16/08 23h → 17/08 07h como colchão. A entrega não deve depender dele.

---

## Mapa Questão → Entregável

| Q | Premissa crítica | Entregável | Resposta avaliável |
|---|---|---|---|
| 1 | Só `orders`, sem limpeza, **SQL** | `q1_eda_orders.sql` | 1.2: média de `total` = **28.704,99** |
| 2 | **Só stdlib** (pandas = desconsiderado), destino PostgreSQL | `q2_gerar_schema.py` + `schema.sql` | upload dos 2 arquivos |
| 3 | Todos os CSVs, **sem tratamento**, Python | `q3_carregar_csvs.py` | 3.2: **251.864** linhas |
| 4 | Ticket médio, **≥13 categorias** de 14, desempate por id | `q4_clientes_elite.sql` | Top 10 + categoria campeã (prévia: líder cliente **22**, categoria **Hélices**) |
| 5 | Só `pos`, calendário completo, dias sem venda = 0, dia em pt-BR | `q5_dim_calendario.sql` | pior dia = **Quinta-feira** (R$ 157.154,32) |
| 6 | Treino ≤31/12/2025, teste Q1/2026, MM3, "Bússola de Bordo 702" | `q6_previsao_demanda.py` | 6.2: soma prevista — **116** (ids 74+240) / 76 (só 74) / 40 (só 240) |
| 7 | Matriz binária, cosseno, top-5, "Motor de Popa 1949" | `q7_recomendacao.py` | 7.2: **Motor de Popa 5331** (literal, sem filtro) |
| 20 | **Dashboard obrigatório** em ferramenta de BI | `.pbix` + PDF + repo | material complementar |

Cada linha vira um **gate de conformidade** em `docs/MAPA_QUESTOES.md`: antes de marcar concluída, um agente confere que a premissa literal foi respeitada.

---

## Riscos e mitigação

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Instalação do Postgres pede senha e trava | Média | Alto | Você roda `! sudo apt install ...`. Plano B: firewall + PG18 do Windows. Plano C: Supabase |
| Q2 rejeitada por biblioteca externa | Baixa | **Fatal** | Gate automatizado: AST scan do script proibindo qualquer import fora da stdlib |
| Resposta numérica errada em prova de tentativa única | Média | **Fatal** | Todo número avaliável recalculado por dois caminhos independentes (SQL e pandas) |
| Ambiguidade da MM3 na Q6 muda a resposta | **Alta** | Médio | Entregar a leitura principal + as alternativas com MAE de cada, documentado |
| "Bússola de Bordo 702" duplicada (ids 74/240) | **Certa** | Alto | Já quantificado: 116 / 76 / 40. Cenário principal declarado + tabela de sensibilidade na própria resposta |
| **Q7.2 muda com filtro de status** (top-1 vence por 0,0003) | **Certa** | **Alto** | Já quantificado. Resposta literal sem filtro + sensibilidade explícita; o enunciado é omisso quanto a status, logo o literal é o defensável |
| PBIP não abre no Desktop | Média | Médio | Fallback: gold em Parquet/CSV + guia de montagem + dashboard HTML como complemento |
| Prazo estourar | Média | **Fatal** | MoSCoW: Q1–Q7 e dashboard são **Must**. Silver completa, Supabase, notebooks e HTML são **Could** — cortáveis sem dano |

---

## Verificação

**Por onda**
- Onda 0: `make setup` verde; `psql` conecta; push chega ao GitHub.
- Onda 1: `psql -f schema.sql` cria 24 tabelas sem erro; `SELECT SUM(n)` das 4 tabelas = **251.864**; `python -c "import ast"` prova zero import externo na Q2.
- Onda 2: média = **28.704,992077**; min/max de `created_at` conferem.
- Onda 3: Q4 e Q5 reproduzidas em pandas a partir dos CSVs, sem passar pelo banco.
- Onda 4: Q6 e Q7 rodam standalone; MAE calculado à mão numa planilha de conferência.
- Onda 5: `.pbip` abre, atualiza e salva `.pbix`; todo visual referencia uma medida existente.
- Onda 6: checklist de envio 100%; PDF gerado; tag criada.

**Comando único de conferência**
```bash
make check   # ruff + mypy + pytest + gate de conformidade das 7 questões
```

**Teste de ponta a ponta**
```bash
make db && make pipeline && make questoes
# recria o banco do zero, carrega os 24 CSVs e reexecuta as 7 questões,
# comparando cada número contra docs/MAPA_QUESTOES.md
```

**Revisão adversarial final (Onda 6):** um agente independente recebe só os CSVs e o enunciado, recalcula os 4 números avaliáveis sem ver minhas respostas, e o resultado é confrontado. Divergência = bloqueio de envio.
