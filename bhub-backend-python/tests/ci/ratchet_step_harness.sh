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
# A ÚNICA mutação feita no bloco extraído é a substituição da linha de
# atribuição do orçamento (`RATCHET_BUDGET=<n>`), usada pelos cenários de
# orçamento inválido. Nada mais é alterado — e o harness falha alto se a
# substituição não pegar.
#
# Cenários de cobertura (10 e 11 do brief da rodada de correção 3) executam a
# suíte REAL (~10 s cada) e por isso ficam atrás de opt-in:
#   RATCHET_HARNESS_COVERAGE=1 bash bhub-backend-python/tests/ci/ratchet_step_harness.sh
#
# Uso:  bash bhub-backend-python/tests/ci/ratchet_step_harness.sh
# Saída: 0 se TODOS os cenários baterem; 1 se algum divergir; 2 se o harness
#        não conseguir fazer o próprio trabalho (extração, stub, etc.).
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

# ---------------------------------------------------------------------------
# 3. Executor dos cenários do ratchet.
# ---------------------------------------------------------------------------
PASSED=0
FAILED=0
DIVERGENCES=()

run_step() {  # $1 = nome, $2 = fixture, $3 = rc do stub, $4 = orçamento ("-" = verbatim), $5 = esperado
  local name="$1" fx="$2" stub_rc="$3" budget="$4" expected="$5"
  local out rc got last

  cp "$TMP/fixtures/$fx" "$TMP/fixture.txt"
  if [ "$budget" = "-" ]; then
    cp "$TMP/step.raw.sh" "$TMP/step.sh"
  else
    sed "s/^RATCHET_BUDGET=[0-9]*\$/RATCHET_BUDGET=$budget/" "$TMP/step.raw.sh" > "$TMP/step.sh"
    if cmp -s "$TMP/step.sh" "$TMP/step.raw.sh"; then
      harness_fail "cenário '$name' pediu orçamento '$budget' e a substituição da linha RATCHET_BUDGET não pegou"
    fi
  fi

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
  echo
  echo "== Cenários 10/11 (cobertura real) PULADOS — rode com RATCHET_HARNESS_COVERAGE=1 =="
fi

# ---------------------------------------------------------------------------
echo
echo "Resumo: $PASSED cenário(s) ok, $FAILED divergência(s)."
if [ "$FAILED" -gt 0 ]; then
  echo "Divergências:"
  printf '  - %s\n' "${DIVERGENCES[@]}"
  exit 1
fi
if [ "${RATCHET_HARNESS_COVERAGE:-0}" != "1" ]; then
  echo "(cenários 10/11 de cobertura NÃO foram executados nesta corrida)"
fi
exit 0
