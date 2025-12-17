'use client';

import React from 'react';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { Icon } from '@/components/Icon/Icon';
import { Badge } from '@/components/Badge/Badge';
import { Button } from '@/components/Button/Button';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';

export default function About() {
  const router = useRouter();

  const features = [
    {
      icon: 'search',
      title: 'Busca Avançada',
      description: 'Motor de busca acadêmico interno com suporte a operadores lógicos (AND, OR, NOT) e filtros granulares por fonte, área temática, idioma, data e autoria.',
      link: '/repository',
      color: 'text-bhub-teal-primary'
    },
    {
      icon: 'barChart',
      title: 'Classificação por IA',
      description: 'Sistema inteligente de classificação em três níveis: IA externa (DeepSeek/OpenRouter), ML local (embeddings) e heurística, garantindo categorização precisa dos artigos.',
      color: 'text-blue-500'
    },
    {
      icon: 'star',
      title: 'Score de Relevância',
      description: 'Avaliação automática (1-10) baseada em palavras-chave de impacto, periódico, DOI, qualidade do abstract e dados quantitativos para identificar artigos de alto impacto.',
      color: 'text-yellow-500'
    },
    {
      icon: 'filter',
      title: 'Filtros Avançados',
      description: 'Refinamento progressivo com filtros por tipo de fonte, categoria, idioma, intervalo de datas, autoria e tipo de conteúdo para pesquisa precisa e reprodutível.',
      color: 'text-purple-500'
    },
    {
      icon: 'globe',
      title: 'Agregação Automática',
      description: 'Sistema automatizado que agrega artigos de múltiplas fontes RSS, portais científicos e PDFs, mantendo o repositório sempre atualizado.',
      color: 'text-green-500'
    },
    {
      icon: 'languages',
      title: 'Tradução Inteligente',
      description: 'Tradução automática de títulos e abstracts usando IA, facilitando o acesso a conteúdo científico em diferentes idiomas.',
      color: 'text-indigo-500'
    }
  ];

  const values = [
    {
      icon: 'award',
      title: 'Excelência Científica',
      description: 'Rigor metodológico e qualidade nas publicações agregadas'
    },
    {
      icon: 'bookOpen',
      title: 'Acesso Aberto',
      description: 'Democratização do conhecimento científico'
    },
    {
      icon: 'users',
      title: 'Colaboração',
      description: 'Intercâmbio e colaboração acadêmica'
    },
    {
      icon: 'trending',
      title: 'Impacto Social',
      description: 'Aplicações práticas e impacto na sociedade'
    }
  ];

  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="font-display font-bold text-4xl md:text-5xl text-bhub-navy-dark dark:text-white mb-4">
            Sobre o BHub
          </h1>
          <p className="font-body font-light text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            Repositório científico dedicado à Análise do Comportamento, 
            conectando pesquisadores e promovendo o conhecimento científico.
          </p>
        </div>

        {/* Mission Section */}
        <section className="bg-gradient-to-br from-bhub-navy-dark to-bhub-dark-gray rounded-lg p-8 md:p-12 text-white mb-12">
          <div className="max-w-3xl mx-auto text-center">
            <Icon name="bookOpen" className="mx-auto mb-4 text-bhub-teal-primary" size="lg" />
            <h2 className="font-display font-bold text-2xl md:text-3xl mb-4">
              Nossa Missão
            </h2>
            <p className="font-body font-light text-lg leading-relaxed">
              Facilitar o acesso a pesquisas de qualidade, promover colaboração entre acadêmicos 
              e acelerar o avanço do conhecimento em análise comportamental e suas aplicações práticas.
            </p>
          </div>
        </section>

        {/* Features Section */}
        <section className="mb-12">
          <div className="text-center mb-8">
            <h2 className="font-display font-bold text-3xl text-bhub-navy-dark dark:text-white mb-2">
              Funcionalidades
            </h2>
            <p className="font-body font-light text-gray-600 dark:text-gray-400">
              Tecnologia avançada para pesquisa científica eficiente
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-4">
                  <div className={cn(
                    "flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center",
                    "bg-gray-100 dark:bg-gray-700"
                  )}>
                    <Icon name={feature.icon as any} className={feature.color} size="md" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-display font-semibold text-lg text-bhub-navy-dark dark:text-white mb-2">
                      {feature.title}
                    </h3>
                    <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                      {feature.description}
                    </p>
                    {feature.link && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="mt-3 text-bhub-teal-primary hover:text-bhub-teal-primary/80"
                        onClick={() => router.push(feature.link!)}
                      >
                        Explorar
                        <Icon name="chevronRight" size="sm" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Values Section */}
        <section className="mb-12">
          <div className="text-center mb-8">
            <h2 className="font-display font-bold text-3xl text-bhub-navy-dark dark:text-white mb-2">
              Nossos Valores
            </h2>
            <p className="font-body font-light text-gray-600 dark:text-gray-400">
              Princípios que guiam nosso trabalho
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {values.map((value, index) => (
              <div
                key={index}
                className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 text-center"
              >
                <div className="w-16 h-16 mx-auto mb-4 bg-bhub-teal-light/20 dark:bg-bhub-teal-primary/20 rounded-full flex items-center justify-center">
                  <Icon name={value.icon as any} className="text-bhub-teal-primary" size="lg" />
                </div>
                <h3 className="font-display font-semibold text-lg text-bhub-navy-dark dark:text-white mb-2">
                  {value.title}
                </h3>
                <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400">
                  {value.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Vision Section */}
        <section className="bg-white dark:bg-gray-800 rounded-lg p-8 md:p-12 border border-gray-200 dark:border-gray-700">
          <div className="max-w-3xl mx-auto text-center">
            <Icon name="trending" className="mx-auto mb-4 text-bhub-teal-primary" size="lg" />
            <h2 className="font-display font-bold text-2xl md:text-3xl text-bhub-navy-dark dark:text-white mb-4">
              Nossa Visão
            </h2>
            <p className="font-body font-light text-lg text-gray-700 dark:text-gray-300 leading-relaxed">
              Ser o principal repositório mundial de pesquisa em análise do comportamento,
              reconhecido pela qualidade, relevância e impacto das publicações que disponibilizamos.
              Utilizamos tecnologia de ponta, incluindo inteligência artificial e machine learning,
              para oferecer uma experiência de pesquisa científica de classe mundial.
            </p>
          </div>
        </section>

        {/* CTA Section */}
        <section className="mt-12 text-center">
          <div className="bg-gradient-to-r from-bhub-teal-primary to-bhub-teal-light rounded-lg p-8 text-white">
            <h2 className="font-display font-bold text-2xl md:text-3xl mb-4">
              Comece a Explorar
            </h2>
            <p className="font-body font-light text-lg mb-6 max-w-2xl mx-auto">
              Descubra artigos científicos de alta qualidade usando nossa busca avançada e filtros inteligentes.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                variant="default"
                size="lg"
                className="bg-white text-bhub-teal-primary hover:bg-gray-100"
                onClick={() => router.push('/repository')}
              >
                <Icon name="search" size="sm" />
                Acessar Repositório
              </Button>
              <Button
                variant="outline"
                size="lg"
                className="border-white text-white hover:bg-white/10"
                onClick={() => router.push('/articles')}
              >
                <Icon name="bookOpen" size="sm" />
                Ver Artigos
              </Button>
            </div>
          </div>
        </section>
      </main>
      
      <Footer />
    </MainLayout>
  );
}
