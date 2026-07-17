# Privacidade e Consentimento de Cookies

Documentação técnica da camada de consentimento de cookies (LGPD) do BHUB: como o
consentimento é armazenado e validado, como ele controla o analytics interno, e como
estender ou testar o sistema.

Código de referência:

- [`app/core/cookie_consent.py`](../../bhub-backend-python/app/core/cookie_consent.py) — fonte única de parsing/serialização do cookie `bhub_consent`
- [`app/core/analytics_middleware.py`](../../bhub-backend-python/app/core/analytics_middleware.py) — gate de coleta automática
- [`app/api/v1/analytics.py`](../../bhub-backend-python/app/api/v1/analytics.py) — gate dos endpoints `/track` e `/pageview`
- [`app/web/consent.py`](../../bhub-backend-python/app/web/consent.py) — rota SSR `POST /cookie-consent`
- [`app/api/v1/cookie_consent.py`](../../bhub-backend-python/app/api/v1/cookie_consent.py) — rota `GET /api/v1/cookie-consent`
- [`app/templates/components/cookie_consent.html`](../../bhub-backend-python/app/templates/components/cookie_consent.html) — banner + central de preferências
- [`app/static/js/cookie-consent.js`](../../bhub-backend-python/app/static/js/cookie-consent.js) — JS mínimo (abre/fecha o `<dialog>`)

---

## 1. Visão geral

O consentimento do visitante é representado por **um único cookie**, `bhub_consent`
(JSON, HttpOnly, `SameSite=Lax`, 180 dias, ≤1 KB). Nenhum outro módulo do backend
interpreta esse cookie diretamente — todo acesso passa por
`app/core/cookie_consent.py`, que é a fonte única de verdade.

Fluxo:

```
Visitante decide (banner / central de preferências)
        ↓
POST /cookie-consent (app/web/consent.py) — grava bhub_consent via set_consent_cookie()
        ↓
Requisições seguintes chegam com o cookie bhub_consent
        ↓
app/core/cookie_consent.py: parse_consent_cookie() → ConsentState (validação estrita)
        ↓
Gates consultam is_granted(request, categoria):
  • AnalyticsMiddleware (app/core/analytics_middleware.py) — coleta automática de page views
  • /api/v1/analytics/track e /pageview (app/api/v1/analytics.py) — _analytics_allowed()
  • Templates — consent_state(request) (Jinja) para renderização condicional
```

**Regra de ouro do analytics**: um evento só é coletado se **todas** as condições
abaixo forem verdadeiras, avaliadas nesta ordem (tanto no middleware quanto nos
endpoints `/track`/`/pageview`, que reimplementam o mesmo gate como
`_analytics_allowed`):

1. `settings.enable_analytics` é `true` (config do servidor — **default `false`**);
2. `settings.analytics_respect_dnt` é `true` **implica** que o header `DNT: 1` não
   esteja presente na requisição;
3. `is_granted(request, "analytics")` — o visitante autorizou a categoria
   "analytics" no cookie `bhub_consent` **na versão atual** da política;
4. a rota não está em `EXCLUDED_PREFIXES` (só se aplica ao `AnalyticsMiddleware`,
   que rastreia qualquer rota da aplicação — os endpoints `/track`/`/pageview` não
   precisam dessa checagem porque só existem para esse fim).

Faltando qualquer uma, nada é coletado e nenhum cookie de sessão de analytics
(`analytics_session_id`) é criado.

O cookie `bhub_consent` guarda **apenas flags booleanas por categoria + versão +
timestamp**. Nunca é armazenado nome, e-mail, IP, id de usuário, fingerprint ou
token — essa é uma invariante reforçada por comentário no próprio módulo
(`app/core/cookie_consent.py:5-6`).

### Categorias

- `necessary` — fixa, sempre `true`, não aparece no cookie (é implícita).
- `analytics`, `external_media`, `marketing` — opcionais, em
  `OPTIONAL_CATEGORIES`; só `analytics` tem uso real hoje.

### Validação estrita (`parse_consent_cookie`)

Qualquer anomalia faz o cookie ser tratado como "não decidido" (`ConsentState()`
default, `decided=False`) — o que reabre o banner e nega todas as categorias
opcionais:

- cookie ausente ou maior que 1024 bytes;
- JSON inválido ou não é um objeto;
- alguma categoria opcional não é um `bool`;
- `version` ausente ou não é `str`;
- `version` **diferente** de `settings.cookie_consent_version` — este é o
  mecanismo de "renovação de consentimento": basta subir a versão configurada
  para invalidar todas as escolhas anteriores (ver seção 6).

---

## 2. Cookies do BHUB

Tabela idêntica à publicada em `/cookies` (fonte:
[`app/templates/pages/cookies.html`](../../bhub-backend-python/app/templates/pages/cookies.html)).
Nenhum cookie de terceiros é definido pela plataforma.

| Nome | Categoria | Finalidade | Duração | Desativável |
|---|---|---|---|---|
| `access_token` | Necessário | Mantém a sessão autenticada (JWT) de usuários administrativos. | 15 minutos | Não |
| `refresh_token` | Necessário | Permite renovar a sessão autenticada sem exigir novo login. | 7 dias | Não |
| `csrf_token` | Necessário | Protege formulários e requisições contra ataques CSRF. | 24 horas | Não |
| `bhub_consent` | Necessário | Guarda a escolha de preferências de cookies do visitante. | 180 dias | Não (é o próprio registro do consentimento) |
| `analytics_session_id` | Analytics | Identificador de sessão aleatório para métricas de uso agregadas, sem ligação com a identidade do visitante. | 30 dias | Sim |

`analytics_session_id` só é criado depois que o visitante autoriza a categoria
Analytics (via banner ou central de preferências) — nunca antes. Ao revogar o
consentimento (`action=revoke`) ou recusar/desmarcar a categoria "analytics"
(`action=reject_all` ou `save` sem o checkbox), `app/web/consent.py` apaga o
cookie `analytics_session_id` explicitamente (`response.delete_cookie(...)`),
além de gravar a nova escolha em `bhub_consent`.

---

## 3. Dados coletados pelo analytics (quando autorizado)

Quando a regra de ouro (seção 1) é satisfeita, `AnalyticsMiddleware._track_request`
(ou os endpoints `/api/v1/analytics/track` e `/pageview`) registram um evento com:

- **Caminho** da requisição (`request.url.path`) e método HTTP;
- **Referrer** (`Referer`/`Referrer` header);
- **User agent** bruto — usado apenas para derivar `device_type` (mobile/tablet/
  desktop), `browser` (Chrome/Firefox/Safari/Edge/Opera) e `os` (Windows/macOS/
  Linux/Android/iOS) via `AnalyticsService._parse_user_agent`
  (`app/services/analytics_service.py`); o texto bruto do UA também é persistido
  no evento/sessão;
- **IP anonimizado** — `anonymize_ip()` (`app/core/ip_anonymization.py`) é aplicado
  sempre que `should_anonymize_ip()` for verdadeiro (comportamento padrão de
  compliance LGPD/GDPR); o IP bruto nunca é gravado nesse caminho quando a
  anonimização está ativa;
- **Session id aleatório** — `secrets.token_urlsafe(24)`
  (`AnalyticsService.generate_session_id`), **sem** IP, usuário ou timestamp
  embutidos — não é reversível para identificar o visitante;
- Código de status e duração da requisição (apenas para requisições
  bem-sucedidas, `status_code < 400`).

### O que NUNCA é rastreado

Independente de consentimento, as rotas em `EXCLUDED_PREFIXES`
(`app/core/analytics_middleware.py`) nunca passam pelo `AnalyticsMiddleware`:

```
/admin, /login, /logout, /api/v1/auth, /api/v1/contact, /contact, /health,
/docs, /redoc, /openapi.json, /static, /api/v1/analytics,
/api/v1/cookie-consent, /cookie-consent, /privacy, /cookies, /terms
```

A comparação é por prefixo seguro (`path == p or path.startswith(p + "/")`), então
`/contact` exclui `/contact/obrigado` mas não afeta `/contatos`. Isso cobre, em
particular, toda a área administrativa, fluxos de autenticação, o formulário de
contato e as próprias páginas/rotas de privacidade — nenhuma delas gera evento de
analytics mesmo com consentimento concedido.

---

## 4. Como testar o consentimento

### Manualmente

1. Abra uma **janela anônima/privada** do navegador e acesse o site — o banner
   deve aparecer (nenhum cookie `bhub_consent` ainda).
2. Nas DevTools → Application/Storage → Cookies, confirme:
   - sem decisão: nenhum `bhub_consent`;
   - após "Aceitar opcionais": `bhub_consent` com `analytics: true` e, na próxima
     navegação, `analytics_session_id` aparece;
   - após "Recusar opcionais" ou revogar: `bhub_consent` com `analytics: false`
     (ou ausente, se revogado) e `analytics_session_id` removido.
3. Teste com JavaScript desabilitado: os botões "Aceitar opcionais" e "Recusar
   opcionais" continuam funcionando (são `<form>` HTML puro submetendo para
   `POST /cookie-consent`); apenas o botão "Configurar" (abre o `<dialog>`) exige
   JS.
4. Envie o header `DNT: 1` (extensão de navegador ou DevTools → Network
   conditions) com `ENABLE_ANALYTICS=true` e consentimento concedido — nenhum
   evento deve ser gravado.

### Automatizado

```bash
cd bhub-backend-python
pytest tests/test_cookie_consent_unit.py -v       # parsing/validação do cookie, session id
pytest tests/test_cookie_consent_endpoints.py -v  # POST/GET /cookie-consent, CSRF, _safe_next
pytest tests/test_analytics_consent_gate.py -v    # regra de ouro do gate (middleware + API)
pytest tests/test_legal_pages.py -v               # banner, footer, /privacy, /cookies, /terms, contato
```

Para rodar a suíte completa do backend:

```bash
python -m pytest tests/ --ignore=tests/test_ai_minimal.py
```

(o `--ignore` evita uma falha de import pré-existente de `llama_cpp` em ambientes
sem essa dependência instalada, não relacionada à camada de privacidade) — a
suíte deve ficar toda verde.

---

## 5. Como habilitar analytics em desenvolvimento

1. No `.env`, defina `ENABLE_ANALYTICS=true` (default é `false` — analytics vem
   **desligado** por padrão, mesmo em produção, até decisão explícita de
   habilitar).
2. Reinicie a aplicação.
3. Acesse o site e **aceite** a categoria "Analytics" no banner ou na central de
   preferências — a config habilitada não substitui nem ignora a escolha do
   visitante; ela apenas define se o gate *pode* coletar quando o consentimento
   permitir.
4. Confirme em `/api/v1/cookie-consent` (JSON, `Cache-Control: no-store`) que
   `analytics: true`, e que `analytics_session_id` passa a ser definido nas
   respostas seguintes.

`ANALYTICS_RESPECT_DNT=true` (default) continua valendo mesmo em desenvolvimento
— um `DNT: 1` no navegador bloqueia a coleta independentemente do consentimento.

---

## 6. Como mudar a versão do consentimento

`COOKIE_CONSENT_VERSION` (`.env`, default `"1.0"`) é comparada contra o campo
`version` gravado dentro do cookie `bhub_consent`
(`parse_consent_cookie`, `app/core/cookie_consent.py:75-76`).

Para invalidar todas as escolhas anteriores (ex.: mudança relevante na política de
privacidade/cookies):

1. Atualize `COOKIE_CONSENT_VERSION` no `.env` (ex.: `"1.0"` → `"1.1"`).
2. Reinicie a aplicação.
3. Todo cookie `bhub_consent` existente, gravado com a versão antiga, passa a ser
   tratado como **não decidido** (`ConsentState()` default) na próxima requisição
   — o banner volta a aparecer para esse visitante, e nenhuma categoria opcional
   fica autorizada até nova decisão.

Não é necessário nenhum código adicional; a invalidação é automática via
comparação de string em `parse_consent_cookie`.

---

## 7. Como adicionar uma categoria futura

`app/core/cookie_consent.py` **não** propaga uma nova categoria automaticamente
em todos os pontos — `serialize_consent` e `is_granted` são genéricos (iteram
`OPTIONAL_CATEGORIES` / usam `getattr`), mas `ConsentState.as_dict()` e a
construção do `ConsentState(...)` dentro de `parse_consent_cookie` **hardcodam**
as três chaves (`analytics`, `external_media`, `marketing`) explicitamente. Ao
adicionar uma categoria, edite todos os pontos abaixo:

1. **`OPTIONAL_CATEGORIES`** (`app/core/cookie_consent.py`) — adicione o nome da
   categoria à tupla. Isso já é suficiente para `parse_consent_cookie` (loop de
   validação de tipos), `is_granted` e `serialize_consent`.
2. **Campo no dataclass `ConsentState`** — adicione o atributo (ex.:
   `nova_categoria: bool = False`).
3. **`ConsentState.as_dict()`** — adicione a chave `"nova_categoria":
   self.nova_categoria` ao dict retornado; ele é montado manualmente, não deriva
   de `OPTIONAL_CATEGORIES`.
4. **Construção do `ConsentState(...)` em `parse_consent_cookie`** — adicione
   `nova_categoria=data["nova_categoria"]` aos kwargs explícitos passados ao
   construtor (mesmo padrão de `analytics=data["analytics"]`, ...); esse
   `return ConsentState(...)` também é escrito à mão, não genérico.
5. **`app/web/consent.py::submit_cookie_consent`** — se a categoria deve poder
   ser marcada via `action=save` no form POST, adicione o parâmetro
   `Form(default=None)` correspondente e inclua-o no dict `submitted`.
6. **`app/templates/components/cookie_consent.html`** — adicione um
   `<input type="checkbox" name="nova_categoria">` no
   `<dialog id="cookie-preferences">`, seguindo o padrão existente
   (`{% if consent.nova_categoria %}checked{% endif %}`, `<label>` explicando a
   finalidade em linguagem simples).
7. **Documentação** — a nova categoria na tabela de `/cookies` (e nesta seção 2,
   se for o caso) e em `/privacy` se envolver dados pessoais.
8. **Testes** — estenda `tests/test_cookie_consent_unit.py` (parsing/
   serialização/`as_dict`) e `tests/test_cookie_consent_endpoints.py` (submissão
   via form).
9. **Recompile o Tailwind** se novas classes de template forem usadas (ver
   `CLAUDE.md` → Frontend / Design System).

Confira o código-fonte de `app/core/cookie_consent.py` no momento da mudança —
esta lista reflete os pontos hardcoded identificados na versão atual; pode haver
mais dependendo de refatorações futuras.

---

## 8. Como adicionar uma ferramenta externa sem carregá-la antes do consentimento

Nunca inclua um `<script>` ou `<iframe>` de terceiros incondicionalmente no
template — isso executaria antes (ou independentemente) da decisão do visitante.
Em vez disso, condicione a renderização à categoria correspondente usando o
helper Jinja `consent_state(request)` (o mesmo usado pelo componente do banner):

```jinja
{% set consent = consent_state(request) %}
{% if consent.external_media %}
<iframe src="https://exemplo-terceiro.com/embed/..." loading="lazy"></iframe>
{% else %}
<p>Este conteúdo requer autorização da categoria "Conteúdo externo".
   <button type="button" data-consent-open>Gerenciar preferências</button></p>
{% endif %}
```

Regras:

- O bloco condicional deve envolver o elemento inteiro que dispara a
  requisição de terceiro (script, iframe, pixel) — nunca apenas ocultar via CSS
  (`display:none` ainda carrega o recurso).
- Se a ferramenta expõe um SDK JS que se auto-inicializa, o `<script src="...">`
  em si só pode existir dentro do bloco condicional — nunca no `<head>` global.
- Depois que o visitante autoriza a categoria e a página recarrega/HTMX
  re-renderiza, o bloco passa a ser incluído porque `consent_state(request)` lê o
  cookie `bhub_consent` a cada requisição (SSR, não há cache client-side do
  estado).

---

## 9. Justificativa: remoção de IP/User-Agent do formulário de contato

O formulário de contato (`/contact`) deixou de gravar `ip_address` e
`user_agent` das mensagens recebidas. As colunas (`app/models/contact.py`)
permanecem no schema, mas como `nullable=True` e não são mais populadas.

Justificativa (princípio da necessidade, art. 6º, III, LGPD — tratamento
limitado ao mínimo necessário para a finalidade): o único uso desses campos era
suporte a antiabuso, e essa finalidade já é coberta por dois controles
independentes que **não** exigem reter IP/UA por mensagem:

- **CSRF** (`app/core/csrf.py`) — impede submissões forjadas de outros
  domínios;
- **Rate limiting** — limita o volume de submissões por origem no tempo de
  requisição, sem persistir o identificador junto ao registro da mensagem.

Como não há finalidade adicional que justifique reter IP/UA associados a cada
mensagem de contato, essa coleta foi removida. A página de contato agora exibe
um aviso de privacidade com link para `/privacy`.

---

## 10. Limitações da fase 1 e próximos passos

Limitações conhecidas e assumidas nesta primeira fase:

- **"Configurar" / central de preferências exige JavaScript** — os botões
  "Aceitar opcionais" e "Recusar opcionais" do banner funcionam sem JS (forms
  HTML puros), mas abrir o `<dialog id="cookie-preferences">` depende de
  `cookie-consent.js` (`dialog.showModal()`). Sem JS, o visitante só tem a opção
  binária aceitar/recusar tudo — não consegue escolher categoria a categoria.
- **`external_media` e `marketing` sem uso real** — as categorias existem no
  modelo de dados e na UI por transparência/preparação futura, mas nenhuma
  integração hoje depende delas.
- **Revogação não apaga histórico** — revogar o consentimento
  (`action=revoke`) impede novas coletas imediatamente e apaga os cookies
  `bhub_consent`/`analytics_session_id`, mas **não** apaga eventos de analytics já
  registrados no banco para sessões anteriores. A política de privacidade
  (`/privacy`) explica como o visitante pode solicitar a exclusão desses
  registros manualmente.

Sugestões para próximas fases:

- Job periódico de expurgo/anonimização de histórico de analytics além de um
  período de retenção definido (e endpoint de exclusão sob demanda ligado à
  revogação, se o volume justificar automação).
- Ativar a categoria `external_media` de fato quando o BHUB passar a incorporar
  mídia de terceiros (ex.: vídeos, embeds de redes sociais), usando o padrão da
  seção 8.
- Avaliar oferecer a central de preferências também sem JS (ex.: página dedicada
  com forms separados por categoria), se a barreira de acessibilidade for
  considerada relevante.
