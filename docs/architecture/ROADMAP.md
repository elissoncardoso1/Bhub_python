# Roadmap — BHUB Backend

**Este arquivo é um índice do trabalho que já está declarado — não é um plano novo.** Ele não
cria compromisso, prazo nem prioridade: tudo o que aparece abaixo já existe em algum artefato
do repositório (o plano vigente, a seção DEFERRED ou a seção KNOWN RISKS de
[`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md)). Se este índice divergir daqueles
documentos, eles estão certos.

- Arquitetura atual (referência única): [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md).
- Decisões estruturais: [`../adr/`](../adr/).
- Índice da documentação: [`../README.md`](../README.md).

---

## 1. Ciclo em curso — BHub v1.1 (Production Reliability)

O trabalho aberto deste ciclo vive em **um** arquivo:
[`docs/superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md`](../superpowers/plans/2026-09-15-bhub-v1.1-production-reliability.md)
(Tasks 1–19; Épicos 1–3 = ARQ/DI/CI, Épico 4 = testes de integração com infraestrutura real,
Épico 5 = sincronização da documentação arquitetural, Épico 6 = checklist de release).

- **Pendente:** Task 19 (Épico 6) — verificação de código do checklist de release v1.1, com
  saída em `docs/quality/RELEASE_CHECKLIST_v1.1.md`. Esse arquivo **não existe** em
  `docs/quality/` hoje (o diretório contém apenas `BASELINE.md`).
- O andamento por task, com evidência, fica em
  [`.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/`](../../.superpowers/sdd/2026-09-15-bhub-v1.1-production-reliability/)
  (`progress.md` + `task-N-report.md`).

**Não há outro ciclo aberto.** Os ciclos anteriores (migração Next.js → Python, refatoração
ARQ/DI/PostgreSQL, redesenho de UI/UX) estão encerrados e seus documentos estão marcados como
históricos — ver §4.

---

## 2. Adiado por decisão (DEFERRED)

Reconhecido, decidido adiar de propósito e registrado — cada um exige uma task própria. A
fonte é a seção **DEFERRED** de [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md#12-deferred):

| Item | O que falta |
|---|---|
| M5 (Task 11) | O CI faz build da imagem mas não executa o container para provar que ela é utilizável |
| Cenários 25, 29 e 31 do harness do ratchet | Casos de tabela inline do `tests/ci/ratchet_step_harness.sh` |
| `.dockerignore` | Não existe em `bhub-backend-python/`; o contexto de build inclui tudo |

---

## 3. Riscos conhecidos à espera de task própria

**Estão registrados, não corrigidos, e não estão agendados aqui.** A lista completa, com
medição e evidência `arquivo:linha`, é a seção **KNOWN RISKS** de
[`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md#13-known-risks):

- `R-01` — não existe outbox entre o `commit` do banco e o despacho do job.
- `R-02` — T16-F1: TOCTOU na deduplicação de PDF por hash (falha terminal sem retry).
- `R-03` — R-03/RED-3: `max_tries`/`retry_jobs` são configuração morta para os jobs do repo.
- `R-04` — RED-5: o startup do worker custa ~12 s e toca a rede.
- `R-05` — rate limiting do `POST /api/v1/ai/translate` não opera como pretendido.
- `R-06` — `get_or_create_category` é check-then-act.
- `R-07` — o ratchet de mypy tem um limite inerente no desenho por contagem.
- `R-08` — N1 (Task 13): a capacidade de falhar do teste de ordenação depende do plano do PG.
- `R-09` — `skipped` do pipeline de PDF é ambíguo.
- `R-10` — templates ainda anunciam SQLite como banco (é `app/`, copy de produção).
- `R-11` — o backup automático não cobre o PostgreSQL.
- `R-12` — o modo `semantic` da busca usa um motor que só existe em desenvolvimento.

---

## 4. Planos históricos — **não** são backlog aberto

Documentos de ciclos encerrados. Os checkboxes deles podem estar desmarcados mesmo com o
trabalho já feito: **nenhum item não marcado desses arquivos é trabalho pendente**. Índice
completo: seção **HISTORICAL** de [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md#14-historical).

- `BHUB_REFACTORING_PLAN.md` (raiz) — plano de refatoração; Fases 1–3 executadas.
- `bhub-backend-python/ARCHITECTURE_REPORT.md` — análise de 06/mai/2026.
- `docs/ESTADO_ATUAL_PROJETO.md` — análise de dez/2024.
- `docs/arquitetura/` — guias da migração Next.js → Python e stack recomendada daquela fase.

---

## 5. Como usar este arquivo (agentes de código)

1. **Não** trate checkbox desmarcado de documento histórico como tarefa aberta.
2. Antes de assumir que algo falta, confira o código (`app/`), as ADRs e
   [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md) — ele descreve o que existe, com
   `arquivo:linha`.
3. Trabalho novo entra pelo plano do ciclo (§1) ou por uma task própria derivada de §2/§3 —
   nunca por uma reescrita silenciosa de documento histórico.

---

**Última revisão deste índice:** Task 18 (Épico 5 / T5.4) — criado para que os arquivos de
contexto de agentes ([`AGENTS.md`](../../AGENTS.md), [`CLAUDE.md`](../../CLAUDE.md)) tenham
para onde apontar, já que a estrutura proposta pelo plano previa `docs/architecture/ROADMAP.md`
e o arquivo não existia.
