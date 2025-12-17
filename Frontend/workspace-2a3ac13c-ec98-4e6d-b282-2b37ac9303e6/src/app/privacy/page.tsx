'use client';

import React from 'react';
import { MainLayout } from '@/components/Layout/MainLayout';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';

export default function PrivacyPage() {
  return (
    <MainLayout>
      <Header />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm">
          <h1 className="font-display font-bold text-3xl text-bhub-navy-dark dark:text-white mb-6">
            Política de Privacidade
          </h1>
          
          <div className="prose dark:prose-invert max-w-none font-body text-gray-700 dark:text-gray-300">
            <p>
              Esta Política de Privacidade descreve como o BHub ("nós", "nosso") coleta, usa e protege suas informações.
            </p>

            <h3>1. Coleta de Dados</h3>
            <p>
              Ao utilizar nossa plataforma, podemos coletar informações sobre sua navegação, artigos lidos e interações (curtidas, salvamentos).
              Não coletamos dados sensíveis sem seu consentimento explícito.
            </p>

            <h3>2. Uso das Informações</h3>
            <p>
              Utilizamos os dados para:
            </p>
            <ul>
              <li>Personalizar sua experiência de leitura.</li>
              <li>Melhorar nossa curadoria de conteúdo científico.</li>
              <li>Analisar tendências de acesso e interesse na área de Análise do Comportamento.</li>
            </ul>

            <h3>3. Cookies e Tecnologias Semelhantes</h3>
            <p>
              Utilizamos cookies para manter suas preferências e sessão ativa. Você pode gerenciar os cookies nas configurações do seu navegador.
            </p>

            <h3>4. Compartilhamento de Dados</h3>
            <p>
              Não vendemos suas informações pessoais. Podemos compartilhar dados anonimizados para fins de pesquisa acadêmica.
            </p>

            <h3>5. Seus Direitos</h3>
            <p>
              Você tem o direito de solicitar acesso, correção ou exclusão de seus dados pessoais, conforme previsto na LGPD (Lei Geral de Proteção de Dados).
            </p>

            <h3>6. Contato</h3>
            <p>
              Para questões sobre privacidade, entre em contato conosco através do canal de suporte na plataforma.
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
