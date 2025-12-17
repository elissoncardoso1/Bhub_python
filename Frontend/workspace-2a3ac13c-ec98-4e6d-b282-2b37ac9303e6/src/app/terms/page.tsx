'use client';

import React from 'react';
import { MainLayout } from '@/components/Layout/MainLayout';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';

export default function TermsPage() {
  return (
    <MainLayout>
      <Header />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm">
          <h1 className="font-display font-bold text-3xl text-bhub-navy-dark dark:text-white mb-6">
            Termos de Uso
          </h1>
          
          <div className="prose dark:prose-invert max-w-none font-body text-gray-700 dark:text-gray-300">
            <p>
              Bem-vindo ao BHub. Ao acessar nosso agregador de notícias científicas, você concorda com os seguintes termos.
            </p>

            <h3>1. Natureza do Serviço</h3>
            <p>
              O BHub é um agregador de conteúdo que facilita o acesso a artigos científicos e notícias sobre Análise do Comportamento.
              Não somos os autores do conteúdo original, salvo quando indicado.
            </p>

            <h3>2. Propriedade Intelectual</h3>
            <p>
              Todo o conteúdo agregado (títulos, resumos, links) pertence aos seus respectivos autores e editores.
              O BHub respeita os direitos autorais e fornece links diretos para as fontes originais.
            </p>

            <h3>3. Uso Aceitável</h3>
            <p>
              Você concorda em usar a plataforma apenas para fins lícitos e educacionais. É proibido tentar coletar dados massivamente (scraping) sem autorização ou comprometer a segurança do site.
            </p>

            <h3>4. Isenção de Responsabilidade</h3>
            <p>
              Embora nos esforcemos para agregar fontes confiáveis, não garantimos a exatidão ou integridade do conteúdo de terceiros.
              As opiniões expressas nos artigos linkados são de responsabilidade exclusiva de seus autores.
            </p>

            <h3>5. Alterações nos Termos</h3>
            <p>
              Podemos atualizar estes termos periodicamente. O uso contínuo da plataforma após alterações constitui aceitação dos novos termos.
            </p>
            
            <p className="text-sm text-gray-500 mt-8">
              Última atualização: Dezembro de 2025
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </MainLayout>
  );
}
