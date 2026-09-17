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
| Tipagem | `mypy app` | **369 erros em 61 arquivos** (105 arquivos analisados) | **rc=0** na Task 10 / T3.3 — via ratchet de strict por módulo + 28 arquivos com `ignore_errors` enumerado; ver §6 |
| Testes | `pytest tests/ -q` | **256 passed**, 0 failed | **256 passed**, 0 failed |
| Cobertura | `pytest tests/ -q --cov=app --cov-report=term-missing` | **59%** (6359 statements, 2609 missing) | **59%** (6339 statements, 2586 missing) — com piso bloqueante `--cov-fail-under=59` desde a Task 10 / T3.4 (§6.4) |

Notas de leitura:

- O baseline de lint/format/testes/cobertura foi medido pelo controller sobre o HEAD
  limpo (`c9d578a`), usando `git stash` para isolar o diff parcial do implementador
  interrompido.
- A cobertura **não regrediu** (59% → 59%). O total de statements caiu de 6359 para 6339
  porque refatorações do Ruff (por exemplo, fusão de `if` aninhados em `app/services/article_parser.py`
  e remoção de código morto) eliminaram linhas executáveis. Menos statements e a mesma
  porcentagem = menos linhas descobertas em termos absolutos (2609 → 2586).
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
**quatro steps bloqueantes** em `bhub-backend-python` (`defaults.run.working-directory`),
mais o de testes — **nenhum** deles usa `continue-on-error`:

```yaml
- name: Lint (ruff check)
  run: ruff check app tests

- name: Format check (ruff format --check)
  run: ruff format --check .

- name: Type check (mypy app)          # Task 10 / T3.3
  run: mypy app

- name: Coverage floor (fail under 59%)  # Task 10 / T3.4
  run: |
    pytest tests/ \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=59
```

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
pytest tests/ -q --cov=app --cov-report=term-missing --cov-report=xml --cov-fail-under=59
```

| Medida | Valor |
|---|---|
| Cobertura do baseline | **59,2%** (3752/6338 statements; 2586 linhas não cobertas) |
| Piso do CI | `--cov-fail-under=59` |
| Testes | **256 passed**, 0 failed |

O piso é o **inteiro que o baseline sustenta** (59,2% → 59), sem inflar: **60 falha hoje** —
verificado, `FAIL Required test coverage of 60% not reached. Total coverage: 59.20%`. O
step do CI roda exatamente isso; o `coverage.xml` pedido pelo plano é gerado e está no
`.gitignore` (junto de `.mypy_cache/`).

### 6.5 Onde o gate é real (evidência RED→GREEN)

| Comando | Antes (BASE `141302d`) | Depois |
|---|---|---|
| `mypy app` | 369 erros, rc=1 | `Success: no issues found`, rc=0 |
| `pytest tests/ -q --cov=app ... --cov-fail-under=59` | *(não existia)* | 256 passed, rc=0 |
| `pytest tests/ -q --cov=app --cov-fail-under=60` | *(não existia)* | rc=1 — o piso morde |
| `ruff check app tests` | 0 erros | 0 erros |
| `ruff format --check .` | 0 pendentes | 0 pendentes (179 já formatados) |
| `pytest tests/ -q` | 256 passed | 256 passed |

E o gate **não é vazio**: inserindo uma função sem anotação em um dos 44 arquivos que
seguem em strict pleno (`app/schemas/article.py`), o `mypy app` volta a rc=1
(`Found 1 error in 1 file`); revertido o probe, volta a rc=0. Ou seja, código novo em
módulo **não** listado nas duas listas de overrides é cobrado de verdade.

### 6.6 Limitações — o gate de mypy é PARCIAL (declaração explícita)

- **28 de 105 arquivos (26,7%) estão fora de qualquer verificação** de mypy:
  `ignore_errors = true`. O mypy não olha o conteúdo deles.
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
  roda.

### 6.7 Pins de versão (duas fontes, uma verdade)

O step de type check é bloqueante, então a versão do `mypy` passou a ser fixa — a mesma
decisão já tomada para o `ruff` na Task 9 (que é o footgun apontado na re-review da Task 9):

| Ferramenta | `pyproject.toml` (`[project.optional-dependencies].dev`) | `requirements-dev.txt` |
|---|---|---|
| ruff | `ruff==0.16.7` | `ruff==0.16.7` |
| mypy | `mypy==2.3.1` | `mypy==2.3.1` |
