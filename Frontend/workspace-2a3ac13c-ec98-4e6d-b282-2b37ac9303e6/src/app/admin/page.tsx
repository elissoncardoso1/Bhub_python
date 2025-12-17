'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { Icon } from '@/components/Icon/Icon';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/Badge/Badge';
import { AdminService, AdminStats, DetailedStats, FeedSyncAllResult } from '@/services/adminService';
import { ArticleAdminService } from '@/services/articleAdminService';
import { AnalyticsService } from '@/services/analyticsService';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import Link from 'next/link';

export default function AdminDashboard() {
  const router = useRouter();
  const { data: session } = useSession();
  const { toast } = useToast();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [detailedStats, setDetailedStats] = useState<DetailedStats | null>(null);
  const [analyticsSummary, setAnalyticsSummary] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [systemStatus, setSystemStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  // Polling para atualização em tempo real
  const fetchStats = useCallback(async () => {
    if (!session?.accessToken) return;
    
    try {
      const [statsData, detailedData, analyticsData] = await Promise.all([
        AdminService.getStats(session.accessToken as string),
        AdminService.getDetailedStats(session.accessToken as string),
        AnalyticsService.getTrafficStats(session.accessToken as string, 7).catch(() => null),
      ]);
      setStats(statsData);
      setDetailedStats(detailedData);
      setAnalyticsSummary(analyticsData);
      setSystemStatus('online');
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Erro ao buscar estatísticas:', error);
      setSystemStatus('offline');
      toast({
        title: 'Erro',
        description: 'Não foi possível atualizar as estatísticas',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [session, toast]);

  useEffect(() => {
    fetchStats();
    
    // Atualizar a cada 30 segundos
    const interval = setInterval(fetchStats, 30000);
    
    return () => clearInterval(interval);
  }, [fetchStats]);

  const handleSyncAllFeeds = async () => {
    if (!session?.accessToken) {
      toast({
        title: 'Erro',
        description: 'Sessão não autenticada',
        variant: 'destructive',
      });
      return;
    }
    
    setIsSyncing(true);
    try {
      const result: FeedSyncAllResult = await AdminService.syncAllFeeds(session.accessToken as string);
      
      toast({
        title: 'Sincronização concluída',
        description: `${result.total_new_articles} novos artigos agregados de ${result.successful}/${result.total_feeds} feeds`,
      });
      
      // Atualizar stats após sincronização
      await fetchStats();
    } catch (error: any) {
      toast({
        title: 'Erro na sincronização',
        description: error.message || 'Falha ao sincronizar feeds',
        variant: 'destructive',
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const statCards = [
    { 
      label: 'Total de Artigos', 
      value: stats?.total_articles || 0, 
      icon: 'fileText', 
      color: 'text-blue-500', 
      bg: 'bg-blue-100 dark:bg-blue-900/20',
      change: stats?.articles_this_week || 0,
      changeLabel: 'esta semana'
    },
    { 
      label: 'Feeds Ativos', 
      value: stats?.total_feeds || 0, 
      icon: 'rss', 
      color: 'text-orange-500', 
      bg: 'bg-orange-100 dark:bg-orange-900/20'
    },
    { 
      label: 'Categorias', 
      value: stats?.total_categories || 0, 
      icon: 'folder', 
      color: 'text-purple-500', 
      bg: 'bg-purple-100 dark:bg-purple-900/20'
    },
    { 
      label: 'Autores', 
      value: stats?.total_authors || 0, 
      icon: 'users', 
      color: 'text-green-500', 
      bg: 'bg-green-100 dark:bg-green-900/20'
    },
    { 
      label: 'PDFs', 
      value: stats?.total_pdfs || 0, 
      icon: 'download', 
      color: 'text-indigo-500', 
      bg: 'bg-indigo-100 dark:bg-indigo-900/20'
    },
    { 
      label: 'Visualizações', 
      value: stats?.views_total?.toLocaleString('pt-BR') || '0', 
      icon: 'eye', 
      color: 'text-cyan-500', 
      bg: 'bg-cyan-100 dark:bg-cyan-900/20'
    },
    { 
      label: 'Downloads', 
      value: stats?.downloads_total?.toLocaleString('pt-BR') || '0', 
      icon: 'download', 
      color: 'text-pink-500', 
      bg: 'bg-pink-100 dark:bg-pink-900/20'
    },
    { 
      label: 'Artigos Destacados', 
      value: stats?.highlighted_articles || 0, 
      icon: 'star', 
      color: 'text-yellow-500', 
      bg: 'bg-yellow-100 dark:bg-yellow-900/20'
    },
  ];

  const quickActions = [
    {
      label: 'Sincronizar Todos os Feeds',
      icon: 'rss',
      onClick: handleSyncAllFeeds,
      loading: isSyncing,
      color: 'bg-blue-500 hover:bg-blue-600',
    },
    {
      label: 'Upload de PDF',
      icon: 'upload',
      onClick: () => router.push('/admin/articles?action=upload'),
      color: 'bg-green-500 hover:bg-green-600',
    },
    {
      label: 'Scrape URL',
      icon: 'globe',
      onClick: () => router.push('/admin/articles?action=scrape'),
      color: 'bg-purple-500 hover:bg-purple-600',
    },
    {
      label: 'Gerenciar Feeds',
      icon: 'settings',
      onClick: () => router.push('/admin/feeds'),
      color: 'bg-orange-500 hover:bg-orange-600',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header com status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Última atualização: {lastUpdate.toLocaleTimeString('pt-BR')}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={cn(
              "w-3 h-3 rounded-full",
              systemStatus === 'online' ? "bg-green-500 animate-pulse" : 
              systemStatus === 'offline' ? "bg-red-500" : "bg-yellow-500"
            )} />
            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
              {systemStatus === 'online' ? 'Online' : systemStatus === 'offline' ? 'Offline' : 'Verificando...'}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchStats}
            disabled={isLoading}
          >
            <Icon name={isLoading ? 'loader' : 'refresh'} size="sm" className={cn(isLoading && "animate-spin")} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {quickActions.map((action, index) => (
          <Button
            key={index}
            onClick={action.onClick}
            disabled={action.loading}
            className={cn(
              "h-auto p-4 flex flex-col items-center gap-2 text-white",
              action.color
            )}
          >
            <Icon 
              name={action.loading ? 'loader' : action.icon as any} 
              size="md" 
              className={cn(action.loading && "animate-spin")}
            />
            <span className="text-sm font-medium">{action.label}</span>
          </Button>
        ))}
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat, index) => (
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-500 dark:text-gray-400">
                {stat.label}
              </CardTitle>
              <div className={`p-2 rounded-full ${stat.bg}`}>
                <Icon name={stat.icon as any} className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              {stat.change !== undefined && (
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  +{stat.change} {stat.changeLabel}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Detailed Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Top Categories */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Icon name="folder" size="sm" />
              Top Categorias
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {detailedStats?.categories.slice(0, 5).map((cat, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">{cat.name}</span>
                  <Badge variant="outline">{cat.count}</Badge>
                </div>
              )) || (
                <p className="text-sm text-gray-500">Carregando...</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Top Feeds */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Icon name="rss" size="sm" />
              Top Feeds
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {detailedStats?.top_feeds.slice(0, 5).map((feed, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400 truncate">{feed.name}</span>
                  <Badge variant="outline">{feed.count}</Badge>
                </div>
              )) || (
                <p className="text-sm text-gray-500">Carregando...</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Top Authors */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Icon name="users" size="sm" />
              Top Autores
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {detailedStats?.top_authors.slice(0, 5).map((author, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400 truncate">{author.name}</span>
                  <Badge variant="outline">{author.count}</Badge>
                </div>
              )) || (
                <p className="text-sm text-gray-500">Carregando...</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Summary */}
      {analyticsSummary && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Icon name="barChart" size="sm" />
                Resumo de Analytics (Últimos 7 dias)
              </CardTitle>
              <Link href="/admin/analytics">
                <Button variant="outline" size="sm">
                  Ver Detalhes
                  <Icon name="arrowRight" size="sm" className="ml-1" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Sessões</p>
                <p className="text-2xl font-bold">{analyticsSummary.total_sessions?.toLocaleString('pt-BR') || 0}</p>
              </div>
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Visitantes Únicos</p>
                <p className="text-2xl font-bold">{analyticsSummary.unique_visitors?.toLocaleString('pt-BR') || 0}</p>
              </div>
              <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Page Views</p>
                <p className="text-2xl font-bold">{analyticsSummary.total_page_views?.toLocaleString('pt-BR') || 0}</p>
              </div>
              <div className="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Duração Média</p>
                <p className="text-2xl font-bold">
                  {analyticsSummary.avg_session_duration 
                    ? `${Math.round(analyticsSummary.avg_session_duration)}s`
                    : '0s'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Icon name="barChart" size="sm" />
            Status do Sistema
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-green-100 dark:bg-green-900/20 flex items-center justify-center">
                <Icon name="checkCircle" className="text-green-500" size="md" />
              </div>
              <div>
                <p className="text-sm font-medium">Backend</p>
                <p className="text-xs text-gray-500">Operacional</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900/20 flex items-center justify-center">
                <Icon name="database" className="text-blue-500" size="md" />
              </div>
              <div>
                <p className="text-sm font-medium">Banco de Dados</p>
                <p className="text-xs text-gray-500">Conectado</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-purple-100 dark:bg-purple-900/20 flex items-center justify-center">
                <Icon name="barChart" className="text-purple-500" size="md" />
              </div>
              <div>
                <p className="text-sm font-medium">IA/ML</p>
                <p className="text-xs text-gray-500">Ativo</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
