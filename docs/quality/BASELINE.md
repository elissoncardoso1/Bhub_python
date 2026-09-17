# Baseline de qualidade — BHUB Backend (Python 3.12)

> Épico 3, Tasks T3.1 (medir) + T3.2 (zerar dívida de Ruff).
> Escopo desta medição: `bhub-backend-python/` (a aplicação vive nesse subdiretório).
> Todos os comandos abaixo foram executados a partir de `bhub-backend-python/`,
> com o venv do projeto (`.venv/bin/python -m <ferramenta>`).

HEAD de referência do baseline: `c9d578a` (`docs(di): document global singleton decisions`),
árvore limpa, sem alterações pendentes.

## 1. Baseline → depois (T3.1)

| Verificação | Comando exato | Baseline (`c9d578a`) | Depois (T3.2) |
|---|---|---|---|
| Lint | `ruff check app tests` | **178 erros** | **0 erros** (`All checks passed!`) |
| Formatter | `ruff format --check .` | **99 seriam reformatados**, 82 já formatados | **0 pendentes** (179 já formatados) |
| Tipagem | `mypy app` | **369 erros em 61 arquivos** (105 arquivos analisados) | *fora do escopo desta task* (Task 10 / T3.3) |
| Testes | `pytest tests/ -q` | **256 passed**, 0 failed | **256 passed**, 0 failed |
| Cobertura | `pytest tests/ -q --cov=app --cov-report=term-missing` | **59%** (6359 statements, 2609 missing) | **59%** (6339 statements, 2586 missing) |

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
   (`dummy-variable-rgx = "^_"`), então essas linhas não suprimiam nada; e o parâmetro morto
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
do projeto.** `ARG004` foi **removido** desta lista na rodada de correção 1: não há nenhuma
ocorrência dele em `tests/` e ignore sem ocorrência é superfície morta. `ARG004` continua
sendo reportado de verdade em `app/` (2 sítios, com `# noqa` justificado — ver §4.1).

## 4. Inventário completo de `# noqa` (reescrito na rodada de correção 1)

O inventário original desta seção estava **incompleto e errado**: listava 9 sítios e
afirmava "Nenhum outro `# noqa` foi introduzido", quando o diff continha **42** linhas
`# noqa` adicionadas em `app/`. Das 42, **27 eram inócuas** (parâmetros já prefixados com
`_`, que o Ruff ignora por padrão via `dummy-variable-rgx = "^_"`), 1 mascarava um parâmetro
morto e 2 foram eliminadas movendo imports. Todo o inventário abaixo foi recontado com
`grep -rn noqa` no HEAD desta rodada e validado com o `ruff 0.16.7` (a versão do pin).

### 4.1 `# noqa` introduzidos por esta task e ainda presentes em `app/` — **12 linhas**

Cada um cobre um argumento cujo **nome faz parte de um contrato** e que, portanto, não pode
virar `_nome` (ou um import deliberadamente tardio):

| Arquivo:linha | Código | Justificativa |
|---|---|---|
| `app/ai/manager.py:286,373,449` | `ARG002` ×3 | `target_lang` implementa a interface de tradução (`BaseAIProvider.translate`, `app/interfaces/services.py`) e é chamável por keyword; a assinatura é contrato entre providers. |
| `app/api/v1/ai.py:63` | `ARG001` | `request` é exigido pelo **slowapi** por nome literal (`slowapi/extension.py`: procura um parâmetro chamado `request`); aqui ele é um `starlette.requests.Request` de verdade e é lido pelo wrapper do limiter. |
| `app/api/v1/articles.py:28` | `ARG001` | idem: `request` exigido pelo slowapi por nome literal. |
| `app/core/security.py:51` | `ARG002` | `token` é imposto pela assinatura de `BaseUserManager.on_after_forgot_password` do fastapi-users (método sobrescrito). |
| `app/services/analytics_service.py:85` | `ARG004` | `ip_address` é passado **por keyword** pelos chamadores (`app/core/analytics_middleware.py:171,184`, `app/api/v1/analytics.py:56,69,107,121`, `app/services/analytics_service.py:53`). |
| `app/services/classification_service.py:108` | `ARG004` | `auto_created` é documentado na docstring e chamado por keyword (`classification_service.py:225`: `db, slug, auto_created=True`). |
| `app/services/classification_service.py:153` | `ARG004` | `db` é documentado na docstring e chamado por keyword (`classification_service.py:73`, `background_tasks.py:48,78`). |
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
removido e agora há **dois steps bloqueantes**, ambos rodando em `bhub-backend-python`
(`defaults.run.working-directory`):

```yaml
- name: Lint (ruff check)
  run: ruff check app tests

- name: Format check (ruff format --check)
  run: ruff format --check .
```

`requirements-dev.txt` fixa `ruff==0.16.7`, a versão em que o repositório foi validado: um
`ruff format --check` bloqueante só é determinístico se a versão do formatter for fixa.
Na rodada de correção 1, o extra `dev` de `pyproject.toml` foi **alinhado ao mesmo pin**
(`ruff==0.16.7`, antes `ruff>=0.8.0`), eliminando a segunda fonte de verdade: antes,
`pip install -e ".[dev]"` podia instalar uma versão diferente da validada.

### Ainda fora do escopo (tasks seguintes do Épico 3)

- `mypy` bloqueante → Task 10 (T3.3).
- Threshold de cobertura → Task 10 (T3.4).
- Build da imagem Docker no CI → Task 11 (T3.5).
