'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Icon } from '@/components/Icon/Icon';
import { TrafficStats, ContentStats } from '@/services/analyticsService';
import { cn } from '@/lib/utils';

interface AnalyticsCardsProps {
  traffic: TrafficStats;
  content: ContentStats;
}

export function AnalyticsCards({ traffic, content }: AnalyticsCardsProps) {
  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${minutes}m ${secs}s`;
  };

  const cards = [
    {
      label: 'Sessões Totais',
      value: traffic.total_sessions.toLocaleString('pt-BR'),
      icon: 'users',
      color: 'text-blue-500',
      bg: 'bg-blue-100 dark:bg-blue-900/20',
      description: 'Total de sessões de usuários',
    },
    {
      label: 'Visitantes Únicos',
      value: traffic.unique_visitors.toLocaleString('pt-BR'),
      icon: 'user',
      color: 'text-green-500',
      bg: 'bg-green-100 dark:bg-green-900/20',
      description: 'Usuários únicos',
    },
    {
      label: 'Visualizações de Página',
      value: traffic.total_page_views.toLocaleString('pt-BR'),
      icon: 'eye',
      color: 'text-purple-500',
      bg: 'bg-purple-100 dark:bg-purple-900/20',
      description: 'Total de page views',
    },
    {
      label: 'Duração Média da Sessão',
      value: formatDuration(traffic.avg_session_duration),
      icon: 'clock',
      color: 'text-orange-500',
      bg: 'bg-orange-100 dark:bg-orange-900/20',
      description: 'Tempo médio por sessão',
    },
    {
      label: 'Visualizações de Artigos',
      value: content.article_views.toLocaleString('pt-BR'),
      icon: 'fileText',
      color: 'text-cyan-500',
      bg: 'bg-cyan-100 dark:bg-cyan-900/20',
      description: 'Artigos visualizados',
    },
    {
      label: 'Downloads de Artigos',
      value: content.article_downloads.toLocaleString('pt-BR'),
      icon: 'download',
      color: 'text-pink-500',
      bg: 'bg-pink-100 dark:bg-pink-900/20',
      description: 'Artigos baixados',
    },
    {
      label: 'Buscas Realizadas',
      value: content.searches.toLocaleString('pt-BR'),
      icon: 'search',
      color: 'text-indigo-500',
      bg: 'bg-indigo-100 dark:bg-indigo-900/20',
      description: 'Total de buscas',
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, index) => (
        <Card key={index} className="hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 dark:text-gray-400">
              {card.label}
            </CardTitle>
            <div className={cn('p-2 rounded-full', card.bg)}>
              <Icon name={card.icon as any} className={cn('h-4 w-4', card.color)} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {card.description}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

