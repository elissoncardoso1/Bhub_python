# 🎨 Implementação de Open Graph Dinâmico - BHub

## 📋 Visão Geral

Este documento descreve a implementação completa de **Open Graph dinâmico** para o BHub, permitindo que links compartilhados em redes sociais (Facebook, Twitter, LinkedIn, WhatsApp) exibam previews ricos e personalizados para cada artigo científico.

## 🏗️ Arquitetura

### Stack Tecnológica

- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: Next.js 15 com App Router
- **Geração de Imagens**: Pillow (PIL)
- **Cache**: Sistema de arquivos local (pode ser migrado para CDN)

### Fluxo de Dados

```
1. Usuário compartilha link → 
2. Crawler acessa URL → 
3. Next.js SSR gera HTML com meta tags → 
4. Crawler lê Open Graph → 
5. Backend gera imagem OG sob demanda → 
6. Preview exibido na rede social
```

## 📁 Estrutura de Arquivos

### Backend

```
bhub-backend-python/
├── app/
│   ├── services/
│   │   └── opengraph_service.py    # Serviço de geração de imagens e metadados
│   └── api/
│       └── v1/
│           └── opengraph.py        # Endpoints de Open Graph
└── uploads/
    └── og_images/                  # Cache de imagens geradas
```

### Frontend

```
Frontend/
└── src/
    ├── services/
    │   └── opengraphService.ts     # Cliente para buscar metadados
    └── app/
        └── articles/
            └── [id]/
                └── page.tsx        # Página SSR com generateMetadata
```

## 🔧 Endpoints da API

### 1. Metadados JSON

```http
GET /api/v1/og/articles/{article_id}/json
```

Retorna metadados Open Graph em formato JSON.

**Resposta:**
```json
{
  "og:title": "Título do Artigo",
  "og:description": "Descrição do artigo...",
  "og:type": "article",
  "og:url": "https://bhub.com.br/articles/123",
  "og:image": "https://bhub.com.br/api/v1/og/articles/123/image",
  "og:image:width": "1200",
  "og:image:height": "630",
  "twitter:card": "summary_large_image",
  "twitter:title": "Título do Artigo",
  "twitter:description": "Descrição do artigo...",
  "article:published_time": "2024-01-15T10:00:00",
  "article:author": "Autor 1, Autor 2",
  "article:section": "ABA"
}
```

### 2. Imagem Open Graph

```http
GET /api/v1/og/articles/{article_id}/image
```

Gera e retorna imagem Open Graph (1200x630px) para o artigo.

**Headers de Resposta:**
```
Cache-Control: public, max-age=31536000, immutable
Content-Type: image/png
```

### 3. HTML com Meta Tags

```http
GET /api/v1/og/articles/{article_id}/meta
```

Retorna HTML completo com meta tags Open Graph (útil para crawlers antigos).

### 4. Regenerar Imagem

```http
POST /api/v1/og/articles/{article_id}/regenerate
```

Força regeneração da imagem (útil após atualizações no artigo).

### 5. Imagem Padrão

```http
GET /api/v1/og/default/image
```

Retorna imagem padrão Open Graph quando artigo não encontrado.

## 🎨 Geração de Imagens

### Características

- **Dimensões**: 1200x630px (padrão Open Graph)
- **Formato**: PNG
- **Cache**: Sistema de arquivos local
- **Conteúdo**:
  - Título do artigo (2 linhas máximo)
  - Abstract truncado (3 linhas máximo)
  - Categoria
  - Data de publicação
  - Branding BHub

### Cores do Tema

```python
COLORS = {
    "primary": "#0D9488",      # Teal
    "secondary": "#1E293B",     # Navy
    "background": "#FFFFFF",    # Branco
    "text": "#1E293B",          # Texto escuro
    "text_light": "#64748B",    # Texto claro
    "accent": "#F59E0B",        # Amarelo
}
```

### Cache

As imagens são geradas sob demanda e armazenadas em:
```
uploads/og_images/article_{article_id}.png
```

A regeneração ocorre quando:
- Artigo é atualizado (comparação de timestamps)
- Endpoint `/regenerate` é chamado
- Cache não existe

## 🚀 Implementação no Frontend

### SSR com Next.js

A página de artigo usa **Server-Side Rendering** para gerar meta tags dinamicamente:

```typescript
// src/app/articles/[id]/page.tsx
export async function generateMetadata({ params }: ArticlePageProps): Promise<Metadata> {
  const { id } = await params;
  const articleId = parseInt(id);

  const ogMetadata = await OpenGraphService.getArticleMetadata(articleId);
  return OpenGraphService.toNextMetadata(ogMetadata);
}
```

### Metadados Gerados

O Next.js automaticamente injeta as seguintes meta tags no `<head>`:

```html
<meta property="og:title" content="Título do Artigo" />
<meta property="og:description" content="Descrição..." />
<meta property="og:type" content="article" />
<meta property="og:url" content="https://bhub.com.br/articles/123" />
<meta property="og:image" content="https://bhub.com.br/api/v1/og/articles/123/image" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Título do Artigo" />
<meta name="twitter:description" content="Descrição..." />
<meta name="twitter:image" content="https://bhub.com.br/api/v1/og/articles/123/image" />
```

## ✅ Validação

### Ferramentas de Teste

1. **Facebook Sharing Debugger**
   - URL: https://developers.facebook.com/tools/debug/
   - Insira a URL do artigo e clique em "Debug"

2. **Twitter Card Validator**
   - URL: https://cards-dev.twitter.com/validator
   - Insira a URL do artigo

3. **LinkedIn Post Inspector**
   - URL: https://www.linkedin.com/post-inspector/
   - Insira a URL do artigo

4. **WhatsApp**
   - Compartilhe o link em uma conversa WhatsApp
   - Verifique se o preview aparece corretamente

### Checklist de Validação

- [ ] Meta tags aparecem no view-source da página
- [ ] Facebook Debugger valida corretamente
- [ ] Twitter Card Preview funciona
- [ ] LinkedIn Post Inspector aceita
- [ ] WhatsApp mostra preview
- [ ] Imagens são servidas com cache headers corretos
- [ ] Performance < 200ms para geração (após cache)
- [ ] Fallback para imagem default funciona
- [ ] Imagens têm dimensões corretas (1200x630)
- [ ] Texto não ultrapassa limites da imagem

## 🔒 Segurança e Privacidade

### Considerações

- ✅ **Dados Públicos**: Apenas artigos publicados (`is_published=True`) geram OG
- ✅ **Cache**: Imagens são públicas e cacheáveis
- ✅ **Rate Limiting**: Endpoints protegidos pelo rate limiter do FastAPI
- ✅ **Validação**: IDs de artigo são validados antes de processar

### Recomendações Futuras

- [ ] Adicionar autenticação para endpoint `/regenerate`
- [ ] Implementar CDN para imagens (CloudFlare, AWS CloudFront)
- [ ] Adicionar watermark opcional nas imagens
- [ ] Implementar compressão de imagens (WebP)

## 📊 Performance

### Métricas Esperadas

- **Primeira Geração**: ~500-1000ms (depende do servidor)
- **Cache Hit**: ~50-100ms (leitura de arquivo)
- **Tamanho Médio**: ~50-150KB por imagem PNG

### Otimizações

1. **Cache Agressivo**: Imagens são cacheadas indefinidamente
2. **Geração Assíncrona**: Pode ser movida para queue (Celery/RQ)
3. **CDN**: Recomendado para produção
4. **Compressão**: PNG otimizado com `optimize=True`

## 🛠️ Configuração

### Variáveis de Ambiente

**Backend:**
```bash
# Já configurado em app/config.py
UPLOAD_DIR=./uploads  # Diretório para cache de imagens
```

**Frontend:**
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BASE_URL=https://bhub.com.br
```

### Permissões de Diretório

Certifique-se de que o diretório de uploads tem permissões de escrita:

```bash
chmod -R 755 uploads/
```

## 🔄 Migração e Deploy

### Passo a Passo

1. **Backend**:
   ```bash
   cd bhub-backend-python
   # As dependências já estão instaladas (Pillow)
   # Apenas reinicie o servidor
   ```

2. **Frontend**:
   ```bash
   cd Frontend/workspace-2a3ac13c-ec98-4e6d-b282-2b37ac9303e6
   npm install  # Se necessário
   npm run build
   ```

3. **Teste Local**:
   ```bash
   # Backend
   uvicorn app.main:app --reload

   # Frontend
   npm run dev
   ```

4. **Validar**:
   - Acesse: http://localhost:3000/articles/1
   - Verifique view-source para meta tags
   - Teste no Facebook Debugger

## 📈 Melhorias Futuras

### Fase 2: Otimização

- [ ] Migrar cache para Redis
- [ ] Implementar CDN (CloudFlare R2, AWS S3)
- [ ] Adicionar suporte a WebP
- [ ] Implementar queue para geração assíncrona

### Fase 3: Avançado

- [ ] A/B testing de designs
- [ ] Analytics de compartilhamentos
- [ ] Personalização por rede social
- [ ] Templates customizáveis por categoria
- [ ] Suporte a múltiplos idiomas nas imagens

## 🐛 Troubleshooting

### Problema: Imagens não aparecem

**Solução:**
1. Verifique permissões do diretório `uploads/og_images/`
2. Verifique se Pillow está instalado: `pip list | grep Pillow`
3. Verifique logs do backend para erros

### Problema: Meta tags não aparecem

**Solução:**
1. Verifique se a página está usando SSR (não 'use client')
2. Verifique se `generateMetadata` está exportado
3. Verifique console do Next.js para erros

### Problema: Performance lenta

**Solução:**
1. Verifique se cache está funcionando
2. Considere usar CDN
3. Implemente queue para geração assíncrona

## 📚 Referências

- [Open Graph Protocol](https://ogp.me/)
- [Twitter Cards](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)
- [Next.js Metadata API](https://nextjs.org/docs/app/api-reference/functions/generate-metadata)
- [Pillow Documentation](https://pillow.readthedocs.io/)

## 👥 Suporte

Para dúvidas ou problemas, abra uma issue no repositório ou entre em contato com a equipe BHub.

---

**Última atualização**: Dezembro 2024
**Versão**: 1.0.0

