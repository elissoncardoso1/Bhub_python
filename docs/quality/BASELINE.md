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
| Formatter | `ruff format --check .` | **99 seriam reformatados**, 82 já formatados | **0 pendentes** (181 já formatados) |
| Tipagem | `mypy app` | **369 erros em 61 arquivos** (105 arquivos analisados) | *fora do escopo desta task* (Task 10 / T3.3) |
| Testes | `pytest tests/ -q` | **256 passed**, 0 failed | **256 passed**, 0 failed |
| Cobertura | `pytest tests/ -q --cov=app --cov-report=term` | **59%** (6359 statements, 2609 missing) | **59%** (6339 statements, 2586 missing) |

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

## 3. `per-file-ignores` adicionados (`pyproject.toml`)

```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ARG001", "ARG002", "ARG004", "ARG005"]
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
do projeto.** `ARG004` está listado por completude da família ARG nos testes (hoje sem
ocorrências nesse diretório).

## 4. `# noqa` adicionados em `app/` (com justificativa)

Nenhum outro `# noqa` foi introduzido. Cada um abaixo cobre um argumento cujo **nome faz
parte de um contrato** e que, portanto, não pode virar `_nome`:

| Arquivo | Código | Quantos | Justificativa |
|---|---|---|---|
| `app/ai/manager.py` | `ARG002` | 3 | `target_lang` implementa a interface de tradução (`BaseAIProvider.translate`) e é chamável por keyword; a assinatura é contrato entre providers. |
| `app/api/v1/ai.py` | `ARG001` | 1 | `request` é exigido pelo `slowapi` (valor padrão de `key_func` do limiter). |
| `app/api/v1/articles.py` | `ARG001` | 1 | idem: `request` exigido pelo `slowapi`. |
| `app/core/security.py` | `ARG002` | 1 | `token` é imposto pela assinatura de `BaseUserManager.on_after_forgot_password` do fastapi-users (método sobrescrito). |
| `app/services/analytics_service.py` | `ARG004` | 1 | `ip_address` é passado **por keyword** pelos chamadores (ex.: `app/core/analytics_middleware.py`). |
| `app/services/classification_service.py` | `ARG004` | 2 | `auto_created` e `db` são documentados na docstring e fazem parte da assinatura pública (chamáveis por keyword). |
| `app/services/opengraph_service.py` | `ARG002` | 2 | `bold` é passado por keyword internamente (`_load_font(48, bold=True)`); `font_name` integra a assinatura do resolvedor de fontes. |

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

### Ainda fora do escopo (tasks seguintes do Épico 3)

- `mypy` bloqueante → Task 10 (T3.3).
- Threshold de cobertura → Task 10 (T3.4).
- Build da imagem Docker no CI → Task 11 (T3.5).
