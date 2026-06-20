# BHUB self-hosted fonts

This directory holds the **licensed** brand binaries that cannot live in Google
Fonts. They are intentionally **git-ignored** — never commit the `.woff2` files
(licensing). The `@font-face` rules live in `app/static/css/fonts.css`.

## Elms Sans (data / metrics face — `var(--font-data)`)

Drop these files here, exact names:

| File | weight |
|------|--------|
| `ElmsSans-Regular.woff2`  | 400 |
| `ElmsSans-SemiBold.woff2` | 600 |
| `ElmsSans-Bold.woff2`     | 700 |

`.woff2` only. To convert from `.otf`/`.ttf`:

```bash
pip install fonttools brotli
fonttools ttLib.woff2 compress ElmsSans-Regular.otf   # → ElmsSans-Regular.woff2
```

Until the files are present, metric numbers fall back to **Reddit Sans with
`tabular-nums`** (the current baseline). No code change is needed when you add
them — `font-display: swap` + the fallback stack handle activation.
