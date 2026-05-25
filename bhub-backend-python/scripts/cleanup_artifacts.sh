#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "-> Procurando diretorio {api/ ..."
BROKEN_DIR="${PROJECT_ROOT}/{api"

if [ -d "$BROKEN_DIR" ]; then
    echo "  Encontrado: $BROKEN_DIR"
    if grep -r '{api/' "${PROJECT_ROOT}/app" --include="*.py" -l 2>/dev/null; then
        echo "  Referencias encontradas; revisar antes de remover"
        exit 1
    fi
    rm -rf "$BROKEN_DIR"
    echo "  Removido"
else
    echo "  Nao encontrado"
fi

echo "-> Verificando .gitignore ..."
IGNORES=("__pycache__" "*.pyc" ".env" "venv/" ".venv/" "dist/" "*.egg-info/")
for pattern in "${IGNORES[@]}"; do
    if ! grep -qF "$pattern" "${PROJECT_ROOT}/.gitignore"; then
        echo "$pattern" >> "${PROJECT_ROOT}/.gitignore"
        echo "  Adicionado: $pattern"
    fi
done

echo "Limpeza concluida"
