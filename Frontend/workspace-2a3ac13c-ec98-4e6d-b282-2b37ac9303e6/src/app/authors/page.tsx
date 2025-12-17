'use client';

import React from 'react';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { Avatar } from '@/components/Avatar/Avatar';
import { Badge } from '@/components/Badge/Badge';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';

export default function Authors() {
  const authors = [
    {
      id: '1',
      name: 'Dra. Ana Silva',
      initials: 'AS',
      affiliation: 'Universidade de São Paulo - Departamento de Psicologia',
      articles: 23,
      citations: 145,
      specialties: ['Análise Comportamental', 'Terapia Cognitivo-Comportamental'],
      email: 'ana.silva@usp.br'
    },
    {
      id: '2',
      name: 'Dr. Carlos Santos',
      initials: 'CS',
      affiliation: 'Universidade Federal do Rio de Janeiro',
      articles: 18,
      citations: 89,
      specialties: ['Pesquisa Experimental', 'Metodologia'],
      email: 'carlos.santos@ufrj.br'
    },
    {
      id: '3',
      name: 'Dra. Maria Oliveira',
      initials: 'MO',
      affiliation: 'Universidade de Brasília',
      articles: 15,
      citations: 67,
      specialties: ['Educação Especial', 'Intervenção Precoce'],
      email: 'maria.oliveira@unb.br'
    },
    {
      id: '4',
      name: 'Dr. João Costa',
      initials: 'JC',
      affiliation: 'Universidade Federal de Minas Gerais',
      articles: 12,
      citations: 54,
      specialties: ['Neurociência Comportamental', 'Modelagem Matemática'],
      email: 'joao.costa@ufmg.br'
    },
    {
      id: '5',
      name: 'Dra. Fernanda Dias',
      initials: 'FD',
      affiliation: 'Universidade Estadual de Campinas',
      articles: 9,
      citations: 43,
      specialties: ['Análise Aplicada', 'Organização Comportamental'],
      email: 'fernanda.dias@unicamp.br'
    },
    {
      id: '6',
      name: 'Dr. Roberto Mendes',
      initials: 'RM',
      affiliation: 'Universidade Federal do Paraná',
      articles: 7,
      citations: 38,
      specialties: ['Comportamento Verbal', 'Análise Funcional'],
      email: 'roberto.mendes@ufpr.br'
    }
  ];

  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-12">
          <h1 className="font-display font-bold text-4xl text-bhub-navy-dark dark:text-white mb-4">
            Autores em Destaque
          </h1>
          <p className="font-body font-light text-lg text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            Conheça os pesquisadores que contribuem para o avanço da análise do comportamento
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {authors.map((author) => (
            <div
              key={author.id}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all"
            >
              <div className="flex items-start gap-4 mb-4">
                <Avatar 
                  name={author.name}
                  initials={author.initials}
                  size="lg"
                />
                <div className="flex-1">
                  <h3 className="font-display font-bold text-lg text-bhub-navy-dark dark:text-white mb-1">
                    {author.name}
                  </h3>
                  <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {author.affiliation}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-500">
                    <Icon name="mail" size="sm" />
                    {author.email}
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-4">
                {author.specialties.map((specialty, index) => (
                  <Badge
                    key={index}
                    label={specialty}
                    variant="light"
                    className="text-xs"
                  />
                ))}
              </div>

              <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <Icon name="fileText" size="sm" />
                    {author.articles} artigos
                  </span>
                  <span className="flex items-center gap-1">
                    <Icon name="star" size="sm" />
                    {author.citations} citações
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-bhub-teal-primary border-bhub-teal-primary hover:bg-bhub-teal-primary hover:text-white"
                >
                  Ver Perfil
                  <Icon name="chevronRight" size="sm" />
                </Button>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center">
          <Button
            variant="default"
            className="bg-bhub-teal-primary hover:bg-bhub-teal-primary/90"
          >
            Ver Todos os Autores
            <Icon name="arrowRight" />
          </Button>
        </div>
      </main>
      
      <Footer />
    </MainLayout>
  );
}