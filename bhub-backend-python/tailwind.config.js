/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // ── BRAND — Burgundy scale (primary). #58272D is the canonical brand color ──
        primary: {
          50: '#fbf3f4',
          100: '#f4dedf',
          200: '#e6b9bc',
          300: '#ce8c91',
          400: '#a85961',
          500: '#7e3640',
          600: '#58272d',  // ★ BRAND — CTAs, links, marks
          700: '#4a1f24',
          800: '#3a181c',
          900: '#2a1115',
        },
        // ── Sage / olive — secondary brand accent ──
        sage: {
          50: '#f5f4e6',
          100: '#ebe9c9',
          200: '#d9d6a0',
          300: '#c0bd84',
          400: '#a3a16e',  // ★ accent — secondary bars, links on dark
          500: '#8b8956',
          600: '#6f6d40',
          700: '#54532f',
        },
        // ── Cream — soft tinted backgrounds, hero washes (never text) ──
        cream: {
          50: '#fdfce8',
          100: '#f8f6d4',
          200: '#f0eebd',  // ★ pastel — hero, soft cards
          300: '#e6e2a3',
          400: '#d4ce80',
        },
        // ── Tan / camel — supporting warm earth tone ──
        tan: {
          50: '#faf6ef',
          100: '#f0e6d2',
          200: '#ddc9a5',
          300: '#c5a87a',
          400: '#a48c68',  // ★ tan — neutral warmth, secondary outlines
          500: '#876f4f',
          600: '#6a563c',
        },
        // ── Off-white — page canvas ──
        paper: {
          DEFAULT: '#f4f0f1',
          soft: '#efe9ea',
        },
        // Legacy alias kept so existing `accent-light` utilities resolve to the warm palette
        accent: {
          light: '#f8f6d4',        // cream-100
          'light-hover': '#f0eebd', // cream-200
        },
        // ── Warm neutral — override Tailwind's cool `slate` with the warm `stone` ramp
        //    so every existing `slate-*` utility across the templates warms up at once. ──
        slate: {
          50: '#fafaf9',
          100: '#f5f5f4',
          200: '#e7e5e4',
          300: '#d6d3d1',
          400: '#a8a29e',
          500: '#78716c',
          600: '#57534e',
          700: '#44403c',
          800: '#292524',
          900: '#1c1917',
        },
        // ── Semantic feedback — tuned to the warm earth palette ──
        success: {
          50: '#f4f7e8',
          100: '#e6edcc',
          500: '#74894a',
          600: '#5c6d3a',
          700: '#475630',
        },
        warning: {
          50: '#fdf6e3',
          100: '#f8ebc4',
          500: '#c79434',
          600: '#a07527',
          700: '#7c5a1d',
        },
        error: {
          50: '#fbebec',
          100: '#f5d2d5',
          500: '#b34a52',
          600: '#8c343b',
          700: '#6e272d',
        },
        info: {
          50: '#eef2ef',
          100: '#d7e0db',
          500: '#5a7f72',
          600: '#456256',
          700: '#354d44',
        },
      },
      fontFamily: {
        sans: ['"Reddit Sans"', 'Inter', 'system-ui', '-apple-system', '"Segoe UI"', 'Roboto', 'sans-serif'],
        serif: ['Georgia', '"Times New Roman"', 'Times', 'serif'],
        mono: ['"Chivo Mono"', '"Fira Code"', 'ui-monospace', 'Menlo', 'monospace'],
        data: ['"Elms Sans"', '"Reddit Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card-hover': '0 4px 14px rgba(88, 39, 45, 0.10)',
      },
      keyframes: {
        blob: {
          '0%':   { transform: 'translate(0px, 0px) scale(1)' },
          '33%':  { transform: 'translate(30px, -50px) scale(1.1)' },
          '66%':  { transform: 'translate(-20px, 20px) scale(0.9)' },
          '100%': { transform: 'translate(0px, 0px) scale(1)' },
        },
      },
      animation: {
        blob: 'blob 7s infinite',
      },
    },
  },
  plugins: [],
}
