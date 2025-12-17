'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { AnalyticsService } from '@/services/analyticsService';

/**
 * Hook para tracking automático de page views
 */
export function useAnalytics() {
  const pathname = usePathname();

  useEffect(() => {
    // Aguardar um pouco para garantir que a página carregou
    const timer = setTimeout(() => {
      AnalyticsService.trackPageView(pathname);
    }, 100);

    return () => clearTimeout(timer);
  }, [pathname]);
}

/**
 * Hook para tracking de eventos customizados
 */
export function useTrackEvent() {
  return {
    trackEvent: (
      eventType: string,
      eventName: string,
      properties?: Record<string, any>
    ) => {
      AnalyticsService.trackEvent(
        eventType,
        eventName,
        properties,
        window.location.pathname,
        document.referrer
      );
    },
    trackArticleView: (articleId: number, articleTitle: string) => {
      AnalyticsService.trackEvent(
        'article_view',
        'article_view',
        {
          article_id: articleId,
          article_title: articleTitle,
        },
        window.location.pathname,
        document.referrer
      );
    },
    trackArticleDownload: (articleId: number, articleTitle: string) => {
      AnalyticsService.trackEvent(
        'article_download',
        'article_download',
        {
          article_id: articleId,
          article_title: articleTitle,
        },
        window.location.pathname,
        document.referrer
      );
    },
    trackSearch: (query: string, resultsCount: number) => {
      AnalyticsService.trackEvent(
        'search',
        'search',
        {
          query,
          results_count: resultsCount,
        },
        window.location.pathname,
        document.referrer
      );
    },
    trackCategoryClick: (categoryId: number, categoryName: string) => {
      AnalyticsService.trackEvent(
        'category_click',
        'category_click',
        {
          category_id: categoryId,
          category_name: categoryName,
        },
        window.location.pathname,
        document.referrer
      );
    },
    trackAuthorClick: (authorId: number, authorName: string) => {
      AnalyticsService.trackEvent(
        'author_click',
        'author_click',
        {
          author_id: authorId,
          author_name: authorName,
        },
        window.location.pathname,
        document.referrer
      );
    },
  };
}

