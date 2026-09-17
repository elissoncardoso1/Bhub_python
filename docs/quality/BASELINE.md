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
| Cobertura | `pytest tests/ -q --cov=app --cov-report=term-missing` | **59%** (6359 statements, 2609 missing) | **59%** (6338 statements, 2586 missing) — com piso bloqueante `--cov-precision=1 --cov-fail-under=59.2` (piso efetivo ≥ 59,15%) desde a Task 10 / T3.4 (§6.4) |

Notas de leitura:

- O baseline de lint/format/testes/cobertura foi medido pelo controller sobre o HEAD
  limpo (`c9d578a`), usando `git stash` para isolar o diff parcial do implementador
  interrompido.
- A cobertura **não regrediu** (59% → 59%). O total de statements caiu de 6359 para 6338
  porque refatorações do Ruff (por exemplo, fusão de `if` aninhados em `app/services/article_parser.py`
  e remoção de código morto) eliminaram linhas executáveis. Menos statements e a mesma
  porcentagem = menos linhas descobertas em termos absolutos (2609 → 2586).
- **Reconciliação do drift de 1 statement (rodada de correção 2).** Esta coluna trazia
  `6339 statements` enquanto o §6.4 e o `ci.yml` traziam `6338`. Nenhum dos dois números
  estava errado por conta própria: 6339 era a medição feita ANTES do commit `141302d`
  (rodada de correção da Task 9), que moveu `from sqlalchemy import event  # noqa: E402`
  do meio de `app/database.py` para o topo, onde a linha se fundiu na
  `from sqlalchemy import event, text` já existente: duas **statements** de import
  viraram uma (−1 statement). Era uma linha executada, logo os cobertos caem de 3753
  para 3752 com o mesmo `missing` 2586 — e ambos os totais exibem 59,2%. O número foi
  corrigido aqui para a medição atual deste HEAD (`coverage 7.16.1`):
  `TOTAL 6338 2586 59.2%`.
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
removido na Task 9 e, na Task 10, entraram os dois gates do Épico 3 que faltavam. Hoje são
**cinco steps bloqueantes** em `bhub-backend-python` (`defaults.run.working-directory`),
mais o de testes — **nenhum** deles usa `continue-on-error`:

```yaml
- name: Lint (ruff check)
  run: ruff check app tests

- name: Format check (ruff format --check)
  run: ruff format --check .

- name: Type check (mypy app)             # Task 10 / T3.3 — gate PARCIAL (§6.6)
  run: mypy app

- name: Type check ratchet (mypy shadow, budget 127)   # rodada de correção 2 / §6.8
  run: |
    RATCHET_BUDGET=127
    rc=0
    mypy app --config-file pyproject.ratchet.toml > /tmp/mypy-ratchet.txt 2>&1 || rc=$?
    cat /tmp/mypy-ratchet.txt
    # rc=1 é o esperado nesta config; só o TOTAL acima do orçamento falha o step.

- name: Coverage floor (fail under 59.2%, precision 1)  # Task 10 / T3.4
  run: |
    pytest tests/ \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-precision=1 \
      --cov-fail-under=59.2
```

**Rótulo dos critérios de aceite do CI** (aplicado nesta rodada de correção 2 no ledger do
plano e no brief da task, porque a redação antiga prometia mais do que o gate entrega):

| Critério | Como ele realmente vale |
|---|---|
| "Mypy bloqueia PR" / "`mypy app` passa" (Task 19) | **Sob o gate PARCIAL do §6.6**: 28 de 105 arquivos ficam fora de verificação (`ignore_errors`). Erro novo nos 44 em strict pleno e nos 33 relaxados falha o CI; erro novo nos 28 é pego pelo shadow ratchet do §6.8, não pelo step `mypy app`. Ratchet pós-release (corrigir os 127 legados) segue pendente. |
| "Coverage não pode cair abaixo do baseline" | Piso `--cov-precision=1 --cov-fail-under=59.2` ⇒ reprova a partir de 59,1% (efetivo: < 59,15%, i.e. qualquer queda de 4+ statements). Antes era `--cov-fail-under=59` com precisão 0 ⇒ reprovava apenas abaixo de 58,5%. |

(O step `Run tests` — `pytest tests/ -v` — continua no lugar, antes do de cobertura. A suíte
roda duas vezes de propósito: ~10 s, e assim uma regressão de cobertura aparece como falha
do próprio step, não escondida no step de testes.)

`requirements-dev.txt` fixa `ruff==0.16.7`, a versão em que o repositório foi validado: um
`ruff format --check` bloqueante só é determinístico se a versão do formatter for fixa.
Na rodada de correção 1, o extra `dev` de `pyproject.toml` foi **alinhado ao mesmo pin**
(`ruff==0.16.7`, antes `ruff>=0.8.0`), eliminando a segunda fonte de verdade: antes,
`pip install -e ".[dev]"` podia instalar uma versão diferente da validada. Na Task 10 o
mesmo tratamento foi dado ao `mypy` (§6.7).

### Ainda fora do escopo (tasks seguintes do Épico 3)

- Build da imagem Docker no CI → Task 11 (T3.5).

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
  --cov-precision=1 --cov-fail-under=59.2
```

| Medida | Valor |
|---|---|
| Cobertura do baseline | **59,2%** (3752/6338 statements; 2586 linhas não cobertas) — valor cru **59,1985%** |
| Piso do CI | `--cov-precision=1 --cov-fail-under=59.2` |
| Piso **efetivo** | reprova a partir de 59,1% (na prática: < 59,15%, ou seja, qualquer queda de **4+ statements** cobertos) |
| Testes | **256 passed**, 0 failed |

**Precisão do piso (corrigida na rodada de correção 2).** O `coverage 7.16.1` decide por
`round(total, precision) < fail_under` (`coverage/results.py:503`), e `precision` tem
default **0**: o antigo `--cov-fail-under=59` só reprovava abaixo de **58,5%** — uma queda
de até 44 statements (−0,70 p.p.) passava verde, inclusive um valor **abaixo** do baseline
medido. Com `--cov-precision=1` a comparação passa a ser a 1 decimal: o total de hoje
(59,1985%) arredonda para 59,2 e **passa**, enquanto um total que arredonde para 59,1
**falha**. Evidências locais do piso mordendo:

| Comando | rc | Saída |
|---|---|---|
| `--cov-precision=1 --cov-fail-under=59.2` (o do CI) | **0** | `TOTAL 6338 2586 59.2%` — passa |
| `--cov-precision=0 --cov-fail-under=59.2` | **1** | `Coverage failure: total of 59 is less than fail-under=59` |
| `--cov-precision=1 --cov-fail-under=59.25` | **1** | `Coverage failure: total of 59.2 is less than fail-under=59.2` (a mensagem formata o `fail-under` com a precisão do gate: 59,25 → 59,2) |
| `--cov-precision=1 --cov-fail-under=60` | **1** | reprova |

> Nuance conhecida, medida e **não** escondida: o resumo final do `pytest-cov 7.1.0` compara
> o total **cru** com o `fail_under` sem aplicar a precisão
> (`failed = self.cov_total < self.options.cov_fail_under`, `pytest_cov/plugin.py:413`), e
> por isso imprime `FAIL Required test coverage of 59.2% not reached. Total coverage: 59.20%`
> **mesmo com o step verde** (o total cru é 59,1985, abaixo do 59,2 nominal). Quem decide o
> `rc` é a checagem do `coverage`, que arredonda por precisão — e ela passa. Não "conserte"
> isso baixando o piso; o `rc` é a fonte da verdade.

O `coverage.xml` pedido pelo plano é gerado e está no `.gitignore` (junto de `.mypy_cache/`).

### 6.5 Onde o gate é real (evidência RED→GREEN)

| Comando | Antes (BASE `141302d`) | Depois |
|---|---|---|
| `mypy app` | 369 erros, rc=1 | `Success: no issues found`, rc=0 |
| `mypy app --config-file pyproject.ratchet.toml` (§6.8) | *(não existia)* | 127 erros em 28 arquivos, **rc=1** — e o step do CI **passa** (127 ≤ 127); com o mesmo comando e o orçamento rebaixado para 126, o step **falha** |
| `pytest tests/ -q --cov=app --cov-precision=1 --cov-fail-under=59.2` | *(não existia)* | 256 passed, rc=0 |
| `pytest tests/ -q --cov=app --cov-precision=1 --cov-fail-under=59.25` | *(não existia)* | rc=1 — o piso morde |
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
  corrigir um único legado. O ratchet pós-release — corrigir os 127 e encolher as duas
  listas — continua sendo a task nova já registrada no ledger.
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

### 6.8 Shadow ratchet de mypy (rodada de correção 2)

**Motivo.** Com o bloco de `ignore_errors` (§6.3), 28 de 105 arquivos ficavam fora de
**qualquer** verificação e nada no CI falhava se um erro novo fosse introduzido neles: o gate
não era autoverificável e as contagens comentadas podiam envelhecer em silêncio. O ratchet
devolve os 105 arquivos à verificação **sem corrigir um único erro legado** — `ignore_errors`
diz "nunca olhe"; o ratchet por contagem diz "olhe sempre, não piore".

| Peça | O que é |
|---|---|
| `bhub-backend-python/pyproject.ratchet.toml` | Cópia fiel da config de mypy do `pyproject.toml` (`python_version`, `ignore_missing_imports`, `strict = true` e o MESMO bloco de relaxamento dos 56 módulos) **sem** o bloco `[[tool.mypy.overrides]]` que aplica `ignore_errors`. Autossuficiente de propósito: `--config-file` **ignora** o `pyproject.toml`. |
| Step `Type check ratchet (mypy shadow, budget 127)` | Roda `mypy app --config-file pyproject.ratchet.toml`, captura a saída, extrai o total e **falha apenas se total > 127**; falha alto (rc>1 ou total não parseável) em vez de aprovar em silêncio. |
| `RATCHET_BUDGET=127` (no `ci.yml`) | Orçamento do legado. **BAIXE** ao corrigir erros legados; nunca suba sem registrar a dívida nova no mesmo PR. |

**Medição** (mypy 2.3.1, o pin): `Found 127 errors in 28 files (checked 105 source files)`,
rc=1 — os mesmos 28 arquivos do §6.3, e as **28 contagens comentadas conferem uma a uma**
(36, 18, 11, 8, 7, 6, 5, 4, 4, 4, 3, 2, 2, 2, 2, 1×13 = 127). Composição: `assignment` 30,
`union-attr` 30, `attr-defined` 26, `arg-type` 12, ... — o `attr-defined` a mais (26 contra
os 25 da medição a strictness default) é o reexport implícito de `app/ai/model_manager.py:9`
já explicado no §6.2. O `model_manager` é também o único arquivo cuja contagem difere entre
as duas medições (11 aqui, 10 a strictness default).

**A armadilha, explicitada.** O mypy sai com **rc=1** nesta config por *design* (há 127
erros), então o rc não pode decidir o step: um step que falhasse no rc seria vermelho para
sempre, e um step que o ignorasse sem checar o total seria verde para sempre. O que decide é
o total extraído da saída. Comportamento verificado executando o **próprio script do step**
(extraído do `ci.yml`) com o mypy real do venv:

| Cenário | Medido |
|---|---|
| Saída real: `Found 127 errors in 28 files`, rc=1, `RATCHET_BUDGET=127` | ✅ **rc=0** — `OK: linha do legado intacta (127 <= 127)` |
| Mesmo mypy real, só o orçamento rebaixado para 126 | ✅ **rc=1** — `::error::regressão de tipos: 127 > 126` |
| `Found 128 errors in 28 files`, rc=1 (erro novo de verdade) | ✅ rc=1 — `::error::regressão de tipos: 128 > 127` |
| `Success: no issues found`, rc=0 | ✅ rc=0 (total 0) |
| `Found 1 error in 1 file` (singular) | ✅ rc=0 (1 ≤ 127) |
| rc=2 (falha de execução do mypy) | ✅ rc=1 — `::error::mypy ratchet saiu com rc=2` |
| Saída vazia ou não parseável (rc=1) | ✅ rc=1 — `::error::não foi possível extrair o total` |

O ratchet custa uma segunda passada do mypy (~10 s), o mesmo custo que o step de cobertura já
aceitava por legibilidade do log, e é determinístico porque o `mypy` está pinado (§6.7).

**O que ele NÃO faz:** não valida cada comentário `# N` individualmente (só o total), não
corrige nenhum dos 127 erros legados e não substitui o ratchet pós-release — ele apenas
garante que a linha do legado não suba.
