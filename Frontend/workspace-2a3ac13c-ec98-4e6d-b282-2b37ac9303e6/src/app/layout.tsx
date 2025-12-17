import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/Theme/ThemeProvider";
import { SessionWrapper } from "@/components/SessionWrapper";
import { AnalyticsProvider } from "@/components/AnalyticsProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});


export const metadata: Metadata = {
  title: "BHub - Repositório de Análise do Comportamento",
  description: "Repositório científico dedicado à análise do comportamento, conectando pesquisadores e promovendo o conhecimento científico.",
  keywords: ["BHub", "Análise do Comportamento", "Psicologia", "Pesquisa Científica", "Terapia Comportamental"],
  authors: [{ name: "BHub Team" }],
  icons: {
    icon: "https://z-cdn.chatglm.cn/z-ai/static/logo.svg",
  },
  openGraph: {
    title: "BHub - Repositório de Análise do Comportamento",
    description: "Repositório científico dedicado à análise do comportamento",
    url: "https://bhub.example.com",
    siteName: "BHub",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "BHub - Repositório de Análise do Comportamento",
    description: "Repositório científico dedicado à análise do comportamento",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <SessionWrapper>
          <ThemeProvider>
            <AnalyticsProvider>
              {children}
            </AnalyticsProvider>
            <Toaster />
          </ThemeProvider>
        </SessionWrapper>
      </body>
    </html>
  );
}
