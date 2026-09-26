# Scripts de Seed e Manutenção

Este diretório contém scripts utilitários para popular e manter o banco de dados.

## Scripts Disponíveis

### `add_journal_feeds.py`

Cadastra os feeds de **periódicos científicos** (diferente de `seed_feeds.py`, que
cadastra blogs e portais de notícias).

#### Uso

```bash
python -m scripts.add_journal_feeds
```

#### O que faz

Upsert idempotente dos 11 periódicos: casa o registro existente por `issn` (feeds do
Crossref) ou `feed_url` (feeds RSS), insere o que falta e corrige o que está defasado —
inclusive a via de ingestão. Rodar duas vezes não duplica nada.

Duas vias de ingestão, decididas no ADR-0007:

- **`CROSSREF`** — editoras que servem o RSS atrás de anti-bot (Wiley, Taylor & Francis,
  Springer). A fonte é a API REST do Crossref, consultada por ISSN.
- **`RSS`** — periódicos cujo feed da editora funciona (OJS, WordPress).

### `validate_journal_issn.py`

Valida ISSNs ao vivo contra o Crossref **antes** de cadastrá-los.

```bash
python -m scripts.validate_journal_issn 1938-3703 2196-8934
python -m scripts.validate_journal_issn --all
```

Um ISSN errado produz um feed silenciosamente vazio — o modo de falha que o ADR-0006
combate. Sem argumentos o exit code é 1 quando algum ISSN falha, para uso em CI.

> **Atenção:** validar retorna sucesso para *qualquer* ISSN registrado no Crossref. Um
> ISSN de outra revista passa no teste. Confira sempre o título devolvido contra o
> periódico esperado.

### `migrate_journal_feeds_to_crossref.py`

Converte os periódicos já cadastrados em produção para a ingestão via Crossref.

```bash
# Simula e faz rollback (padrão)
python -m scripts.migrate_journal_feeds_to_crossref

# Aplica
python -m scripts.migrate_journal_feeds_to_crossref --apply
```

Idempotente. Não faz nenhuma requisição externa: valide os ISSNs antes, num passo
separado. **Faça backup do banco antes de `--apply`.**

### `e2e_crossref_sync.py`

Teste ponta a ponta do pipeline Crossref contra banco real e API real: cria o feed,
sincroniza, confere os artigos gravados, verifica a deduplicação e limpa o que criou.

```bash
docker run --rm --network <net> -v "$PWD:/app" -w /app \
  -e DATABASE_URL='postgresql+asyncpg://...' \
  --entrypoint python bhub-backend-python-backend:latest scripts/e2e_crossref_sync.py
```

### `smoke_crossref.py` e `probe_corrections.py`

Diagnóstico de rede do adaptador. `smoke_crossref.py` exercita `validate_issn`,
`fetch_works` e `work_to_entry`. `probe_corrections.py` imprime os títulos de
correção/retratação conforme publicados no Crossref, para manter o filtro de títulos
descartáveis alinhado com a realidade.

### `seed_feeds.py`

Script para popular o banco de dados com feeds RSS do projeto Meridiano.

#### Uso

```bash
# A partir do diretório raiz do projeto
python -m scripts.seed_feeds

# Ou diretamente
cd scripts
python seed_feeds.py
```

#### O que faz

1. Inicializa o banco de dados (cria tabelas se necessário)
2. Lê a lista de feeds RSS organizados por categoria
3. Cria ou atualiza feeds no banco de dados
4. Organiza feeds por tipo (Internacional/Brasileira)
5. Configura frequência de sincronização apropriada

#### Feeds Incluídos

- **ABA Internacional**: 15 feeds de fontes internacionais
- **ABA Brasileira**: 14 feeds de fontes brasileiras

Total: **29 feeds RSS** configurados e prontos para sincronização.

## Classificação Automática

Os artigos são automaticamente classificados em categorias quando sincronizados:

### Categorias Disponíveis

1. **Clínica** - Prática clínica em ABA
2. **Educação** - Aplicações educacionais
3. **Organizacional** - ABA em contextos organizacionais
4. **Pesquisa** - Pesquisa básica e conceitual
5. **Autismo** - Artigos sobre autismo e TEA
6. **Notícias** - Notícias e atualidades
7. **Outros** - Artigos que não se enquadram nas outras categorias

### Como Funciona

1. **Classificação ML**: Usa embeddings (sentence-transformers) para classificar baseado em título, abstract e keywords
2. **Fallback Heurístico**: Se ML não estiver disponível, usa keywords simples
3. **Confiança**: Cada classificação inclui um score de confiança (0-1)

### Melhorias Futuras

- Treinar modelo específico para ABA
- Adicionar mais categorias conforme necessário
- Melhorar keywords para classificação heurística

## Próximos Passos

Após executar o seed:

1. **Sincronizar feeds**: Use a API ou scheduler para sincronizar os feeds
2. **Verificar classificação**: Revise artigos classificados e ajuste se necessário
3. **Monitorar**: Acompanhe logs e estatísticas de sincronização

## Troubleshooting

### Erro: "Module not found"
- Certifique-se de estar no ambiente virtual correto
- Instale dependências: `pip install -r requirements.txt`

### Erro: "Database not initialized"
- Execute o seed novamente (ele inicializa o banco automaticamente)

### Feeds não sincronizam
- Verifique se os feeds estão ativos no banco
- Verifique logs para erros de conexão
- Alguns feeds podem estar temporariamente indisponíveis

