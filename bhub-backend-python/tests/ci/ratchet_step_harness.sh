#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Harness determinístico dos steps de GATE de qualidade do CI
# (`Type check ratchet` e `Coverage floor` de .github/workflows/ci.yml).
#
# Por que ele existe
# ------------------
# O step do shadow ratchet NÃO decide pelo rc do mypy: nesta config o mypy sai
# com rc=1 por design (há 127 erros legados), então o que decide o gate é o
# TOTAL extraído da saída. Um gate que decide por texto extraído precisa falhar
# FECHADO em orçamento inválido, escopo degradado e parsing duvidoso — e foi
# exatamente aí que a rodada de correção 2 deixou 4 falsos verdes: dentro de um
# `if`, um erro de shell (ex.: comparação com `127,`) sob `bash -e` vira
# simplesmente condição falsa, o step imprime OK e sai 0.
#
# Este harness congela esse comportamento: cada cenário de falso verde que já
# existiu está aqui como caso de teste, executável sem mypy real, sem rede e
# sem GitHub Actions.
#
# Como funciona
# -------------
#   1. extrai o BLOCO `run:` REAL do step direto de .github/workflows/ci.yml
#      (dedent, verbatim — não é paráfrase do script: se o ci.yml mudar, o
#      harness passa a testar a versão nova);
#   2. põe um stub de `mypy` no PATH que imprime uma fixture sintética e sai
#      com um rc sintético (a árvore do repositório não é tocada);
#   3. executa o bloco com `bash -e` e cwd = `bhub-backend-python/`, que são o
#      shell default do GitHub Actions para `run:` e o `working-directory` do
#      workflow;
#   4. compara o rc do step com o esperado (PASS = rc 0; FAIL = rc != 0).
#
# As ÚNICAS mutações feitas no bloco extraído são as LINHAS DE DECLARAÇÃO que o
# próprio step apresenta como entrada humana — `RATCHET_BUDGET=`,
# `EXPECTED_SOURCE_FILES=` e `RATCHET_CONFIG=` (as três são fonte única no ci.yml,
# e é para poder substituí-las que existem como linha própria). NENHUMA linha de
# lógica é alterada, e um cenário que peça uma substituição que não pegue (linha
# renomeada ou removida no ci.yml) faz o harness abortar com rc=2.
#
# Cenários de cobertura (10 e 11 do brief da rodada de correção 3) executam a
# suíte REAL (~10 s cada) e por isso ficam atrás de opt-in:
#   RATCHET_HARNESS_COVERAGE=1 bash bhub-backend-python/tests/ci/ratchet_step_harness.sh
#
# Uso:  bash bhub-backend-python/tests/ci/ratchet_step_harness.sh
# Saída: 0 se TODOS os cenários EXECUTADOS baterem; 1 se algum divergir; 2 se o
#        harness não conseguir fazer o próprio trabalho (extração, stub, etc.).
#        O resumo final separa "disponíveis" de "executados": uma corrida sem
#        `RATCHET_HARNESS_COVERAGE=1` NÃO cobre o step de cobertura, e isso
#        aparece no resumo, não só numa linha fácil de passar batido.
# ---------------------------------------------------------------------------

set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
BACKEND="$ROOT/bhub-backend-python"
CI_YML="$ROOT/.github/workflows/ci.yml"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/bin" "$TMP/fixtures"

# ---------------------------------------------------------------------------
# 1. Extração verbatim do bloco `run:` do step do ratchet.
# ---------------------------------------------------------------------------
extract_run_block() {  # $1 = trecho do nome do step, $2 = arquivo de saída
  awk -v pat="$1" '
    $0 ~ ("^      - name: .*" pat) { found = 1; next }
    found && /^[[:space:]]*run: \|/ { inrun = 1; next }
    inrun {
      if ($0 ~ /^[[:space:]]*$/) { print ""; next }
      ind = match($0, /[^ ]/) - 1
      if (ind < 10) exit
      print substr($0, 11)
    }
  ' "$CI_YML" > "$2"
  [ -s "$2" ]
}

harness_fail() { echo "FALHA DO HARNESS: $*"; exit 2; }

extract_run_block "Type check ratchet" "$TMP/step.raw.sh" \
  || harness_fail "não consegui extrair o bloco run: do step do ratchet de $CI_YML"
grep -q '^RATCHET_BUDGET=' "$TMP/step.raw.sh" \
  || harness_fail "o bloco extraído do ratchet não tem a atribuição RATCHET_BUDGET — extração errada"
if grep -q '^EXPECTED_SOURCE_FILES=' "$TMP/step.raw.sh"; then
  echo "info: o step declara EXPECTED_SOURCE_FILES (gate de escopo presente)."
else
  # Aviso, não falha: o harness precisa conseguir rodar também contra a versão
  # SEM o gate de escopo — é assim que a regressão de C2 se reproduz aqui
  # (cenários 7b e 13 ficam vermelhos justamente por falta da asserção).
  echo "AVISO: o step NÃO declara EXPECTED_SOURCE_FILES — o gate de escopo do ratchet (C2) está ausente."
fi
if grep -q '^RATCHET_CONFIG=' "$TMP/step.raw.sh"; then
  echo "info: o step declara RATCHET_CONFIG (guard de ignore_errors presente)."
else
  echo "AVISO: o step NÃO declara RATCHET_CONFIG — o guard de ignore_errors (Important #2 da rodada 4) está ausente; o cenário 23 deve ficar vermelho."
fi

# ---------------------------------------------------------------------------
# 2. Stub de `mypy`: imprime a fixture e sai com o rc combinado.
# ---------------------------------------------------------------------------
cat > "$TMP/bin/mypy" <<'STUB'
#!/usr/bin/env bash
# Stub de mypy do harness. Ignora os argumentos, imprime a fixture apontada por
# MYPY_STUB_DIR e sai com MYPY_STUB_RC. Só escreve no diretório temporário do
# harness — a árvore do repositório não é tocada.
out="$MYPY_STUB_DIR/fixture.txt"
if [ ! -f "$out" ]; then
  echo "stub de mypy: fixture ausente ($out)" >&2
  exit 70
fi
cat "$out"
exit "${MYPY_STUB_RC:-0}"
STUB
chmod +x "$TMP/bin/mypy"

fixture() {  # $1 = nome, $2.. = linhas
  local name="$1"; shift
  printf '%s\n' "$@" > "$TMP/fixtures/$name"
}

fixture success_105.txt   "Success: no issues found in 105 source files"
fixture success_0.txt     "Success: no issues found in 0 source files"
fixture found_127.txt     "app/main.py:134: error: dummy legado  [arg-type]" \
                          "Found 127 errors in 28 files (checked 105 source files)"
fixture found_128.txt     "app/main.py:134: error: erro novo  [arg-type]" \
                          "Found 128 errors in 28 files (checked 105 source files)"
fixture found_999.txt     "app/main.py:134: error: legado dobrado  [arg-type]" \
                          "Found 999 errors in 28 files (checked 105 source files)"
fixture found_0_105.txt   "Found 0 errors in 28 files (checked 105 source files)"
fixture found_0_3.txt     "Found 0 errors in 3 source files"
fixture found_0_3_wc.txt  "Found 0 errors in 3 files (checked 3 source files)"
fixture found_nocount.txt "app/main.py:134: error: sem contagem  [arg-type]" \
                          "Found 127 errors in 28 files"
fixture multi_last_200.txt "Found 3 errors in 1 file (checked 105 source files)" \
                           "Found 200 errors in 28 files (checked 105 source files)"
fixture multi_last_127.txt "Found 200 errors in 28 files (checked 105 source files)" \
                           "Found 127 errors in 28 files (checked 105 source files)"
fixture empty.txt
fixture only_notes.txt     "app/ai/manager.py:35: note: By default the bodies of untyped functions are not checked  [annotation-unchecked]"
# Cenário 17: formato REAL de resumo com erro bloqueante do mypy (`mypy/util.py`:
# o sufixo `(checked N source files)` é SUBSTITUÍDO por `(errors prevented further
# checking)`). Medido com o mypy 2.3.1 do venv:
#   $ mypy <arquivo-com-syntax-error> --no-incremental
#   app/bad.py:1: error: Invalid syntax  [syntax]
#   Found 1 error in 1 file (errors prevented further checking)
# Hoje cai no fail-closed ("não consegui extrair a contagem"); o cenário congela
# esse comportamento para o dia em que alguém "consertar" o parser.
fixture blocking_summary.txt "app/bad.py:1: error: Invalid syntax  [syntax]" \
                             "Found 1 error in 1 file (errors prevented further checking)"

# ---------------------------------------------------------------------------
# 3. Executor dos cenários do ratchet.
# ---------------------------------------------------------------------------
PASSED=0
FAILED=0
SKIPPED=0
DIVERGENCES=()

mutate_line() {  # $1 = VAR, $2 = valor, $3 = nome do cenário (roda sobre $TMP/step.sh)
  # Delimitador `|` no sed: os valores usados incluem CAMINHO (`RATCHET_CONFIG=`),
  # que contém `/`. Nenhum valor de cenário contém `|` nem `&`.
  local var="$1" val="$2" name="$3"
  sed "s|^$var=.*\$|$var=$val|" "$TMP/step.sh" > "$TMP/step.mut.sh"
  if ! grep -qxF "$var=$val" "$TMP/step.mut.sh"; then
    harness_fail "cenário '$name' pediu $var='$val' e o bloco executado não tem essa declaração literal — a substituição não pegou (linha renomeada ou removida no ci.yml?)"
  fi
  mv "$TMP/step.mut.sh" "$TMP/step.sh"
}

run_step() {  # $1 = nome, $2 = fixture, $3 = rc do stub, $4 = orçamento ("-" = verbatim), $5 = esperado, $6 = overrides extras ("VAR=valor VAR2=valor2")
  local name="$1" fx="$2" stub_rc="$3" budget="$4" expected="$5" extra="${6:-}"
  local out rc got last

  cp "$TMP/fixtures/$fx" "$TMP/fixture.txt"
  cp "$TMP/step.raw.sh" "$TMP/step.sh"
  if [ "$budget" != "-" ]; then
    mutate_line RATCHET_BUDGET "$budget" "$name"
  fi
  local ovr
  for ovr in $extra; do
    mutate_line "${ovr%%=*}" "${ovr#*=}" "$name"
  done

  out=$( cd "$BACKEND" && PATH="$TMP/bin:$PATH" MYPY_STUB_DIR="$TMP" MYPY_STUB_RC="$stub_rc" \
         bash -e "$TMP/step.sh" 2>&1 )
  rc=$?
  last=$(printf '%s\n' "$out" | tail -n 1)

  if [ "$rc" -eq 0 ]; then got=PASS; else got=FAIL; fi

  if [ "$got" = "$expected" ]; then
    PASSED=$((PASSED + 1))
    printf '  ok    %-58s esperado=%-4s rc=%s  | %s\n' "$name" "$expected" "$rc" "$last"
  else
    FAILED=$((FAILED + 1))
    DIVERGENCES+=("$name: esperado=$expected rc=$rc")
    printf '  FALHA %-58s esperado=%-4s rc=%s  | %s\n' "$name" "$expected" "$rc" "$last"
    printf '        saída completa: %s\n' "$(printf '%s' "$out" | tr '\n' '|')"
  fi
}

echo "== Cenários do step 'Type check ratchet' (bloco run: verbatim de $CI_YML) =="
# --- os 11 cenários mínimos do brief da rodada de correção 3 ---
run_step "1  budget 127 + 127 erros + 105 arquivos"        found_127.txt     1 -     PASS
run_step "2  budget 127 + 128 erros + 105 arquivos"        found_128.txt     1 -     FAIL
run_step "3  budget 127, + 0 erros + 105 arquivos"         found_0_105.txt   1 "127," FAIL
run_step "4  budget 127, + 999 erros + 105 arquivos"       found_999.txt     1 "127," FAIL
run_step "5  budget vazio"                                 found_127.txt     1 ""     FAIL
run_step "6  budget não numérico (abc)"                    found_127.txt     1 "abc"  FAIL
run_step "7  0 erros + 3 source files (sem contagem)"      found_0_3.txt     1 -     FAIL
run_step "8  output sem contagem de source files"          found_nocount.txt 1 -     FAIL
run_step "9  múltiplas linhas Found (última = 200 erros)"  multi_last_200.txt 1 -    FAIL
# --- regressões e casos de borda que a rodada 2 não cobria ---
run_step "7b 0 erros + '(checked 3 source files)'"         found_0_3_wc.txt  1 -     FAIL
run_step "9b múltiplas linhas Found (última = 127 erros)"  multi_last_127.txt 1 -    PASS
run_step "12 Success em 105 source files (legado zerado)"  success_105.txt   0 -     PASS
run_step "13 Success em 0 source files (escopo colapsado)" success_0.txt     0 -     FAIL
run_step "14 rc=2 do mypy (falha de execução)"             found_127.txt     2 -     FAIL
run_step "15 saída vazia (rc=1)"                           empty.txt         1 -     FAIL
run_step "16 saída só com 'note' (rc=1)"                   only_notes.txt    1 -     FAIL
# --- rodada de correção 4 (falsos verdes fechados nesta rodada) ---
# 17: formato REAL de resumo com erro bloqueante do mypy (sem `(checked N ...)`).
run_step "17 resumo com 'errors prevented further checking'"  blocking_summary.txt 1 - FAIL
# 18-20b: MAGNITUDE dos operandos (Important #1). `^[0-9]+$` aceitava inteiro de
# tamanho arbitrário e `[ … -gt/-ne … ]` estoura o int64 (limite 2^63): o `test`
# devolve erro e, dentro de `if` sob `bash -e`, isso é condição falsa → o step saía
# 0 imprimindo OK. Medido antes da correção: budget 99999999999999999999 com
# `Found 999 errors in 28 files (checked 105 source files)` → rc=0.
run_step "18 budget 99999999999999999999 + 999 erros"      found_999.txt     1 99999999999999999999 FAIL
run_step "19 budget 9223372036854775808 (2^63) + 999"      found_999.txt     1 9223372036854775808 FAIL
run_step "19b budget 9223372036854775807 (int64 max)"      found_999.txt     1 9223372036854775807 FAIL
run_step "20 budget 999999999 (teto de 9 dígitos)"         found_127.txt     1 999999999 PASS
run_step "20b budget 1000000000 (teto + 1) + 127 erros"    found_127.txt     1 1000000000 FAIL
# 21-22: mesma classe no gate de ESCOPO, e controle do próprio mecanismo de override
# (EXPECTED_SOURCE_FILES=105 é o valor real: prova que o override não quebra o verde).
run_step "21 EXPECTED_SOURCE_FILES 99999999999999999999"   found_0_3_wc.txt  1 - FAIL "EXPECTED_SOURCE_FILES=99999999999999999999"
run_step "22 EXPECTED_SOURCE_FILES=105 (controle)"         found_127.txt     1 - PASS "EXPECTED_SOURCE_FILES=105"
# 23-24: `ignore_errors` ATIVO na config do ratchet (Important #2). `ignore_errors`
# NÃO reduz `(checked N source files)` (segue 105), então o gate de ESCOPO passa e o
# total vira 0: sem o guard o step sairia verde com o shadow ratchet anulado. O
# cenário 23 usa uma cópia degradada em $TMP (árvore intocada); o 24 é o controle com
# o arquivo REAL, que cita `ignore_errors` só em COMENTÁRIOS e tem de continuar verde.
DEGRADED_CFG="$TMP/degraded.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$DEGRADED_CFG"
cat >> "$DEGRADED_CFG" <<'DEGRADED'

# --- bloco ATIVO injetado pelo harness (não existe no arquivo real) ---------
# Este arquivo SEGUE citando `ignore_errors` em comentários (acima): o guard do
# step tem de ler só a CHAVE ativa, nunca a menção em comentário.
[[tool.mypy.overrides]]
module = [
    "app.web.routes",
]
ignore_errors = true
DEGRADED
run_step "23 config do ratchet com ignore_errors ATIVO"    success_105.txt   0 - FAIL "RATCHET_CONFIG=$DEGRADED_CFG"
run_step "24 config real do ratchet (só comentários)"      found_127.txt     1 - PASS "RATCHET_CONFIG=pyproject.ratchet.toml"
# 25: mesma chave em TOML de tabela inline (uma linha só) — o guard não pode depender
# de a chave começar a linha.
DEGRADED_INLINE_CFG="$TMP/degraded-inline.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$DEGRADED_INLINE_CFG"
printf '\n[tool.mypy]\noverrides = [{ module = ["app.web.routes"], ignore_errors = true }]\n' >> "$DEGRADED_INLINE_CFG"
run_step "25 ignore_errors em tabela inline (1 linha)"     success_105.txt   0 - FAIL "RATCHET_CONFIG=$DEGRADED_INLINE_CFG"
# 26: CONTROLE NEGATIVO do guard — config com módulo cujo NOME contém o texto
# `ignore_errors` e com comentário citando a chave: isso NÃO é a chave ativa, e o
# step tem de continuar verde (o guard não pode reprovar por substring).
KNOWNFALSE_CFG="$TMP/other.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$KNOWNFALSE_CFG"
printf '\n# um modulo cujo nome apenas CONTEM o texto: app.ignore_errors_shim\nignore_errors_note = "citado em comentario acima; chave real ausente"\n' >> "$KNOWNFALSE_CFG"
run_step "26 controle: nome/valor com o texto, sem a chave" found_127.txt    1 - PASS "RATCHET_CONFIG=$KNOWNFALSE_CFG"
# --- rodada de correção 5 ---
# 27-29: a chave CITADA. `"ignore_errors"` (aspas duplas) e `'ignore_errors'` (aspas
# simples) são o MESMO nome em TOML, e o mypy as HONRA: medido com o mypy real do venv
# (2.3.1), o bloco citado aplicado aos 5 módulos de maior contagem derruba o total de
# 127 para 60 (36+18+11+1+1 = 67 do §6.3 da BASELINE) mantendo `(checked 105 source
# files)` intacto. O guard da rodada 4 — `(^|[[:space:],{])ignore_errors[[:space:]]*=`,
# com o token precedido de aspas — NÃO casava a linha e o step saía VERDE (rc=0) com o
# ratchet anulado (rodada de correção 5 / Important #1). A tabela inline com a chave
# citada era cega pelo mesmo motivo.
DEGRADED_DQ_CFG="$TMP/degraded-doublequote.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$DEGRADED_DQ_CFG"
cat >> "$DEGRADED_DQ_CFG" <<'DQ'

# --- chave ATIVA com aspas duplas (injetada pelo harness) -------------------
[[tool.mypy.overrides]]
module = [
    "app.web.routes",
]
"ignore_errors" = true
DQ
run_step "27 ignore_errors com aspas duplas (ativo)"       success_105.txt   0 - FAIL "RATCHET_CONFIG=$DEGRADED_DQ_CFG"

DEGRADED_SQ_CFG="$TMP/degraded-singlequote.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$DEGRADED_SQ_CFG"
cat >> "$DEGRADED_SQ_CFG" <<'SQ'

# --- chave ATIVA com aspas simples (injetada pelo harness) ------------------
[[tool.mypy.overrides]]
module = [
    'app.web.routes',
]
'ignore_errors' = true
SQ
run_step "28 ignore_errors com aspas simples (ativo)"      success_105.txt   0 - FAIL "RATCHET_CONFIG=$DEGRADED_SQ_CFG"

# 29: o mesmo nome, citado, dentro de TOML de tabela inline (uma linha só).
DEGRADED_INLINE_Q_CFG="$TMP/degraded-inline-quoted.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$DEGRADED_INLINE_Q_CFG"
printf '\n[tool.mypy]\noverrides = [{ module = ["app.web.routes"], "ignore_errors" = true }]\n' >> "$DEGRADED_INLINE_Q_CFG"
run_step "29 chave citada em tabela inline (ativo)"        success_105.txt   0 - FAIL "RATCHET_CONFIG=$DEGRADED_INLINE_Q_CFG"

# 30-31: CONTROLE DE VALOR (rodada de correção 5 / Important #2). `ignore_errors = false`
# é o DEFAULT do mypy, não uma relaxação: medido com o mypy real do venv, a config com a
# chave em `false` mede EXATAMENTE os mesmos 127 erros / 28 arquivos / checked 105 do
# arquivo sem ela. O guard da rodada 4 rejeitava esse estado legítimo com uma mensagem
# FALSA ("tem a chave ATIVA … o total vira 0"); o guard novo exige o valor `true`.
# 30 = chave bare em `false`; 31 = chave CITADA em `false` (as duas correções juntas:
# citar a chave e exigir o valor são checagens independentes).
DEGRADED_FALSE_CFG="$TMP/degraded-false.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$DEGRADED_FALSE_CFG"
cat >> "$DEGRADED_FALSE_CFG" <<'FALSE'

# --- chave INERTE (valor default false; injetada pelo harness) --------------
[[tool.mypy.overrides]]
module = [
    "app.web.routes",
]
ignore_errors = false
FALSE
run_step "30 ignore_errors = false (inerte, nao rejeitar)" found_127.txt     1 - PASS "RATCHET_CONFIG=$DEGRADED_FALSE_CFG"

DEGRADED_FALSE_Q_CFG="$TMP/degraded-false-quoted.ratchet.toml"
cp "$BACKEND/pyproject.ratchet.toml" "$DEGRADED_FALSE_Q_CFG"
printf '\n[tool.mypy]\noverrides = [{ module = ["app.web.routes"], "ignore_errors" = false }]\n' >> "$DEGRADED_FALSE_Q_CFG"
run_step "31 chave citada = false (inerte, nao rejeitar)"  found_127.txt     1 - PASS "RATCHET_CONFIG=$DEGRADED_FALSE_Q_CFG"

# ---------------------------------------------------------------------------
# 4. Cenários de cobertura (opt-in: rodam a suíte REAL).
# ---------------------------------------------------------------------------
if [ "${RATCHET_HARNESS_COVERAGE:-0}" = "1" ]; then
  echo
  echo "== Cenários do step 'Coverage floor' (suíte real, ~10 s por cenário) =="
  extract_run_block "Coverage floor" "$TMP/cov.raw.sh" \
    || harness_fail "não consegui extrair o bloco run: do step de cobertura de $CI_YML"
  grep -q -- '--cov-fail-under=' "$TMP/cov.raw.sh" \
    || harness_fail "o bloco extraído da cobertura não tem --cov-fail-under — extração errada"

  run_coverage() {  # $1 = nome, $2 = fail-under substituto ("-" = verbatim), $3 = esperado
    local name="$1" thresh="$2" expected="$3" out rc got last
    if [ "$thresh" = "-" ]; then
      cp "$TMP/cov.raw.sh" "$TMP/cov.sh"
    else
      sed "s/--cov-fail-under=[0-9.]*/--cov-fail-under=$thresh/" "$TMP/cov.raw.sh" > "$TMP/cov.sh"
      cmp -s "$TMP/cov.sh" "$TMP/cov.raw.sh" \
        && harness_fail "cenário '$name' pediu fail-under '$thresh' e a substituição não pegou"
    fi
    out=$( cd "$BACKEND" && PATH="$BACKEND/.venv/bin:$TMP/bin:$PATH" \
           bash -e "$TMP/cov.sh" 2>&1 )
    rc=$?
    last=$(printf '%s\n' "$out" | tail -n 1)
    if [ "$rc" -eq 0 ]; then got=PASS; else got=FAIL; fi
    if [ "$got" = "$expected" ]; then
      PASSED=$((PASSED + 1))
      printf '  ok    %-58s esperado=%-4s rc=%s  | %s\n' "$name" "$expected" "$rc" "$last"
    else
      FAILED=$((FAILED + 1))
      DIVERGENCES+=("$name: esperado=$expected rc=$rc")
      printf '  FALHA %-58s esperado=%-4s rc=%s  | %s\n' "$name" "$expected" "$rc" "$last"
    fi
  }

  run_coverage "10 cobertura real >= piso do ci.yml"        -       PASS
  run_coverage "11 cobertura real < piso (piso 60)"         60      FAIL
else
  SKIPPED=2
  echo
  echo "== Cenários 10/11 (cobertura real) NÃO EXECUTADOS: 2 cenário(s) disponíveis ficaram de fora desta corrida =="
  echo "== rode com RATCHET_HARNESS_COVERAGE=1 para executá-los =="
fi

# ---------------------------------------------------------------------------
echo
echo "Resumo: $((PASSED + FAILED + SKIPPED)) cenário(s) disponíveis, $((PASSED + FAILED)) executado(s) — $PASSED ok, $FAILED divergência(s), $SKIPPED pulado(s)."
if [ "$FAILED" -gt 0 ]; then
  echo "Divergências:"
  printf '  - %s\n' "${DIVERGENCES[@]}"
  exit 1
fi
if [ "$SKIPPED" -gt 0 ]; then
  echo "ATENÇÃO: $SKIPPED cenário(s) de cobertura NÃO foram executados nesta corrida — o verde acima NÃO cobre o step 'Coverage floor'."
fi
exit 0
