import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
    darkMode: "class",
    content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
        extend: {
                colors: {
                        // BHub specific colors
                        'bhub-dark-gray': '#272727',
                        'bhub-light-gray': '#F7F7F7',
                        'bhub-teal-primary': '#41B5A3',
                        'bhub-teal-light': '#B7ECE4',
                        'bhub-navy-dark': '#1C3159',
                        'bhub-navy-light': '#D6E0EC',
                        'bhub-red-accent': '#BA213D',
                        'bhub-red-light': '#FAEDED',
                        'bhub-yellow-primary': '#FABD4A',
                        'bhub-yellow-light': '#FDE6BA',
                        // Default shadcn colors
                        background: 'hsl(var(--background))',
                        foreground: 'hsl(var(--foreground))',
                        card: {
                                DEFAULT: 'hsl(var(--card))',
                                foreground: 'hsl(var(--card-foreground))'
                        },
                        popover: {
                                DEFAULT: 'hsl(var(--popover))',
                                foreground: 'hsl(var(--popover-foreground))'
                        },
                        primary: {
                                DEFAULT: 'hsl(var(--primary))',
                                foreground: 'hsl(var(--primary-foreground))'
                        },
                        secondary: {
                                DEFAULT: 'hsl(var(--secondary))',
                                foreground: 'hsl(var(--secondary-foreground))'
                        },
                        muted: {
                                DEFAULT: 'hsl(var(--muted))',
                                foreground: 'hsl(var(--muted-foreground))'
                        },
                        accent: {
                                DEFAULT: 'hsl(var(--accent))',
                                foreground: 'hsl(var(--accent-foreground))'
                        },
                        destructive: {
                                DEFAULT: 'hsl(var(--destructive))',
                                foreground: 'hsl(var(--destructive-foreground))'
                        },
                        border: 'hsl(var(--border))',
                        input: 'hsl(var(--input))',
                        ring: 'hsl(var(--ring))',
                        chart: {
                                '1': 'hsl(var(--chart-1))',
                                '2': 'hsl(var(--chart-2))',
                                '3': 'hsl(var(--chart-3))',
                                '4': 'hsl(var(--chart-4))',
                                '5': 'hsl(var(--chart-5))'
                        }
                },
                fontFamily: {
                        'display': ['Roboto Slab', 'serif'],
                        'body': ['Raleway', 'sans-serif'],
                        'mono': ['Fira Code', 'monospace']
                },
                fontSize: {
                        'h1': ['56px', { lineHeight: '1.2', fontWeight: '800' }],
                        'h2': ['28px', { lineHeight: '1.35', fontWeight: '700' }],
                        'h3': ['18px', { lineHeight: '1.4', fontWeight: '700' }],
                        'body-lg': ['14px', { lineHeight: '1.7', fontWeight: '300' }]
                },
                borderRadius: {
                        lg: 'var(--radius)',
                        md: 'calc(var(--radius) - 2px)',
                        sm: 'calc(var(--radius) - 4px)'
                }
        }
  },
  plugins: [tailwindcssAnimate],
};
export default config;
