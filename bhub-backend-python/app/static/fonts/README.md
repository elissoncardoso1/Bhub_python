# BHUB self-hosted fonts

All brand families are self-hosted here and wired up in
`app/static/css/fonts.css`. The app has **no runtime dependency on the Google
Fonts CDN** (privacy / LGPD, offline, performance). Each is shipped as a single
**variable** woff2 (roman + italic) covering its full weight range, and is
open-source under the **SIL Open Font License** — the matching `*-OFL.txt` ships
alongside, so the `.woff2` are committed with the repo.

| Family | Role | Token | Files | `wght` |
|--------|------|-------|-------|--------|
| Reddit Sans | UI / body | `var(--font-sans)` | `RedditSans-Variable.woff2` (+ Italic) | 200–900 |
| Chivo Mono | code / tokens | `var(--font-mono)` | `ChivoMono-Variable.woff2` (+ Italic) | 100–900 |
| Elms Sans | data / metrics | `var(--font-data)` | `ElmsSans-Variable.woff2` (+ Italic) | 100–900 |

If a binary is ever missing, each token stack degrades to a system fallback
(`font-display: swap` keeps text visible meanwhile).

## Regenerating from source TTF

Source TTFs live outside the repo (`/assets/.../`, git-ignored). To rebuild a
woff2:

```bash
pip install fonttools brotli
python -c "from fontTools.ttLib import woff2; \
  woff2.compress('RedditSans-VariableFont_wght.ttf', 'RedditSans-Variable.woff2')"
```

Raw `.ttf`/`.otf` are git-ignored here — only the optimized `.woff2` ship.
