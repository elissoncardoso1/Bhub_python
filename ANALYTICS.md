# Sistema de Analytics - BHUB

## Visão Geral

O sistema de analytics do BHUB foi implementado seguindo as melhores práticas de privacidade e transparência. Ele coleta dados agregados e anônimos para melhorar a experiência do usuário e entender o uso da plataforma.

## Características Principais

### ✅ Privacidade e Transparência
- **Dados Anônimos**: Não coletamos informações pessoais identificáveis
- **Respeito ao Do Not Track**: O sistema respeita o header DNT do navegador
- **Agregação de Dados**: Dados são agregados e não rastreiam usuários individuais
- **Transparência**: Aviso claro sobre coleta de dados no painel de admin

### 📊 Métricas Coletadas

1. **Tráfego**
   - Total de sessões
   - Visitantes únicos
   - Visualizações de página
   - Duração média das sessões

2. **Conteúdo**
   - Visualizações de artigos
   - Downloads de artigos
   - Buscas realizadas

3. **Eventos**
   - Page views
   - Visualizações de artigos
   - Downloads
   - Buscas
   - Cliques em categorias/autores
   - E outros eventos customizados

## Estrutura Técnica

### Backend

#### Modelos de Dados
- `AnalyticsEvent`: Eventos individuais de analytics
- `AnalyticsSession`: Sessões de usuários
- `AnalyticsMetric`: Métricas agregadas por período

#### Middleware Automático
O middleware `AnalyticsMiddleware` captura automaticamente:
- Todas as requisições HTTP (exceto rotas excluídas)
- Page views
- Requisições da API

#### Endpoints

**Públicos (para tracking):**
- `POST /api/v1/analytics/track` - Registrar evento customizado
- `POST /api/v1/analytics/pageview` - Registrar visualização de página

**Admin (para visualização):**
- `GET /api/v1/admin/analytics/overview` - Visão geral completa
- `GET /api/v1/admin/analytics/traffic` - Estatísticas de tráfego
- `GET /api/v1/admin/analytics/content` - Estatísticas de conteúdo
- `GET /api/v1/admin/analytics/events` - Estatísticas de eventos
- `GET /api/v1/admin/analytics/time-series` - Dados de série temporal
- `GET /api/v1/admin/analytics/top-pages` - Páginas mais visitadas

### Frontend

#### Serviços
- `AnalyticsService`: Serviço principal para comunicação com a API
- Métodos públicos para tracking de eventos
- Gerenciamento automático de session_id via cookies

#### Hooks
- `useAnalytics()`: Hook para tracking automático de page views
- `useTrackEvent()`: Hook para tracking de eventos customizados

#### Componentes
- `AnalyticsProvider`: Provider que rastreia automaticamente page views
- `AnalyticsCharts`: Componentes de visualização com gráficos (Recharts)
- `AnalyticsCards`: Cards com métricas principais

#### Páginas
- `/admin/analytics`: Página dedicada de analytics com visualizações completas

## Configuração

### Backend

No arquivo `.env` ou variáveis de ambiente:

```env
# Habilitar/desabilitar analytics
ENABLE_ANALYTICS=true

# Respeitar Do Not Track header
ANALYTICS_RESPECT_DNT=true
```

### Frontend

O tracking é automático através do `AnalyticsProvider` no layout principal.

## Uso

### Tracking Automático

O sistema rastreia automaticamente:
- Todas as navegações de página (via `AnalyticsProvider`)
- Requisições HTTP (via middleware do backend)

### Tracking Manual

Para eventos customizados, use o hook `useTrackEvent`:

```typescript
import { useTrackEvent } from '@/hooks/use-analytics';

function MyComponent() {
  const { trackArticleView, trackSearch } = useTrackEvent();

  const handleArticleClick = (articleId: number, title: string) => {
    trackArticleView(articleId, title);
  };

  const handleSearch = (query: string, resultsCount: number) => {
    trackSearch(query, resultsCount);
  };
}
```

### Visualização no Admin

1. Acesse `/admin/analytics` no painel de administração
2. Selecione o período desejado (7, 30, 90 dias ou 1 ano)
3. Visualize:
   - Cards com métricas principais
   - Gráficos de série temporal
   - Top páginas visitadas
   - Distribuição de eventos por tipo

## Migração do Banco de Dados

Execute a migração para criar as tabelas de analytics:

```bash
cd bhub-backend-python
alembic upgrade head
```

Isso criará as seguintes tabelas:
- `analytics_events`
- `analytics_sessions`
- `analytics_metrics`

## Privacidade e Conformidade

### LGPD/GDPR
- ✅ Dados anônimos e agregados
- ✅ Respeito ao Do Not Track
- ✅ Transparência sobre coleta de dados
- ✅ Não compartilhamento com terceiros
- ✅ Dados armazenados localmente

### Boas Práticas Implementadas
1. **Minimização de Dados**: Apenas dados essenciais são coletados
2. **Anonimização**: Session IDs não são vinculados a usuários identificáveis
3. **Transparência**: Aviso claro sobre coleta de dados
4. **Controle do Usuário**: Respeito ao DNT header
5. **Segurança**: Dados armazenados de forma segura no banco de dados

## Manutenção

### Limpeza de Dados Antigos

Recomenda-se implementar um job periódico para limpar dados antigos (ex: > 1 ano) para manter o banco de dados otimizado.

### Otimização

As tabelas possuem índices otimizados para consultas frequentes:
- Índices em `session_id`, `user_id`, `event_type`, `timestamp`
- Índices compostos para consultas por tipo e período

## Troubleshooting

### Analytics não está funcionando

1. Verifique se `ENABLE_ANALYTICS=true` no backend
2. Verifique se o middleware está registrado no `main.py`
3. Verifique os logs do backend para erros
4. Verifique se as tabelas foram criadas (migração executada)

### Dados não aparecem no painel

1. Verifique se há eventos sendo registrados no banco de dados
2. Verifique se o período selecionado contém dados
3. Verifique a autenticação do admin
4. Verifique os logs do console do navegador

## Melhorias Futuras

- [ ] Exportação de relatórios em PDF/CSV
- [ ] Filtros avançados por período, tipo de evento, etc.
- [ ] Comparação de períodos
- [ ] Alertas e notificações baseadas em métricas
- [ ] Dashboard em tempo real (WebSocket)
- [ ] Análise de funil de conversão
- [ ] Heatmaps de cliques

