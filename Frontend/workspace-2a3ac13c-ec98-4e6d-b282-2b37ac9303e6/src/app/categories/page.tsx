'use client';

import React from 'react';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { Badge } from '@/components/Badge/Badge';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';

export default function Categories() {
  const categories = [
    {
      id: 'behavior',
      name: 'Comportamento',
      description: 'Estudos experimentais e aplicados do comportamento humano',
      count: 145,
      color: 'bg-bhub-teal-primary'
    },
    {
      id: 'cognition',
      name: 'Cognição',
      description: 'Processos cognitivos e sua relação com o comportamento',
      count: 98,
      color: 'bg-bhub-navy-dark'
    },
    {
      id: 'therapy',
      name: 'Terapia',
      description: 'Intervenções terapêuticas baseadas em análise comportamental',
      count: 87,
      color: 'bg-bhub-red-accent'
    },
    {
      id: 'education',
      name: 'Educação',
      description: 'Aplicações da análise do comportamento em contextos educacionais',
      count: 76,
      color: 'bg-bhub-yellow-primary'
    },
    {
      id: 'research',
      name: 'Pesquisa',
      description: 'Metodologia e fundamentos da pesquisa comportamental',
      count: 112,
      color: 'bg-bhub-teal-primary'
    },
    {
      id: 'clinical',
      name: 'Clínica',
      description: 'Aplicações clínicas da análise do comportamento',
      count: 93,
      color: 'bg-bhub-navy-dark'
    }
  ];

  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-12">
          <h1 className="font-display font-bold text-4xl text-bhub-navy-dark dark:text-white mb-4">
            Categorias
          </h1>
          <p className="font-body font-light text-lg text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            Explore nossas categorias de pesquisa para encontrar artigos especializados em sua área de interesse
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {categories.map((category) => (
            <div
              key={category.id}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 ${category.color} rounded-lg flex items-center justify-center`}>
                  <Icon name="folder" className="text-white" />
                </div>
                <span className="font-body font-medium text-sm text-gray-500 dark:text-gray-400">
                  {category.count} artigos
                </span>
              </div>
              
              <h3 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white mb-2 group-hover:text-bhub-teal-primary transition-colors">
                {category.name}
              </h3>
              
              <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                {category.description}
              </p>
              
              <Button
                variant="outline"
                className="w-full group-hover:border-bhub-teal-primary group-hover:text-bhub-teal-primary"
              >
                Explorar Categoria
                <Icon name="chevronRight" size="sm" />
              </Button>
            </div>
          ))}
        </div>

        <div className="text-center">
          <Button
            variant="default"
            className="bg-bhub-teal-primary hover:bg-bhub-teal-primary/90"
          >
            Ver Todas as Categorias
            <Icon name="arrow-right" />
          </Button>
        </div>
      </main>
      
      <Footer />
    </MainLayout>
  );
}