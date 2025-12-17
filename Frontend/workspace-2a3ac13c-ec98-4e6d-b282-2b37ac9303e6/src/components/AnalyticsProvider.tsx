'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { AnalyticsService } from '@/services/analyticsService';

/**
 * Provider de Analytics que rastreia automaticamente page views
 * Respeita o header Do Not Track do navegador
 */
export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  useEffect(() => {
    // Verificar se o usuário optou por não ser rastreado
    if (typeof navigator !== 'undefined' && navigator.doNotTrack === '1') {
      return;
    }

    // Aguardar um pouco para garantir que a página carregou
    const timer = setTimeout(() => {
      AnalyticsService.trackPageView(pathname);
    }, 100);

    return () => clearTimeout(timer);
  }, [pathname]);

  return <>{children}</>;
}

