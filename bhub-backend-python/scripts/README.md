# Scripts de Seed e Manutenção

Este diretório contém scripts utilitários para popular e manter o banco de dados.

## Scripts Disponíveis

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

