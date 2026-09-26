# Lista de Feeds RSS - Projeto Meridiano

Este documento contém a lista completa de feeds RSS utilizados no projeto Meridiano, organizados por categoria.

## � Periódicos Científicos

Periódicos têm cadastro e ingestão próprios (script `scripts/add_journal_feeds.py`), separados
dos blogs e portais abaixo. Desde o ADR-0007 há **duas vias de ingestão**:

- **`journal_source=CROSSREF`** — a fonte é a API REST do Crossref, consultada por ISSN.
  Usada onde o RSS da editora está atrás de anti-bot, que é o caso de Wiley, Taylor &
  Francis e Springer.
- **`journal_source=RSS`** — o feed da editora funciona (OJS, WordPress).

Para feeds do Crossref, `feed_url` guarda o endpoint da API que o sync usa e
`website_url` aponta para a página do periódico.

### Crossref (RSS bloqueado pela editora)

| Periódico | ISSN (eletrônico) | Editora |
| --- | --- | --- |
| Journal of Applied Behavior Analysis (JABA) | 1938-3703 | Wiley |
| Journal of the Experimental Analysis of Behavior (JEAB) | 1938-3711 | Wiley |
| Journal of Organizational Behavior Management (JOBM) | 1540-8604 | Taylor & Francis |
| Behavior Analysis in Practice (BAP) | 2196-8934 | Springer |
| Perspectives on Behavior Science (PoBS) | 2520-8977 | Springer |
| The Analysis of Verbal Behavior (TAVB) | 2196-8926 | Springer |
| Behavior and Social Issues (BSI) | 2376-6786 | Springer |

### RSS (feed da editora funcionando)

| Periódico | Feed |
| --- | --- |
| Revista Perspectivas em Análise do Comportamento | `https://revistaperspectivas.org/perspectivas/gateway/plugin/WebFeedGatewayPlugin/rss2` |
| Revista ESPECTRO (UFSCar) | `https://espectro.ufscar.br/index.php/1979/gateway/plugin/WebFeedGatewayPlugin/rss2` |
| Boletim Contexto | `https://boletimcontexto.wordpress.com/feed` |
| OBM Network News *(inativo — sem publicação desde 2024)* | `https://www.obmnetwork.com/news/news_rss.asp` |

### Operação

```bash
# Cadastrar/corrigir os periódicos (idempotente)
python -m scripts.add_journal_feeds

# Validar ISSNs antes de cadastrar (confira o título devolvido!)
python -m scripts.validate_journal_issn --all

# Migrar os feeds já cadastrados em produção (dry-run por padrão)
python -m scripts.migrate_journal_feeds_to_crossref
python -m scripts.migrate_journal_feeds_to_crossref --apply
```

## �📚 ABA (Análise do Comportamento Aplicada)

### Fontes Internacionais

#### Blogs Profissionais e Sites Educacionais
- `https://science.abainternational.org/feed/` - ABAI Science Blog
- `https://www.iloveaba.com/feeds/posts/default?alt=rss` - I Love ABA!
- `https://www.appliedbehavioranalysisedu.org/feed/` - Applied Behavior Analysis Edu
- `https://www.verbalbeginnings.com/feed/` - Verbal Beginnings Blog
- `https://aba-works.com/feed/` - ABA Works Blog
- `https://carolinacenterforaba.com/feed/` - Carolina Center for ABA
- `https://www.iabaconsultants.com/feed/` - IABA Consultants Blog
- `https://alldayaba.org/blog/f.rss` - All Day ABA
- `https://abaspeech.org/feed/` - ABA Speech Blog
- `https://www.fullspectrumaba.com/blog-feed.xml` - Full Spectrum ABA
- `https://abaeveryday.com/feed/` - ABA Everyday Blog
- `https://www.brighterstridesaba.com/feed/` - Brighter Strides ABA

#### Portais de Notícias sobre Autismo (com cobertura ABA)
- `https://autismspectrumnews.org/feed` - Autism Spectrum News
- `https://www.spectrumnews.org/feed/` - Spectrum News (Autism Research)
- `https://autismparentingmagazine.com/feed` - Autism Parenting Magazine

### Fontes Brasileiras

#### Associações Profissionais e Publicações
- `https://boletimcontexto.wordpress.com/feed/` - Boletim Contexto - ABPMC
- `https://comportese.com/feed/` - Portal Comporte-se

#### Blogs Acadêmicos e Programas Universitários
- `http://analisedocomportamentouel.blogspot.com/feeds/posts/default` - Blog PGAC UEL
- `https://accultura.wordpress.com/feed/` - Blog AC Cultura PUC-SP
- `https://obmbrasil.wordpress.com/feed/` - Blog OBM Brasil

#### Blogs Profissionais e Educacionais
- `https://blog.ieac.net.br/feed` - Blog do IEAC
- `https://genialcare.com.br/blog/feed` - Genial Care Blog
- `https://wayaba.com.br/feed` - WayABA
- `https://abamais.com/feed` - ABA+ (ABA Mais)
- `https://abaforadamesinha.com.br/feed` - ABA Fora da Mesinha
- `https://www.abaedu.com.br/blog/feed` - Blog ABAEDU

#### Portais de Notícias e Organizações sobre Autismo
- `https://www.canalautismo.com.br/feed` - Canal Autismo / Revista Autismo
- `https://autismoerealidade.org.br/feed` - Autismo e Realidade
- `https://jornal.usp.br/tag/autismo/feed` - Jornal da USP - Tag Autismo

