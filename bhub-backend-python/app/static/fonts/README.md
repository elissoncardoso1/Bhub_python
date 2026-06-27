# BHUB self-hosted fonts

Self-hosted brand binaries served by `app/static/css/fonts.css`.

## Elms Sans (data / metrics face — `var(--font-data)`)

Shipped as a **variable** woff2 covering the full 200–900 weight range:

| File | axis | style |
|------|------|-------|
| `ElmsSans-Variable.woff2`        | `wght` 200–900 | normal |
| `ElmsSans-Italic-Variable.woff2` | `wght` 200–900 | italic |

Licensed under the **SIL Open Font License** (`ElmsSans-OFL.txt`), so the
`.woff2` are committed with the repo. Metric numbers (`.metric-value`,
`font-data`) render in Elms Sans; if a binary is ever missing the stack falls
back to Reddit Sans with `tabular-nums`.

### Regenerating from source TTF

Source TTFs live outside the repo (`/assets/.../Elms_Sans/`). To rebuild the
woff2:

```bash
pip install fonttools brotli
python -c "from fontTools.ttLib import woff2; \
  woff2.compress('ElmsSans-VariableFont_wght.ttf', 'ElmsSans-Variable.woff2')"
```

Raw `.ttf`/`.otf` are git-ignored here — only the optimized `.woff2` ship.
