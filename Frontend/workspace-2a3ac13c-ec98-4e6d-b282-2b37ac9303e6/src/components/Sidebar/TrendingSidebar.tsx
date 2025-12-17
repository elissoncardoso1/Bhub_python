'use client';

import React, { useEffect, useState } from 'react';
import { Badge } from '@/components/Badge/Badge';
import { Icon } from '@/components/Icon/Icon';
import { cn, getCategoryColor } from '@/lib/utils';
import { Article } from '@/types/article';
import { ArticleService } from '@/services/articleService';
import { useRouter } from 'next/navigation';

interface TrendingSidebarProps {
  className?: string;
}

export function TrendingSidebar({ className }: TrendingSidebarProps) {
  const router = useRouter();
  const [trendingArticles, setTrendingArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrending = async () => {
      try {
        const articles = await ArticleService.getTrending(5);
        setTrendingArticles(articles);
      } catch (error) {
        console.error('Failed to fetch trending articles:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchTrending();
  }, []);

  const handleArticleClick = (id: number) => {
    router.push(`/articles/${id}`);
  };

  if (loading) {
    return (
      <aside className={cn('bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700', className)}>
        <div className="flex items-center gap-2 mb-6">
          <Icon name="trending" className="text-bhub-teal-primary" />
          <h3 className="font-display font-bold text-lg text-bhub-navy-dark dark:text-white">
            Em Alta
          </h3>
        </div>
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="animate-pulse flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-700" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </aside>
    );
  }

  return (
    <aside className={cn('bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-6">
        <Icon name="trending" className="text-bhub-teal-primary" />
        <h3 className="font-display font-bold text-lg text-bhub-navy-dark dark:text-white">
          Em Alta
        </h3>
      </div>

      {/* Trending Articles */}
      <div className="space-y-4">
        {trendingArticles.map((article, index) => (
          <article 
            key={article.id}
            className="pb-4 border-b border-gray-100 dark:border-gray-700 last:border-b-0 last:pb-0"
          >
            <div className="flex items-start gap-3">
              {/* Rank */}
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-bhub-navy-light dark:bg-bhub-navy-dark flex items-center justify-center">
                <span className="font-display font-bold text-xs text-bhub-navy-dark dark:text-white">
                  {index + 1}
                </span>
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h4 
                  className="font-body font-medium text-sm text-gray-900 dark:text-white mb-1 line-clamp-2 hover:text-bhub-teal-primary cursor-pointer transition-colors"
                  onClick={() => handleArticleClick(article.id)}
                >
                  {article.title}
                </h4>
                
                <div className="flex items-center gap-2 mb-2">
                  <Badge 
                    label={article.category?.name || 'Geral'}
                    variant="outline"
                    className={cn("text-[10px]", getCategoryColor(article.category?.name || 'Geral'))}
                  />
                  <div className="flex items-center gap-1">
                     <Icon name="trending" className="text-green-500 w-3 h-3" />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <p className="font-body font-light text-xs text-gray-600 dark:text-gray-400 line-clamp-1">
                    {article.authors?.[0]?.name || 'Autor Desconhecido'}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <Icon name="eye" size="sm" />
                    {article.view_count}
                  </div>
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>

      {/* View More Link */}
      <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-700">
        <a
          href="/articles?sort_by=view_count"
          className="flex items-center justify-center gap-2 text-sm font-body font-medium text-bhub-teal-primary hover:text-bhub-teal-primary/80 transition-colors"
        >
          Ver todos os artigos em alta
          <Icon name="chevronRight" size="sm" />
        </a>
      </div>
    </aside>
  );
}