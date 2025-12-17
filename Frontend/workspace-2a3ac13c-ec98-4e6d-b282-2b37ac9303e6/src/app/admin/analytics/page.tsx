'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { Icon } from '@/components/Icon/Icon';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AnalyticsService, AnalyticsOverview } from '@/services/analyticsService';
import { AnalyticsCards } from '@/components/Admin/AnalyticsCards';
import { AnalyticsCharts } from '@/components/Admin/AnalyticsCharts';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

export default function AnalyticsPage() {
  const { data: session } = useSession();
  const { toast } = useToast();
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [period, setPeriod] = useState<number>(30);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchAnalytics = useCallback(async () => {
    if (!session?.accessToken) return;

    setIsLoading(true);
    try {
      const data = await AnalyticsService.getOverview(session.accessToken as string, period);
      setAnalytics(data);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Erro ao buscar analytics:', error);
      toast({
        title: 'Erro',
        description: 'Não foi possível carregar os dados de analytics',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [session, period, toast]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gray-900 dark:text-white">
            Analytics
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Métricas e estatísticas de uso da plataforma
          </p>
          {lastUpdate && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Última atualização: {lastUpdate.toLocaleTimeString('pt-BR')}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <Select
            value={period.toString()}
            onValueChange={(value) => setPeriod(Number(value))}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Período" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Últimos 7 dias</SelectItem>
              <SelectItem value="30">Últimos 30 dias</SelectItem>
              <SelectItem value="90">Últimos 90 dias</SelectItem>
              <SelectItem value="365">Último ano</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchAnalytics}
            disabled={isLoading}
          >
            <Icon 
              name={isLoading ? 'loader' : 'refresh'} 
              size="sm" 
              className={cn(isLoading && 'animate-spin')} 
            />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Aviso de Transparência */}
      <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Icon name="info" className="text-blue-500 mt-0.5" size="sm" />
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                Transparência de Dados
              </h3>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                Os dados de analytics são coletados de forma anônima e agregada. 
                Não coletamos informações pessoais identificáveis. Os dados são usados 
                exclusivamente para melhorar a experiência do usuário e entender o uso da plataforma.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Icon name="loader" className="animate-spin text-gray-400" size="lg" />
          <span className="ml-2 text-gray-500">Carregando analytics...</span>
        </div>
      ) : analytics ? (
        <>
          {/* Cards de Métricas */}
          <AnalyticsCards traffic={analytics.traffic} content={analytics.content} />

          {/* Gráficos */}
          <AnalyticsCharts
            timeSeriesData={analytics.time_series}
            topPages={analytics.top_pages}
            eventsStats={analytics.events}
          />

          {/* Tabela de Top Páginas */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon name="barChart" size="sm" />
                Páginas Mais Visitadas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-4 font-medium text-gray-700 dark:text-gray-300">
                        Página
                      </th>
                      <th className="text-right py-2 px-4 font-medium text-gray-700 dark:text-gray-300">
                        Visualizações
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.top_pages.map((page, index) => (
                      <tr key={index} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="py-2 px-4 text-sm text-gray-600 dark:text-gray-400">
                          {page.path || '/'}
                        </td>
                        <td className="py-2 px-4 text-sm text-right font-medium">
                          {page.views.toLocaleString('pt-BR')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Resumo de Eventos */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Icon name="activity" size="sm" />
                Resumo de Eventos
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                    Total de Eventos
                  </p>
                  <p className="text-2xl font-bold">
                    {analytics.events.total_events.toLocaleString('pt-BR')}
                  </p>
                </div>
                {Object.entries(analytics.events.events_by_type || {}).map(([type, count]) => (
                  <div key={type} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                      {type.replace('_', ' ').toUpperCase()}
                    </p>
                    <p className="text-2xl font-bold">{count.toLocaleString('pt-BR')}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <Icon name="alertCircle" className="mx-auto text-gray-400 mb-2" size="lg" />
            <p className="text-gray-500">Nenhum dado de analytics disponível</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

