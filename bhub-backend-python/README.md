# BHUB Backend — Python

> Esta é a aplicação principal do BHUB (FastAPI assíncrono: agregação de RSS,
> classificação ML, busca full-text e UI SSR via Jinja2/HTMX). **Todos os comandos
> abaixo assumem este diretório (`bhub-backend-python/`).**

A documentação canônica fica na raiz do repositório, para não duplicar conteúdo:

- 🏗️ **[Arquitetura atual](../docs/architecture/CURRENT_ARCHITECTURE.md)** — referência única (o código manda)
- 🗺️ **[Roadmap](../docs/architecture/ROADMAP.md)** — o que está declarado como trabalho aberto
- 📄 **[README do projeto](../README.md)** — visão geral, stack e instalação passo a passo
- 🤖 **[AGENTS.md](../AGENTS.md)** / **[CLAUDE.md](../CLAUDE.md)** — contexto para agentes de código, comandos (setup, run, testes, lint, migrations) e convenções
- 📚 **[docs/](../docs/README.md)** — documentação completa por categoria (arquitetura, deploy, segurança, UI/UX, …)

## Início rápido

```bash
pip install -r requirements-dev.txt
cp .env.example .env          # depois edite .env
alembic upgrade head
python scripts/create_superuser.py
uvicorn app.main:app --reload
```

Detalhes e variáveis de ambiente: ver [CLAUDE.md](../CLAUDE.md) e [docs/configuracao/GUIA_INICIO_RAPIDO.md](../docs/configuracao/GUIA_INICIO_RAPIDO.md).
