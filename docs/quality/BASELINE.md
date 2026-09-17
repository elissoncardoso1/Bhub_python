# Baseline de qualidade — BHUB Backend (Python 3.12)

> Épico 3, Tasks T3.1 (medir) + T3.2 (zerar dívida de Ruff) + T3.3/T3.4
> (mypy bloqueante e piso de cobertura no CI — ver §6).
> Escopo desta medição: `bhub-backend-python/` (a aplicação vive nesse subdiretório).
> Todos os comandos abaixo foram executados a partir de `bhub-backend-python/`,
> com o venv do projeto (`.venv/bin/python -m <ferramenta>`).

HEAD de referência do baseline: `c9d578a` (`docs(di): document global singleton decisions`),
árvore limpa, sem alterações pendentes. A atualização da Task 10 (§6) foi medida sobre
`141302d` (Task 9 revisada e limpa) mais o diff da própria Task 10.

## 1. Baseline → depois (T3.1)

| Verificação | Comando exato | Baseline (`c9d578a`) | Depois (T3.2) |
|---|---|---|---|
| Lint | `ruff check app tests` | **178 erros** | **0 erros** (`All checks passed!`) |
| Formatter | `ruff format --check .` | **99 seriam reformatados**, 82 já formatados | **0 pendentes** (179 já formatados) |
| Tipagem | `mypy app` | **369 erros em 61 arquivos** (105 arquivos analisados) | **rc=0** na Task 10 / T3.3 — via ratchet de strict por módulo + 28 arquivos com `ignore_errors` enumerado: **é um gate PARCIAL** (§6.6); desde a rodada de correção 2 há o shadow ratchet por contagem (§6.8) cobrindo os 28 |
| Testes | `pytest tests/ -q` | **256 passed**, 0 failed | **256 passed**, 0 failed |
| Cobertura | `pytest tests/ -q --cov=app --cov-report=term-missing` | **59%** (6359 statements, 2609 missing) | **59%** (6338 statements, 2586 missing) — com piso bloqueante `--cov-precision=2 --cov-fail-under=59.19` (piso efetivo ≥ 3752 statements cobertos, ≈ 59,19%; o valor cru é 59,1985%) desde a Task 10 / T3.4 (§6.4) |

Notas de leitura:

- O baseline de lint/format/testes/cobertura foi medido pelo controller sobre o HEAD
  limpo (`c9d578a`), usando `git stash` para isolar o diff parcial do implementador
  interrompido.
- A cobertura **não regrediu** (59% → 59%) e as **duas medições** dos statements estão na
  tabela acima — **fato verificado** (o HEAD atual mede `TOTAL 6338 2586 59.2%`, §6.4).
  Menos statements com a mesma porcentagem = menos linhas descobertas em termos absolutos
  (2609 → 2586) — **fato verificado**, decorre das duas linhas da tabela.
- **A CAUSA** da queda de 6359 para 6338 statements é **inferência, não medida** (rotulada
  na rodada de correção 3). Atribuí-la às refatorações do Ruff (fusão de `if` aninhados,
  remoção de código morto) é plausível — a Task 9 é de lint/format e não registra mudança
  de comportamento —, mas ninguém isolou os statements removidos nem re-mediu o estado
  intermediário. O exemplo específico que esta nota citava
  (`app/services/article_parser.py`) foi **removido por não ter evidência no repositório
  que o sustentasse**. **Hipótese** não descartada: parte da diferença pode vir da mudança
  de versão das ferramentas de medição entre os dois momentos, não do código.
- **Reconciliação do drift de 1 statement (rodada de correção 2; rotulada na rodada de
  correção 3).** Esta coluna trazia `6339 statements` enquanto o §6.4 e o `ci.yml` traziam
  `6338`. **Fato verificado pelo histórico do git:** o commit `141302d` (rodada de correção
  da Task 9) fundiu os dois imports de `event` de `app/database.py` em uma única statement —
  `from sqlalchemy import event  # noqa: E402` saiu do meio do arquivo e a linha virou
  `from sqlalchemy import event, text` no topo (−1 statement):

  ```console
  $ git show 141302d^:bhub-backend-python/app/database.py | grep -n "sqlalchemy import"
  8:from sqlalchemy import text
  49:from sqlalchemy import event  # noqa: E402
  $ git show 141302d:bhub-backend-python/app/database.py | grep -n "sqlalchemy import"
  8:from sqlalchemy import event, text
  ```

  **Inferência consistente com a aritmética, NÃO re-medida:** que o `6339` fosse exatamente
  a medição de ANTES de `141302d` e que os cobertos caíssem de 3753 para 3752 com o mesmo
  `missing` 2586. A aritmética fecha (−1 statement, como no diff acima), mas **a suíte não
  foi rodada no commit anterior a `141302d`** para re-medir os 6339 — o re-reviewer declarou
  esse limite e ninguém o refutou desde então. O que está **medido neste HEAD**
  (`coverage 7.16.1`) é `TOTAL 6338 2586 59.2%`, e é esse o número que as colunas usam.
- `mypy` continua intencionalmente fora do escopo: os 369 erros são a dívida tratada na
  Task 10 (T3.3, "mypy strict check"). Nenhum `continue-on-error` de mypy foi alterado aqui.
- Sobre o formatter: os números de baseline **99 reformatados + 82 já formatados = 181**
  contavam com dois scripts auxiliares não rastreados (`fix_arg.py`, `fix_manual.py`) que
  foram **apagados** nesta task. Por isso o estado final medido é **179 já formatados**
  (181 − 2), e não 181. A versão anterior deste documento registrava 181 no estado "depois"
  — era um número medido antes da remoção dos scripts; corrigido na rodada de correção 1.

### Amplitude do `ruff check`

O escopo medido e cobrado no CI é `app tests` — os dois diretórios onde o plano V1.1 aplicou
dívida de lint. Estado atual, para registro honesto:

| Comando | Resultado atual |
|---|---|
| `ruff check app tests` | 0 erros |
| `ruff check .` | 113 erros, **todos** em `scripts/` e `alembic/` (nenhum em `app/` ou `tests/`) |

Os 113 erros restantes fora de `app tests` são dívida pré-existente (códigos: `UP007` 27,
`I001` 27, `E402` 21, `F401` 16, `UP035` 9, `F541` 8, `W291` 3, `E712` 1, `ARG001` 1) e
**não** foram zerados nesta task: `alembic/versions/*` são migrações já aplicadas que não
se deve reescrever para satisfazer lint, e `scripts/` são utilitários operacionais fora do
caminho do CI atual. Ficaram, porém, **reformatados** por `ruff format .`, de modo que
`ruff format --check .` passa no repositório inteiro. Isso está registrado aqui como lacuna
conhecida, não como sucesso.

## 2. Como o débito foi zerado (T3.2)

1. **Correção de sítios reais em `app/`** — sem `# noqa` em massa:
   - `import contextlib` adicionado em `app/core/analytics_middleware.py` (correção de
     `F821`, regressão de runtime que quebrava a suíte);
   - `I001` corrigido por `ruff check --fix`;
   - `SIM102` (2 sítios) resolvidos fundindo os `if` aninhados em `app/services/article_parser.py`;
   - `ARG001` de `app/web/translation.py` resolvido renomeando `current_user` → `_current_user`
     (o FastAPI resolve a dependência pela **anotação**, não pelo nome, então a renomeação é segura).
2. **Formatter aplicado em todo o repositório** (`ruff format .`): 99 arquivos reformatados,
   82 inalterados.
3. **`per-file-ignores` justificado** em `pyproject.toml` para `tests/**` (ver seção 3).
4. **`# noqa` cirúrgico** apenas onde o nome do parâmetro é contrato externo (ver seção 4).
   Na **rodada de correção 1**, foram removidas as 27 linhas de `# noqa` que estavam em
   parâmetros **já `_`-prefixados** — o Ruff ignora esses nomes por padrão
   (`dummy-variable-rgx`, cujo default é `^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$`
   no Ruff 0.16.7, e não `^_` como este documento afirmava; a regex real foi lida do
   próprio binário do pin com `ruff check --show-settings` na Task 10),
   então essas linhas não suprimiam nada; e o parâmetro morto
   de `_get_font_path` foi apagado. Inventário completo em §4.

## 3. `per-file-ignores` adicionados (`pyproject.toml`)

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ARG001", "ARG002", "ARG005"]
```

**Justificativa:** em `tests/`, argumentos não usados não são dívida — são obrigações de
assinatura:

- parâmetros de **fixture do pytest** são resolvidos **por nome**. Renomear `client` para
  `_client` **quebra** a injeção da fixture, e removê-los quebraria testes que dependem do
  efeito colateral da fixture;
- fakes e dublês precisam manter a **aridade da assinatura real** que substituem
  (por exemplo `FakeDB.execute(self, stmt)` e `lambda *args, **kwargs` que fazem o papel de
  `get_or_create_session(*, db, session_id, ...)`).

Espalhar dezenas de `# noqa` por arquivos de teste seria ruído sem ganho de qualidade; o
`per-file-ignores` documenta a decisão uma única vez. **Este é o único `per-file-ignores`
do projeto.** `ARG004` foi **removido** desta lista na rodada de correção 1. A justificativa
registrada então — "não há nenhuma ocorrência dele em `tests/`" — estava **errada**, e foi
**corrigida na Task 10**: existem **3** ocorrências em `tests/`
(`tests/unit/test_arq_job_observability.py:323,329,472`, todas no parâmetro `db` de
`process_article_pdf`), **cada uma já coberta por um `# noqa: ARG004` local**. Remover
`ARG004` do `per-file-ignores` portanto não expõe erro nenhum (o `ruff check app tests` = 0
confirma), mas o motivo real de removê-lo não é "ocorrência zero": é que nesses 3 sítios o
`# noqa` local é onde a decisão fica visível, e o `db` existe para espelhar a assinatura
real do job do arq. `ARG004` continua sendo reportado de verdade em `app/` (2 sítios, com
`# noqa` justificado — ver §4.1).

## 4. Inventário completo de `# noqa` (reescrito na rodada de correção 1)

O inventário original desta seção estava **incompleto e errado**: listava 9 sítios e
afirmava "Nenhum outro `# noqa` foi introduzido", quando o diff continha **42** linhas
`# noqa` adicionadas em `app/`. Das 42, **27 eram inócuas** (parâmetros já prefixados com
`_`, que o Ruff ignora por padrão via `dummy-variable-rgx`;
a regex default do Ruff 0.16.7 é `^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$`, não `^_` —
corrigido na Task 10), 1 mascarava um parâmetro
morto e 2 foram eliminadas movendo imports. Todo o inventário abaixo foi recontado com
`grep -rn noqa` no HEAD desta rodada e validado com o `ruff 0.16.7` (a versão do pin).

### 4.1 `# noqa` introduzidos por esta task e ainda presentes em `app/` — **12 linhas**

Cada um cobre um argumento cujo **nome faz parte de um contrato** e que, portanto, não pode
virar `_nome` (ou um import deliberadamente tardio):

| Arquivo:linha | Código | Justificativa |
|---|---|---|
| `app/ai/manager.py:286,373,449` | `ARG002` ×3 | `target_lang` é contrato de tradução em dois lugares: no Protocol `IAIManager.translate(self, text: str, target_lang: str = "pt")` (`app/interfaces/services.py:61-67`) e no método abstrato `BaseAIService.translate(self, text: str, target_lang: str = "pt") -> str` (`app/ai/manager.py:148,158`). É chamável por keyword, e os 3 sítios são justamente os **overrides** de `DeepSeekService` (`:286`), `OpenRouterService` (`:373`) e `HuggingFaceService` (`:449`); a assinatura é contrato entre providers. **Correção da Task 10:** a rodada de correção 1 citava aqui a classe `BaseAIProvider`, que **não existe** no repositório (`grep -rn BaseAIProvider app tests` = 0 ocorrências). |
| `app/api/v1/ai.py:63` | `ARG001` | `request` é exigido pelo **slowapi** por nome literal (`slowapi/extension.py`: procura um parâmetro chamado `request`); aqui ele é um `starlette.requests.Request` de verdade e é lido pelo wrapper do limiter. |
| `app/api/v1/articles.py:28` | `ARG001` | idem: `request` exigido pelo slowapi por nome literal. |
| `app/core/security.py:51` | `ARG002` | `token` é imposto pela assinatura de `BaseUserManager.on_after_forgot_password` do fastapi-users (método sobrescrito). |
| `app/services/analytics_service.py:85` | `ARG004` | `ip_address` é passado **por keyword** pelos chamadores (`app/core/analytics_middleware.py:171,184`, `app/api/v1/analytics.py:56,69,107,121`, `app/services/analytics_service.py:53`). |
| `app/services/classification_service.py:108` | `ARG004` | `auto_created` é documentado na docstring e chamado por keyword (`classification_service.py:225`: `db, slug, auto_created=True`). |
| `app/services/classification_service.py:153` | `ARG004` | `db` é documentado na docstring e chamado **por keyword** em `app/services/background_tasks.py:47-52` (`db=db,`) e em `tests/test_services_minimal.py:25-26` (`db=None,`). **Correção da Task 10:** a rodada de correção 1 citava `classification_service.py:73` e `background_tasks.py:48,78`, que são chamadas de OUTRO método — `assign_categories_to_article` (`classification_service.py:72-77` e `background_tasks.py:77-82`), não de `classify_with_multiple_categories` (`classification_service.py:150-153`). |
| `app/services/opengraph_service.py:65` | `ARG002` | `bold` é passado por keyword internamente (`_load_font(48, bold=True)` em `:167`, `_load_font(64, bold=True)` em `:371`). |
| `app/main.py:142` | `E402` | import tardio proposital do `CSRFMiddleware`, junto do ponto em que ele é instalado; comentário de justificativa na linha acima. |
| `app/main.py:325` | `E402` | import tardio proposital de `app.web.router`, junto do bloco que monta rotas/estáticos; comentário de justificativa na linha acima. |

Removidos nesta rodada: **27** linhas em parâmetros `_`-prefixados
(`app/api/v1/admin/{feeds,stats,articles,analytics}.py` — 23× `_admin`;
`app/api/v1/opengraph.py` — 2× `_db`; `app/api/v1/ai.py` — `_http_request`;
`app/api/v1/contact.py` — `_csrf_valid`), **1** em `app/services/opengraph_service.py`
(parâmetro morto `font_name`, que foi apagado) e **2** em `app/database.py` /
`app/web/router.py` (imports movidos para o topo). Prova de que eram inócuas: com as 27
linhas apagadas, `ruff check app tests` continua `All checks passed!` (rc=0) com o ruff
0.16.7 do pin — nenhuma supressão foi perdida.

### 4.2 `# noqa` **pré-existentes** em `app/` (não introduzidos por esta task) — 5 linhas

| Arquivo:linha | Código | Nota |
|---|---|---|
| `app/models/article.py:181,182,183,184` | `E402, F811` | imports no fim do módulo para `model_rebuild()` dos relacionamentos; já existiam em `c9d578a` (não aparecem no diff desta task). |
| `app/models/pdf_metadata.py:75` | `E402, F811` | idem. |

### 4.3 `tests/`

**25** linhas `# noqa` em `tests/` em `c9d578a` e **25** no HEAD — **nenhuma adicionada**,
nenhuma removida. A decisão para `tests/` foi `per-file-ignores` (§3), não `# noqa`
espalhado.

## 5. CI

`.github/workflows/ci.yml` deixou de ter lint informativo: o `continue-on-error: true` foi
removido na Task 9; na Task 10 entraram os dois gates do Épico 3 que faltavam e na Task 11 o
build da imagem. Hoje são
**sete steps bloqueantes** em `bhub-backend-python` (`defaults.run.working-directory`),
mais o de testes — **nenhum** deles usa `continue-on-error`:

```yaml
- name: Lint (ruff check)
  run: ruff check app tests

- name: Format check (ruff format --check)
  run: ruff format --check .

- name: Type check (mypy app)             # Task 10 / T3.3 — gate PARCIAL (§6.6)
  run: mypy app

- name: Type check ratchet (mypy shadow, budget 127)   # rodadas de correção 2, 3, 4 e 5 / §6.8
  run: |
    RATCHET_BUDGET=127
    EXPECTED_SOURCE_FILES=105
    RATCHET_CONFIG=pyproject.ratchet.toml
    rc=0
    mypy app --config-file "$RATCHET_CONFIG" > /tmp/mypy-ratchet.txt 2>&1 || rc=$?
    cat /tmp/mypy-ratchet.txt
    if [ "$rc" -gt 1 ]; then exit 1; fi
    # FAIL CLOSED #0 — guard da config do ratchet: `ignore_errors` ATIVO (valor
    # `true`, com a chave citada com " ou ' ou não, em linha própria ou tabela
    # inline) → ::error:: + exit 1.
    # FAIL CLOSED #1 — operandos validados por FORMA e MAGNITUDE (`^[0-9]{1,9}$`)
    # antes de qualquer comparação; #2 = parsing da última linha de resumo;
    # #3 = escopo (`checked == 105`) e teto (`total <= 127`).
    # (Transcrição abreviada: o corpo real, comentado linha a linha, está em
    # ci.yml; os cenários congelados, no harness abaixo e no §6.8.)

- name: Run ratchet step harness          # autoteste do step acima (rodada de correção 4)
  run: bash tests/ci/ratchet_step_harness.sh

- name: Run tests
  run: pytest tests/ -v

- name: Coverage floor (fail under 59.19%, precision 2, >= 3752 statements)  # Task 10 / T3.4
  run: |
    pytest tests/ \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-precision=2 \
      --cov-fail-under=59.19

- name: Build da imagem Docker (Dockerfile do deploy)   # Task 11 / T3.5
  run: docker build -f Dockerfile .
```

**O step de build da imagem (Task 11 / T3.5).** Bloqueante, sem `continue-on-error`, rodando
no fim — a ordem do job é barato→caro, e é ele o passo caro. O que ele constrói não é
escolha livre: o **caminho real de deploy** é `docker-compose.prod.yml` do próprio
`bhub-backend-python/` (o único com Traefik + Postgres + Redis + `arq-worker`, mantido em
`chore(deploy)`), e ele aponta para `Dockerfile` (não `Dockerfile.prod`). A cadeia:
`upload-to-vps.sh` sobe `bhub-backend-python/` para `/var/www/bhub/backend/`;
`docs/deploy/VPS_DEPLOY.md` manda rodar `bash scripts/vps/deploy.sh` **de dentro** desse
diretório; e `bhub-backend-python/scripts/vps/deploy.sh` executa
`docker-compose -f docker-compose.prod.yml up -d --build` ali. O `Dockerfile.prod` só é
referenciado pelo `docker-compose.prod.yml` da RAIZ, que monta o stack com um `./Frontend`
que não existe neste repositório — não é caminho de deploy desta app e por isso **não** é
construído no CI. O contexto é a raiz de `bhub-backend-python/` (o working-directory do job),
que é exatamente o contexto que aquele compose usa. Consumo do build: rede (apt Debian,
PyPI, índice CPU do PyTorch e download do modelo do `sentence-transformers` no
HuggingFace) — **nenhum segredo**, nenhum `--build-arg`; por isso ele é reproduzível no
runner, ao custo de minutos. Não há `.dockerignore` em `bhub-backend-python/`, então o
`COPY . .` do `Dockerfile` carrega o que estiver na árvore de trabalho (no CI, os caches de
ruff/mypy/pytest e o `coverage.xml`; numa máquina de dev, o `.venv`) — follow-up nomeado,
não feito aqui.

**Rótulo dos critérios de aceite do CI** (aplicado nesta rodada de correção 2 no ledger do
plano e no brief da task, porque a redação antiga prometia mais do que o gate entrega):

| Critério | Como ele realmente vale |
|---|---|
| "Mypy bloqueia PR" / "`mypy app` passa" (Task 19) | **Sob o gate PARCIAL do §6.6**: 28 de 105 arquivos ficam fora de verificação (`ignore_errors`). Erro novo nos 44 em strict pleno e nos 33 relaxados falha o CI; erro novo nos 28 é pego pelo shadow ratchet do §6.8, não pelo step `mypy app`. Ratchet pós-release (corrigir os 127 legados) segue pendente. |
| "Coverage não pode cair abaixo do baseline" | Piso `--cov-precision=2 --cov-fail-under=59.19` ⇒ piso **efetivo 3752 statements cobertos** (59,1985% → 59,20 ≥ 59,19): qualquer perda de statement coberto falha. Antes da rodada de correção 2, `--cov-fail-under=59` com precisão 0 tolerava até 3708 (58,50%) — 44 statements de folga; a rodada 2 usou `--cov-precision=1 --cov-fail-under=59.2` (efetivo 3749). |

(O step `Run tests` — `pytest tests/ -v` — continua no lugar, logo depois do step do harness e
antes do de cobertura. A suíte roda duas vezes de propósito: ~10 s, e assim uma regressão de
cobertura aparece como falha do próprio step, não escondida no step de testes. O step
`Run ratchet step harness` entrou na rodada de correção 4, entre o ratchet e o de testes: sem
ele o harness só rodava à mão, e um artefato de verificação que ninguém executa apodrece.)

`requirements-dev.txt` fixa `ruff==0.16.7`, a versão em que o repositório foi validado: um
`ruff format --check` bloqueante só é determinístico se a versão do formatter for fixa.
Na rodada de correção 1, o extra `dev` de `pyproject.toml` foi **alinhado ao mesmo pin**
(`ruff==0.16.7`, antes `ruff>=0.8.0`), eliminando a segunda fonte de verdade: antes,
`pip install -e ".[dev]"` podia instalar uma versão diferente da validada. Na Task 10 o
mesmo tratamento foi dado ao `mypy` (§6.7).

### Entrou no escopo nesta rodada

- Build da imagem Docker no CI → **Task 11 (T3.5)**: step
  `Build da imagem Docker (Dockerfile do deploy)`, bloqueante, com o `Dockerfile` do caminho
  real de deploy (não o `Dockerfile.prod`) — evidência no parágrafo acima.

> `mypy` bloqueante (T3.3) e piso de cobertura (T3.4) **entraram** no CI na Task 10 — ver §6.

## 6. Task 10 (T3.3 + T3.4): mypy bloqueante e piso de cobertura

Medições feitas a partir de `bhub-backend-python/`, com o venv do projeto
(`.venv/bin/python -m <ferramenta>`), sobre a BASE `141302d` + o diff desta task.
`mypy 2.3.1` — o pin novo, ver §6.7.

### 6.1 Números do mypy

| Config | Resultado |
|---|---|
| `mypy app` com a config de BASE (`strict = true`, sem overrides) | **369 erros em 61 dos 105 arquivos** — rc=1 |
| `mypy app` a strictness **default** (config temporária fora do repo, repo intocado) | **126 erros em 28 arquivos** — rc=1 |
| `mypy app` com a config final desta task | **`Success: no issues found in 105 source files`** — **rc=0** |
| `mypy app --config-file pyproject.ratchet.toml` (config final **sem** o bloco `ignore_errors`; §6.8) | **127 erros em 28 arquivos** — rc=1 (**este é o orçamento do shadow ratchet**) |

Composição dos 369 (config de BASE): `no-untyped-def` 132, `type-arg` 51,
`no-any-return` 35, `assignment` 30, `union-attr` 30, `attr-defined` 26,
`no-untyped-call` 23, `arg-type` 12, `call-overload` 6, `index` 6, `var-annotated` 4,
`type-var` 3, `return-value` 3, `list-item` 2, `operator` 2, `misc` 2, `exit-return` 1,
`prop-decorator` 1.

Dos 369, **241 são ruído de anotação** (`no-untyped-def` 132 + `type-arg` 51 +
`no-any-return` 35 + `no-untyped-call` 23): são a ausência de anotação do código legado, não
erro de tipo, e desaparecem quando a strictness é relaxada. Os outros **126 são erros reais
de tipo**, em 28 arquivos (strictness default): `assignment` 30, `union-attr` 30,
`attr-defined` 25, `arg-type` 12, `call-overload` 6, `index` 6, `var-annotated` 4,
`type-var` 3, `return-value` 3, `list-item` 2, `misc` 2, `exit-return` 1, `prop-decorator` 1,
`operator` 1.

> Divergência de contagem registrada, não escondida: o controller anotou
> `annotation-unchecked` 2 na cauda longa; a medição desta rodada, com o `mypy 2.3.1` do pin,
> dá `list-item` 2 e **nenhum** `annotation-unchecked` como erro (ele aparece apenas como
> *note* informativo em `app/ai/manager.py:35`, sem afetar o rc). O total confere: **126
> erros em 28 arquivos**.

### 6.2 Estratégia aplicada (e por que o gate é parcial)

`strict = true` continua sendo o **default global** em `pyproject.toml` — não foi
desativado. O ajuste é por módulo, visível um a um em `[[tool.mypy.overrides]]`:

1. **56 módulos legados** (dos 105 de `app/`) relaxam os checks que `strict = true` liga e
   que **não** são default do mypy — 12 flags: `disallow_untyped_defs`,
   `disallow_incomplete_defs`, `disallow_untyped_calls`, `disallow_any_generics`,
   `disallow_subclassing_any`, `check_untyped_defs`, `disallow_untyped_decorators`,
   `warn_unused_ignores`, `warn_return_any`, `no_implicit_reexport`, `strict_equality`,
   `extra_checks`. É isso que elimina os 241 erros de ruído de anotação.
   `no_implicit_optional` **não** é desligado: é default do mypy desde 0.990 e pega bug real
   (Optional implícito em parâmetro), não ruído de anotação. (`warn_redundant_casts` não é
   flag por módulo no mypy e por isso não aparece na lista.)
2. **28 módulos** ficam com `ignore_errors = true` (§6.3) — são os que ainda têm os erros
   reais de tipo, listados **individualmente com a contagem ao lado**. Nada de glob
   (`app/**`, `app/services/*`) aqui: o ratchet tem de ser visível arquivo a arquivo.
3. Os 126 erros **não foram corrigidos** nesta task: T3.3 é uma task de CI, não de tipagem
   do codebase. Não foi usado `# type: ignore`, não foi usado `cast()`, e nenhuma lógica de
   produção foi alterada para agradar o mypy. A correção dos 126 erros é a task nova de
   ratchet pós-release já registrada no ledger pelo controller.

Com o bloco 1 ativo e o bloco 2 ausente, o `mypy` acusa **127 erros nos mesmos 28 arquivos**
(medido: `Found 127 errors in 28 files`). A diferença de 1 em relação aos 126 default é um
diagnóstico de reexport implícito vindo de **dependência de terceiro**:
`app/ai/model_manager.py:9` importa `HfHubHTTPError` de `huggingface_hub.utils`, que não o
reexporta explicitamente (`attr-defined`). Ele só aparece porque o `strict` global também
vale para os módulos de terceiros que o mypy analisa — comportamento que já valia na config
de BASE. Por isso a contagem de `model_manager` é **11**, e não 10.

### 6.3 Os 28 arquivos com `ignore_errors` (enumerados, um a um)

Contagens medidas com o bloco de relaxamento ativo e o `ignore_errors` **comentado** (o
"default: N" marca o único arquivo cuja contagem difere da medição a strictness default
pura):

| Arquivo | Erros suprimidos |
|---|---|
| `app/services/web_scraper.py` | 36 |
| `app/web/routes.py` | 18 |
| `app/ai/model_manager.py` | 11 (default: 10) |
| `app/ml/embedding_classifier.py` | 8 |
| `app/services/opengraph_service.py` | 7 |
| `app/api/v1/admin/articles.py` | 6 |
| `app/services/pdf_service.py` | 5 |
| `app/ai/local_llm_service.py` | 4 |
| `app/ml/__init__.py` | 4 |
| `app/services/article_parser.py` | 4 |
| `app/web/admin.py` | 3 |
| `app/api/v1/ai.py` | 2 |
| `app/api/v1/search.py` | 2 |
| `app/core/cookie_transport.py` | 2 |
| `app/services/analytics_service.py` | 2 |
| `app/api/v1/admin/feeds.py` | 1 |
| `app/api/v1/articles.py` | 1 |
| `app/config.py` | 1 |
| `app/core/ip_anonymization.py` | 1 |
| `app/core/log_sanitizer.py` | 1 |
| `app/core/rate_limiting.py` | 1 |
| `app/core/refresh_token.py` | 1 |
| `app/core/scheduler_lock.py` | 1 |
| `app/jobs/observe.py` | 1 |
| `app/jobs/tasks.py` | 1 |
| `app/main.py` | 1 |
| `app/services/feed_aggregator.py` | 1 |
| `app/services/translation_cache_service.py` | 1 |
| **Total** | **127** (126 a strictness default pura) |

### 6.4 Threshold de cobertura (T3.4)

```bash
pytest tests/ -q --cov=app --cov-report=term-missing --cov-report=xml \
  --cov-precision=2 --cov-fail-under=59.19
```

| Medida | Valor |
|---|---|
| Cobertura do baseline | **59,2%** (3752/6338 statements; 2586 linhas não cobertas) — valor cru **59,1985%** |
| Piso do CI | `--cov-precision=2 --cov-fail-under=59.19` |
| Piso **efetivo** | **3752 statements cobertos** (= 59,1985% → 59,20 ≥ 59,19). Qualquer perda de statement coberto no baseline (3751 → 59,1827% → 59,18) **falha**: é o critério escrito como "nenhum statement coberto pode ser perdido" |
| Testes | **256 passed**, 0 failed |

**Precisão do piso (corrigida na rodada de correção 2, endurecida na rodada 3).** O
`coverage 7.16.1` decide por `round(total, precision) < fail_under`
(`coverage/results.py:503`), e `precision` tem default **0**: o antigo
`--cov-fail-under=59` só reprovava abaixo de **58,5%** — uma queda de até 44 statements
(−0,70 p.p.) passava verde, inclusive um valor **abaixo** do baseline medido. A rodada de
correção 2 trocou a precisão para 1 (`59.2`), o que deixou o piso efetivo em 3749; a rodada
3 adotou `--cov-precision=2 --cov-fail-under=59.19`, que aperta o piso efetivo para **3752**
(zero folga sobre o baseline) e elimina uma mensagem enganosa (§ nota abaixo).

Aritmética do piso, com o total real de 6338 statements
(`round(covered/6338*100, 2) ≥ 59.19`):

| Cobertos | % cru | round(·,2) | passa? |
|---|---|---|---|
| 3749 | 59,1512% | 59,15 | não |
| 3750 | 59,1669% | 59,17 | não |
| 3751 | 59,1827% | 59,18 | não |
| **3752** | **59,1985%** | **59,20** | **sim** (o baseline) |

Evidências locais do piso mordendo (**execuções reais**, `.venv/bin/python -m pytest
tests/ -q --cov=app <flags>`, saída colada verbatim):

| Comando | rc | Saída |
|---|---|---|
| `--cov-precision=2 --cov-fail-under=59.19` (o do CI) | **0** | `TOTAL 6338 2586 59.20%` + `Required test coverage of 59.19% reached. Total coverage: 59.20%` |
| `--cov-precision=1 --cov-fail-under=59.2` (o da rodada 2) | 0 | `TOTAL 6338 2586 59.2%` + `FAIL Required test coverage of 59.2% not reached. Total coverage: 59.20%` ← rc verde com a palavra FAIL no log (a nota abaixo) |
| `--cov-precision=0 --cov-fail-under=59.2` | 1 | `ERROR: Coverage failure: total of 59 is less than fail-under=59` |
| `--cov-precision=1 --cov-fail-under=59.25` | 1 | `ERROR: Coverage failure: total of 59.2 is less than fail-under=59.2` (a mensagem formata o `fail-under` com a precisão do gate: 59,25 → 59,2) |
| `--cov-precision=2 --cov-fail-under=60` | 1 | `ERROR: Coverage failure: total of 59.20 is less than fail-under=60.00` |

> **Por que a precisão 2 e não 1 (footgun removido na rodada de correção 3).** O resumo
> final do `pytest-cov 7.1.0` compara o total **cru** com o `fail_under` sem aplicar a
> precisão (`failed = self.cov_total < self.options.cov_fail_under`,
> `pytest_cov/plugin.py:413`). Com o `59.2` nominal, o total cru (59,1985) fica **abaixo**
> do piso nominal e o plugin imprimia `FAIL Required test coverage of 59.2% not reached`
> em **toda execução verde** — ver a segunda linha da tabela acima, com rc=0. Quem decide o
> `rc` sempre foi a checagem do `coverage` (arredondada), e ela passava; mas normalizar a
> palavra FAIL ao lado de um check verde convidava exatamente o conserto errado (baixar o
> piso). Com `59.19` + precisão 2 as duas checagens **concordam** em todo inteiro alcançável:
> 3752 passa nas duas (`Required test coverage of 59.19% reached`); 3751 falha nas duas.
> Não "conserte" um log de cobertura baixando o piso: o `rc` é a fonte da verdade.

O `coverage.xml` pedido pelo plano é gerado e está no `.gitignore` (junto de `.mypy_cache/`).

### 6.5 Onde o gate é real (evidência RED→GREEN)

| Comando | Antes (BASE `141302d`) | Depois |
|---|---|---|
| `mypy app` | 369 erros, rc=1 | `Success: no issues found`, rc=0 |
| `mypy app --config-file pyproject.ratchet.toml` (§6.8) | *(não existia)* | `Found 127 errors in 28 files (checked 105 source files)`, **rc=1** — e o step do CI **passa** (127 ≤ 127, escopo 105 = esperado); com o orçamento rebaixado para 126, o step **falha** |
| `pytest tests/ -q --cov=app --cov-precision=2 --cov-fail-under=59.19` | *(não existia)* | 256 passed, rc=0 — `Required test coverage of 59.19% reached. Total coverage: 59.20%` |
| `pytest tests/ -q --cov=app --cov-precision=2 --cov-fail-under=60` | *(não existia)* | rc=1 — o piso morde |
| `pytest tests/ -q --cov=app --cov-precision=0 --cov-fail-under=59.2` | *(não existia)* | rc=1 — a precisão da comparação é o que muda o resultado |
| `ruff check app tests` | 0 erros | 0 erros |
| `ruff format --check .` | 0 pendentes | 0 pendentes (179 já formatados) |
| `pytest tests/ -q` | 256 passed | 256 passed |

E o gate **não é vazio**: inserindo uma função sem anotação em um dos 44 arquivos que
seguem em strict pleno (`app/schemas/article.py`), o `mypy app` volta a rc=1
(`Found 1 error in 1 file`); revertido o probe, volta a rc=0. Ou seja, código novo em
módulo **não** listado nas duas listas de overrides é cobrado de verdade. Para os 28
arquivos que o `mypy app` não olha, a cobertura equivalente é hoje a do shadow ratchet
(§6.8): um erro **novo** ali eleva o total acima de 127 e falha o CI.

### 6.6 Limitações — o gate de mypy é PARCIAL (declaração explícita)

- **28 de 105 arquivos (26,7%) estão fora de qualquer verificação** de mypy:
  `ignore_errors = true`. O mypy não olha o conteúdo deles.
- **ROTULAGEM DO CRITÉRIO (rodada de correção 2).** Onde o critério aparece — "Mypy bloqueia
  PR" nos critérios de aceite do plano e do brief da task, e "`mypy app` passa" no checklist
  de release (Task 19) — ele passa a estar escrito como **"sob o gate PARCIAL desta seção
  (§6.6)"**, com a lacuna dos 28 arquivos nomeada. Sem a qualificação, essas linhas
  prometiam uma cobertura de codebase que o gate não entrega.
- **A lacuna de regressão foi fechada (§6.8).** O shadow ratchet roda a mesma config sem o
  bloco de `ignore_errors` e falha se o total de erros crescer além de 127: um erro **novo**
  em qualquer dos 28 arquivos (inclusive `app/web/routes.py`) passa a falhar o CI, sem
  corrigir um único legado. **Ressalva (rodada de correção 5):** o invariante vale enquanto a
  config do ratchet não for **afrouxada** — o guard da §6.8 barra a chave `ignore_errors`
  ativa (valor `true`) nas grafias que enumera: sem aspas, com aspas duplas ou com aspas
  simples, em linha própria (indentada ou não) ou em tabela inline. Duas grafias ficam
  FORA da enumeração (chave depois de um `#` dentro de string, que o `sed` corta, e chave
  com escape unicode — `"\u0069gnore_errors"`, que o `tomllib` decodifica para o nome
  real); e outra relaxação (`disable_error_code`, `follow_imports`)
  baixa o total sem ser pega; é o "LIMITE INERENTE do desenho por contagem" documentado no
  fim da §6.8, com o conserto estrutural registrado lá como follow-up. O ratchet pós-release —
  corrigir os 127 e encolher as duas listas — continua sendo a task nova já registrada no
  ledger.
- **Pré-condição do shadow ratchet, agora verificada (rodada de correção 4).** O parágrafo
  acima só vale enquanto `pyproject.ratchet.toml` **não** reativar `ignore_errors`: com a
  chave ativa, o mypy volta a não reportar nada **sem reduzir** `(checked 105 source
  files)`, e o step sairia verde com o ratchet anulado (medido com o mypy real do venv:
  `Success: no issues found in 105 source files`, rc=0). Quem barra isso é a **checagem
  dedicada da chave** do step (§6.8), e **não** a asserção de escopo `checked == 105` — que
  continua detectando apenas `exclude`/`files` mais estreitos e arquivos novos/removidos.
- Dos 77 arquivos restantes, **44 estão sob strict pleno** e **33 sob apenas o default do
  mypy** (sem `disallow_untyped_defs` e companhia) — nesses 33, adicionar uma função sem
  anotação **não** falha o CI.
- O alvo do ratchet pós-release é **encolher as duas listas** de `[[tool.mypy.overrides]]`,
  arquivo a arquivo, começando pelos de maior contagem (`app/services/web_scraper.py` 36,
  `app/web/routes.py` 18, `app/ai/model_manager.py` 11) — e só então subir o piso de
  cobertura.
- `mypy app` imprime 1 linha de **note** (não erro) em `app/ai/manager.py:35`
  (`annotation-unchecked`, sugerindo `--check-untyped-defs`); o rc continua 0.
- `pytest` emite **187 warnings** pré-existentes (44 de `datetime.utcnow()`), fora do escopo
  desta task: não foram corrigidos nem silenciados.
- O workflow do GitHub Actions **não foi executado** nesta rodada (sem push e sem `act`): a
  evidência é a execução local, com o venv do projeto, dos mesmos comandos que o workflow
  roda. Para o step novo do shadow ratchet, a evidência inclui a execução do **próprio script
  do step** (extraído do `ci.yml`) contra a saída real do mypy e contra cenários adversos
  (§6.8).

### 6.7 Pins de versão (duas fontes, uma verdade)

O step de type check é bloqueante, então a versão do `mypy` passou a ser fixa — a mesma
decisão já tomada para o `ruff` na Task 9 (que é o footgun apontado na re-review da Task 9):

| Ferramenta | `pyproject.toml` (`[project.optional-dependencies].dev`) | `requirements-dev.txt` |
|---|---|---|
| ruff | `ruff==0.16.7` | `ruff==0.16.7` |
| mypy | `mypy==2.3.1` | `mypy==2.3.1` |

### 6.8 Shadow ratchet de mypy (rodadas de correção 2, 3, 4 e 5)

**Motivo.** Com o bloco de `ignore_errors` (§6.3), 28 de 105 arquivos ficavam fora de
**qualquer** verificação e nada no CI falhava se um erro novo fosse introduzido neles: o gate
não era autoverificável e as contagens comentadas podiam envelhecer em silêncio. O ratchet
devolve os 105 arquivos à verificação **sem corrigir um único erro legado** — `ignore_errors`
diz "nunca olhe"; o ratchet por contagem diz "olhe sempre, não piore".

| Peça | O que é |
|---|---|
| `bhub-backend-python/pyproject.ratchet.toml` | Cópia fiel da config de mypy do `pyproject.toml` (`python_version`, `ignore_missing_imports`, `strict = true` e o MESMO bloco de relaxamento dos 56 módulos) **sem** o bloco `[[tool.mypy.overrides]]` que aplica `ignore_errors`. Autossuficiente de propósito: `--config-file` **ignora** o `pyproject.toml`. A lista de módulos é **duplicada à mão**: qualquer patch nela tem de ser aplicado nos DOIS arquivos (`pyproject.toml` avisa). |
| Step `Type check ratchet (mypy shadow, budget 127)` | Roda `mypy app --config-file "$RATCHET_CONFIG"`, extrai o resumo e **falha se total > 127**; e falha FECHADO (exit 1) em entrada inválida — de FORMA (`127,`, vazio, `abc`) **e de MAGNITUDE** (mais de 9 dígitos), escopo degradado, parsing duvidoso ou `ignore_errors` **ativo** na config do ratchet (valor `true`, nas grafias enumeradas: chave sem aspas, citada com `"` ou `'`, em linha própria, indentada ou em tabela inline; `= false` é inerte e **passa** — §6.8 traz as grafias cobertas e as duas não cobertas). |
| `RATCHET_BUDGET=127` + `EXPECTED_SOURCE_FILES=105` + `RATCHET_CONFIG=pyproject.ratchet.toml` (no `ci.yml`) | Orçamento do legado, escopo esperado e caminho da config, numa fonte única — cada um em LINHA PRÓPRIA também para o harness poder substituí-la (é o único ponto do bloco que o harness muta). **BAIXE** o orçamento ao corrigir erros legados; nunca suba sem registrar a dívida nova no mesmo PR. Atualize o escopo se um arquivo entrar/sair de `app/`. Os dois números são validados como inteiro de **até 9 dígitos** (ver C1b) antes de qualquer comparação. |
| `bhub-backend-python/tests/ci/ratchet_step_harness.sh` | Harness determinístico: extrai o bloco `run:` **real** do `ci.yml` (verbatim, dedent), põe um **stub de `mypy`** no PATH e executa o step com `bash -e` e cwd = `bhub-backend-python/`. 33 cenários do ratchet + 2 de cobertura (opt-in `RATCHET_HARNESS_COVERAGE=1`). É o que impede o retorno dos falsos verdes de C1/C1b/C2/C3/C4 — e **o CI o executa** no step `Run ratchet step harness` (rodada de correção 4); sem isso ele só rodava à mão. |

**Medição** (mypy 2.3.1, o pin): `Found 127 errors in 28 files (checked 105 source files)`,
rc=1 — os mesmos 28 arquivos do §6.3, e as **28 contagens comentadas conferem uma a uma**
(36, 18, 11, 8, 7, 6, 5, 4, 4, 4, 3, 2, 2, 2, 2, 1×13 = 127). Composição: `assignment` 30,
`union-attr` 30, `attr-defined` 26, `arg-type` 12, ... — o `attr-defined` a mais (26 contra
os 25 da medição a strictness default) é o reexport implícito de `app/ai/model_manager.py:9`
já explicado no §6.2. O `model_manager` é também o único arquivo cuja contagem difere entre
as duas medições (11 aqui, 10 a strictness default).

> **O `105` não é o `56`.** O escopo checado é o número de **arquivos** de `app/` que o mypy
> lê — `Success: no issues found in 105 source files` na config principal e
> `(checked 105 source files)` no ratchet. O `56` é a quantidade de **módulos** do bloco de
> relaxamento de strict (§6.2), não o escopo. `EXPECTED_SOURCE_FILES=105` é o valor medido;
> codificar 56 deixaria o step vermelho no primeiro run.

**A armadilha, explicitada.** O mypy sai com **rc=1** nesta config por *design* (há 127
erros), então o rc não pode decidir o step: um step que falhasse no rc seria vermelho para
sempre, e um step que o ignorasse sem checar o total seria verde para sempre. O que decide é
o resumo extraído — e um gate que decide por texto extraído precisa falhar fechado. Foi
exatamente aí que a rodada 2 passou a perna em três classes de falso verde — outras duas
foram abertas depois e fechadas nas rodadas 3, 4 e 5 —, todas reproduzidas pelo harness antes
da correção (**10 das 18 linhas divergiam**: 8 falsos verdes + 2 desempates errados de
parsing; o harness passou a ter 28 cenários do ratchet na rodada 4 e 33 ao fim da rodada 5,
que acrescentou as grafias citadas da chave e o controle de valor):

| Classe | Falso verde (rodada em que apareceu) | Correção |
|---|---|---|
| **C1 — operandos (forma)** | `RATCHET_BUDGET=127,` (typo na linha que o próprio step manda humanos editarem) + `Found 999 errors`: `[ "$total" -gt "127," ]` falha com `integer expression expected`; dentro de `if` sob `bash -e` isso é condição falsa → imprime `OK: linha do legado intacta (999 <= 127,)` e **sai 0**. Idem orçamento vazio ou `abc`. | `[[ "$RATCHET_BUDGET" =~ ^[0-9]{1,9}$ ]]` (idem `EXPECTED_SOURCE_FILES` e os números extraídos do mypy) antes de qualquer comparação: entrada inválida → `::error::` + `exit 1`. O teto de 9 dígitos entrou na rodada 4 (classe C1b, abaixo); a rodada 3 validava só a forma (`^[0-9]+$`). |
| **C1b — operandos (magnitude)** — rodada 4 | `RATCHET_BUDGET=99999999999999999999` (20 dígitos: passa no `^[0-9]+$`) + `Found 999 errors in 28 files (checked 105 source files)`: a comparação estoura o int64, o `test` devolve erro e, dentro de `if` sob `bash -e`, isso é condição falsa → `OK: linha do legado intacta (999 <= 99999999999999999999)` e **rc=0**. Mesmo mecanismo no gate de escopo: `EXPECTED_SOURCE_FILES=99999999999999999999` faz a asserção `checked == 105` ser **pulada em silêncio** (`Found 0 errors in 3 files (checked 3 source files)` → rc=0). Limite do int64: `9223372036854775808` (2^63) já dispara. | Teto de **9 dígitos** no regex dos quatro números validados (`RATCHET_BUDGET`, `EXPECTED_SOURCE_FILES` e `total`/`checked` vindos do mypy): `^[0-9]{1,9}$` (até 999.999.999, folgado para orçamento/escopo e imune ao overflow). Acima disso é entrada inválida → `::error::` + `exit 1`. |
| **C2 — escopo** | `Found 0 errors in 3 source files`: o step só olhava o total, então uma config degradada (`exclude`/`files` mais estreitos, ou arquivo novo/removido em `app/`) virava um no-op verde. | Exige `(checked N source files)` e `N == 105`. Vale para os dois formatos de resumo (`Found ...` e `Success ...`). **Limite desta asserção:** ela detecta redução de ESCOPO, não de estritudez — `ignore_errors` **não** muda `checked` (segue 105) e **não** é pego aqui; esse caso é o C4. |
| **C3 — parsing** | `head -n 1` ficava com a **primeira** linha `Found`: `Found 3 errors in 1 file` antes de `Found 200 errors in 28 files` → `OK` com 3 ≤ 127. | A ÚLTIMA linha de resumo é a única usada (`tail -n 1`), e os dois números saem dela; sem resumo reconhecível ou com número não numérico → `exit 1`. |
| **C4 — `ignore_errors` reativado** — rodadas 4 e 5 | Chave `ignore_errors` de volta em `pyproject.ratchet.toml`: o mypy continua checando os **105** arquivos (o gate de escopo PASSA) mas para de reportar os 127 legados → `Success: no issues found in 105 source files`, rc=0, com o shadow ratchet **anulado** (medido com o mypy real do venv, config copiada para `/tmp`, árvore intocada). Este é o caso que os textos da rodada 3 diziam estar coberto pela asserção de escopo — não estava. A rodada 5 mediu duas variantes que o guard da rodada 4 deixava passar: a chave **citada** (`"ignore_errors" = true` / `'ignore_errors' = true`, que o mypy honra: 127 → **60** erros com 5 módulos, `(checked 105 source files)` intacto — 60 = 127 − 67, a soma do §6.3 para esses 5) e a **tabela inline com a chave citada**, as duas saindo **rc=0** com o ratchet anulado; e mediu o caso espelho, `ignore_errors = false`, rejeitado com a mensagem FALSA de "isso ANULA o ratchet" quando ele mede **exatamente os mesmos 127 / 28 / checked 105** (a chave é o default do mypy, é inerte). | Checagem dedicada da CHAVE **e do VALOR**, antes do parsing: `sed 's/#.*//' "$RATCHET_CONFIG" \| grep -qE "(^\|[[:space:],{])("\|')?ignore_errors("\|')?[[:space:]]*=[[:space:]]*true"` → `::error::` + `exit 1`. Ignora as menções em **comentário** (o arquivo real tem várias) e pega a chave ativa em linha própria, indentada ou em tabela inline, **inclusive citada** com `"` ou `'`. O valor tem de ser o literal `true`, o único que anula o ratchet: `ignore_errors = false` **passa** (controle negativo do cenário 30 — a rodada 5 fechou os dois defeitos nesta mesma linha). **Limite desta checagem:** ela cobre ESTA chave; outra relaxação da config (`disable_error_code`, `follow_imports`) baixa o total sem ser pega — ver "LIMITE INERENTE do desenho por contagem" abaixo. |

**Comportamento verificado — cenários do harness** (`bash
bhub-backend-python/tests/ci/ratchet_step_harness.sh`; **35/35 ok** com
`RATCHET_HARNESS_COVERAGE=1`, rc do harness = 0 — 33 do ratchet + 2 de cobertura). Coluna
"stub" = saída sintética do mypy / rc sintético; orçamento 127 salvo onde indicado:

O harness separa o que EXISTE do que RODOU no resumo final
(`35 cenário(s) disponíveis, 33 executado(s) — 33 ok, 0 divergência(s), 2 pulado(s)`): uma
corrida sem `RATCHET_HARNESS_COVERAGE=1` deixa explícito que os 2 cenários de cobertura real
ficaram de fora — antes o resumo dizia só "16 ok" e a linha de skip passava batido.

Roda também **no CI** (step `Run ratchet step harness`, rodada de correção 4), sem
`RATCHET_HARNESS_COVERAGE=1` — ou seja, no CI os 33 do ratchet são executados e os 2 de
cobertura ficam para o step `Coverage floor`, que roda a suíte real logo em seguida. Os 28
cenários que existiam na rodada 4 foram executados também em **ubuntu 24.04 / bash 5.2 /
GNU sed 4.9 / mawk 1.3.4 e gawk**, além do bash 3.2 do macOS, com o mesmo resultado (rc=0 do
harness) — é o que autoriza o step no CI. Os **5 cenários novos da rodada 5** (27-31) foram
executados até agora no **bash 3.2 + BSD grep do macOS** (33 ok, 2 pulados, rc=0); eles não
usam nada além de `cp`/`cat`/`printf` e da mesma linha de guard, e o primeiro run do step no
ubuntu será a segunda testemunha — não há medição própria em ubuntu para eles nesta rodada.

| # | Entrada (stub) | Esperado | Medido |
|---|---|---|---|
| 1 | `Found 127 errors in 28 files (checked 105 source files)` / rc=1 | PASS | rc=0 — `OK: … (127 <= 127) e escopo intacto (105 source files)` |
| 2 | `Found 128 errors in 28 files (checked 105)` / rc=1 | FAIL | rc=1 — `regressão de tipos: 128 > 127` |
| 3 | `Found 0 errors in 28 files (checked 105)` / rc=1, `RATCHET_BUDGET=127,` | FAIL | rc=1 — `RATCHET_BUDGET inválido: '127,'` |
| 4 | `Found 999 errors in 28 files (checked 105)` / rc=1, `RATCHET_BUDGET=127,` | FAIL | rc=1 — `RATCHET_BUDGET inválido: '127,'` (antes: rc=0 com 999) |
| 5 | `RATCHET_BUDGET=""` | FAIL | rc=1 — `RATCHET_BUDGET inválido: ''` |
| 6 | `RATCHET_BUDGET=abc` | FAIL | rc=1 — `RATCHET_BUDGET inválido: 'abc'` |
| 7 | `Found 0 errors in 3 source files` / rc=1 | FAIL | rc=1 — não conseguiu extrair a contagem de source files |
| 7b | `Found 0 errors in 3 files (checked 3 source files)` / rc=1 | FAIL | rc=1 — `escopo divergente: checou 3, esperado 105` |
| 8 | `Found 127 errors in 28 files` (sem contagem) / rc=1 | FAIL | rc=1 — não conseguiu extrair a contagem |
| 9 | `Found 3 errors in 1 file (checked 105)` + `Found 200 errors in 28 files (checked 105)` / rc=1 | FAIL | rc=1 — usou a ÚLTIMA (200 > 127) |
| 9b | mesma ordem invertida (última = 127) | PASS | rc=0 — usou a ÚLTIMA |
| 12 | `Success: no issues found in 105 source files` / rc=0 | PASS | rc=0 (total 0, escopo 105) |
| 13 | `Success: no issues found in 0 source files` / rc=0 | FAIL | rc=1 — `escopo divergente: checou 0, esperado 105` |
| 14 | rc=2 do mypy | FAIL | rc=1 — `mypy ratchet saiu com rc=2` |
| 15 | saída vazia / rc=1 | FAIL | rc=1 — não conseguiu extrair o total |
| 16 | saída só com linha `note` / rc=1 | FAIL | rc=1 — não conseguiu extrair o total |
| 17 | `Found 1 error in 1 file (errors prevented further checking)` / rc=1 — formato REAL de erro bloqueante do mypy | FAIL | rc=1 — não conseguiu extrair a contagem de source files (fail-closed congelado) |
| 18 | `Found 999 errors in 28 files (checked 105)` / rc=1, `RATCHET_BUDGET=99999999999999999999` | FAIL | rc=1 — `RATCHET_BUDGET inválido` (antes: **rc=0** com 999 erros) |
| 19 | idem, `RATCHET_BUDGET=9223372036854775808` (2^63) | FAIL | rc=1 — `RATCHET_BUDGET inválido` (antes: **rc=0**) |
| 19b | idem, `RATCHET_BUDGET=9223372036854775807` (int64 max) | FAIL | rc=1 — acima do teto de 9 dígitos: entrada inválida, não comparação |
| 20 | `Found 127 errors in 28 files (checked 105)` / rc=1, `RATCHET_BUDGET=999999999` (teto válido) | PASS | rc=0 — `(127 <= 999999999)` (controle: o teto não rejeita tudo) |
| 20b | idem, `RATCHET_BUDGET=1000000000` (teto + 1) | FAIL | rc=1 — `RATCHET_BUDGET inválido` (borda) |
| 21 | `Found 0 errors in 3 files (checked 3 source files)` / rc=1, `EXPECTED_SOURCE_FILES=99999999999999999999` | FAIL | rc=1 — `EXPECTED_SOURCE_FILES inválido` (antes: **rc=0**, asserção de escopo pulada) |
| 22 | `Found 127 errors in 28 files (checked 105)` / rc=1, `EXPECTED_SOURCE_FILES=105` (explícito) | PASS | rc=0 — controle do mecanismo de override |
| 23 | `Success: no issues found in 105 source files` / rc=0, `RATCHET_CONFIG=<cópia com ignore_errors ativo>` | FAIL | rc=1 — `tem a chave ATIVA 'ignore_errors': isso ANULA o ratchet` (antes: **rc=0** com o ratchet anulado) |
| 24 | config REAL do ratchet (cita `ignore_errors` só em comentários), `Found 127 …` | PASS | rc=0 — controle do guard |
| 25 | `ignore_errors` em TOML de tabela inline (uma linha), `Success … 105` | FAIL | rc=1 — o guard não depende de a chave começar a linha |
| 26 | config com módulo/valor que só CONTÉM o texto `ignore_errors` | PASS | rc=0 — controle negativo: o guard não reprova por substring |
| 27 | `"ignore_errors" = true` (chave CITADA, aspas duplas) em linha própria | FAIL | rc=1 — `tem a chave ATIVA 'ignore_errors' (valor 'true')` (antes: **rc=0** com o ratchet anulado; o mypy real mediu **60** erros em vez de 127, `checked 105`) |
| 28 | `'ignore_errors' = true` (chave CITADA, aspas simples) | FAIL | rc=1 — idem (antes: **rc=0**; o mypy real mediu 126 erros com a chave em 1 módulo) |
| 29 | `overrides = [{ module = [...], "ignore_errors" = true }]` (tabela inline com a chave citada) | FAIL | rc=1 — idem (antes: **rc=0**) |
| 30 | `ignore_errors = false` (chave presente, valor default/inertes) | PASS | rc=0 — `OK: … (127 <= 127) e escopo intacto (105 source files)` (antes: **rc=1** com a mensagem FALSA de que a chave "ANULA o ratchet"; o mypy real mede os mesmos 127/28/checked 105) |
| 31 | `"ignore_errors" = false` em tabela inline (citada + inerte) | PASS | rc=0 — controle negativo das duas checagens juntas (citar a chave e exigir o valor são independentes) |
| 10 | cobertura real, piso do `ci.yml` (`RATCHET_HARNESS_COVERAGE=1`) | PASS | rc=0 — o step roda a suíte real, 256 passed, `Required test coverage of 59.19% reached. Total coverage: 59.20%` |
| 11 | cobertura real com piso temporário 60 | FAIL | rc=1 — `FAIL Required test coverage of 60% not reached. Total coverage: 59.20%` (mensagem do `pytest-cov` 7.1.0, medida nesta rodada) |

Nos cenários 10/11 o harness imprime a ÚLTIMA linha da saída do step, que neste venv é
`sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute` (aviso
pré-existente do environment, anterior a esta task). O que decide o cenário é o `rc`; as
mensagens acima saem do corpo da saída, verificado diretamente com o pytest.

E com o **mypy real** do venv (bloco `run:` extraído do `ci.yml`, orçamento 127):
`Found 127 errors in 28 files (checked 105 source files)`, rc do mypy = 1 → **rc=0** no step,
com `OK: linha do legado intacta (127 <= 127) e escopo intacto (105 source files)`.

O ratchet custa uma segunda passada do mypy (~10 s), o mesmo custo que o step de cobertura já
aceitava por legibilidade do log, e é determinístico porque o `mypy` está pinado (§6.7).

**Grafias da chave que o guard cobre — e as duas que não cobre (Task 11).** A enumeração
abaixo é o que o guard de fato barra; "qualquer grafia TOML" era over-claim. Cobertas:
`ignore_errors = true` (sem aspas, em linha própria, indentada ou não), `"ignore_errors" =
true`, `'ignore_errors' = true` e as mesmas dentro de tabela inline (`overrides = [{ module =
[...], "ignore_errors" = true }]`) — cenários 23, 25, 27, 29 e 31 do harness —, sempre exigindo
o valor literal `true` (cenários 30-31: `= false` é o default do mypy, é inerte e PASSA). NÃO
cobertas: (a) a chave na MESMA linha de um `#` dentro de string — o `sed 's/#.*//'` corta dali
para o fim e o texto da chave não chega ao `grep` (verificado: a linha `overrides = [{ module =
["app.web.routes", "#"], "ignore_errors" = true }]` vira `overrides = [{ module =
["app.web.routes", "` antes do `grep`, e o guard não casa); e (b) a chave com **escape
unicode** — `"\u0069gnore_errors" = true`, que o `tomllib` decodifica para `ignore_errors` e o
mypy **honra**: medido nesta rodada com o mypy real do venv (2.3.1), a config do ratchet com
essa chave em `app.web.routes` mede `Found 109 errors in 27 files (checked 105 source files)`
— o total caiu de 127 para 109 enquanto o guard da (b) não casa a linha. As duas são o mesmo
limite de desenho do "LIMITE INERENTE" abaixo, e o conserto estrutural é o follow-up nomeado
no fim da seção.

**LIMITE INERENTE do desenho por contagem (rodada de correção 5 — documentado, NÃO corrigido).**
O step decide por **contagem de erros** de uma config que vive no próprio repositório, e o guard
do C4 cobre **uma** chave dessa config. Qualquer OUTRA relaxação de `[tool.mypy]` baixa o total,
mantém `(checked 105 source files)` intacto e o step sai **verde**. Medido nesta rodada com o
**mypy real do venv** (2.3.1), o bloco `run:` do `ci.yml` e configs derivadas em `/tmp` (árvore
intocada):

| Relaxação injetada em `pyproject.ratchet.toml` | Total medido | Step |
|---|---|---|
| `disable_error_code = ["assignment"]` | `Found 97 errors in 21 files (checked 105 source files)` | **rc=0** (verde) |
| `follow_imports = "skip"` | `Found 58 errors in 27 files (checked 105 source files)` | **rc=0** (verde — **69** erros de folga silenciosa contra o orçamento 127) |
| `follow_imports = "silent"` | `Found 127 errors in 28 files (checked 105 source files)` | rc=0 (sem efeito) |

Um ratchet que conta erros **não consegue distinguir** "menos erros porque o código melhorou" de
"menos erros porque a config foi afrouxada": o guard de `ignore_errors` é um conserto
DIRECIONADO (uma chave, nas grafias TOML que a §6.8 enumera — não em todas elas —, e só com
o valor `true`), não estrutural. Isso
**não é regressão desta rodada** — a rodada 3 tinha o mesmo buraco — e não há vetor de acidente
equivalente ao `ignore_errors` (que existe no `pyproject.toml`, pronto para ser copiado); mas o
invariante vendido acima ("erro novo em QUALQUER arquivo passa a falhar") só vale enquanto nada
mais da config do ratchet for relaxado — é isso, e só isso, que o gate entrega hoje.

**Follow-up nomeado (não implementado nesta rodada, fora de escopo):** comparar o `[tool.mypy]`
do `pyproject.ratchet.toml` com o do `pyproject.toml` de forma **estrutural**, tolerando apenas o
bloco `[[tool.mypy.overrides]]` que aplica `ignore_errors` — exatamente a "cópia fiel" que este
§6.8 já descreve como invariante do desenho. Enquanto ele não existir, o gate é **contagem +
guard de uma chave**, e a cobertura de estritudez depende da disciplina do PR.

**O que ele NÃO faz:** não valida cada comentário `# N` individualmente (só o total), não
corrige nenhum dos 127 erros legados e não substitui o ratchet pós-release — ele apenas
garante que a linha do legado não suba. Limite conhecido e não resolvido pelo desenho: o
**total** pode ser mascarado por um PR que conserte 5 erros legados e introduza 5 novos
(127 → 127, verde). O caso que a §6.6 nomeia (erro novo sem conserto compensatório) é pego,
e o step manda baixar o orçamento ao corrigir legado — mas isso depende de disciplina do PR.
