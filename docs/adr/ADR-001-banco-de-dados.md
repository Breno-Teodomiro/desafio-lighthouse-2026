# ADR-001 — PostgreSQL local no WSL como banco canônico

**Data:** 15/08/2026 · **Status:** aceito

## Contexto

As questões 2 e 3 do desafio exigem PostgreSQL de forma explícita: *"Considere o banco de destino como sendo um PostgreSQL"*. As questões 1, 4 e 5 pedem SQL e precisam rodar no mesmo motor para que a entrega seja coerente. É preciso decidir onde esse banco vive.

Restrições do ambiente, levantadas em 15/08:

- Docker indisponível — o binário do Windows está no PATH, mas a integração WSL do Docker Desktop está desligada.
- O host Windows tem **PostgreSQL 18 rodando**, escutando em `0.0.0.0:5432`. Porém o WSL está em modo NAT (`172.22.193.112`, gateway `172.22.192.1`) e o firewall do Windows recusa a conexão.
- Existe conta Supabase com MCP já configurado em outro projeto.
- O prazo é de ~30 horas e a prova é de tentativa única.

## Decisão

**PostgreSQL instalado nativamente no WSL via `apt` é o banco canônico** de trabalho.

**Supabase entra apenas na Onda 6**, publicando somente a camada `gold` (agregados, poucos MB), para viabilizar um dashboard online como peça de portfólio.

## Justificativa

O banco local roda no mesmo ambiente onde o código é executado: socket Unix, sem rede, sem firewall, `COPY` nativo carregando 433 mil linhas em segundos. Numa prova sem segunda chance, eliminar a rede do caminho crítico vale mais do que qualquer conveniência.

O PG 18 do Windows foi descartado como banco primário porque exigiria duas intervenções com privilégio de administrador — regra de firewall em PowerShell e provável ajuste de `pg_hba.conf` dentro de `Program Files`, com restart do serviço — e um diagnóstico difícil de conduzir de dentro do WSL caso algo falhasse.

O Supabase sozinho foi descartado como banco de trabalho: carregar 433 mil linhas por rede é lento, o free tier tem teto de 500 MB, e cada consulta analítica passaria a depender de latência externa.

## Consequências

- O usuário precisa rodar `sudo apt install -y postgresql postgresql-contrib` uma vez, informando a senha. É o único passo do projeto que exige intervenção manual dele além do Power BI.
- Passam a existir dois PostgreSQL na máquina (o 18 no Windows, o do WSL). A string de conexão do projeto sempre aponta para o do WSL, via `.env`.
- Se a instalação falhar, o plano B é liberar o PG 18 no firewall; o plano C é o Supabase.
