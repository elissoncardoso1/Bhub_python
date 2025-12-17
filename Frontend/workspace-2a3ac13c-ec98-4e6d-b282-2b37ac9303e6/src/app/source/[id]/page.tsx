'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useParams } from 'next/navigation';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { ArticleCardList } from '@/components/ArticleCard/ArticleCardList';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { Badge } from '@/components/Badge/Badge';
import { FeedService, Feed } from '@/services/feedService';
import { SearchService } from '@/services/searchService';
import { Article, articleToCardProps } from '@/types/article';

export default function SourcePage() {
  const params = useParams();
  const feedId = params?.id ? parseInt(Array.isArray(params.id) ? params.id[0] : params.id) : null;
  
  const [feed, setFeed] = useState<Feed | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
        if (!feedId) return;
        
        setIsLoading(true);
        try {
            const [feedData, articlesData] = await Promise.all([
                FeedService.getById(feedId),
                SearchService.search({ feed_id: feedId, page_size: 20 })
            ]);
            
            if (!feedData) {
                setError('Fonte não encontrada');
            } else {
                setFeed(feedData);
                setArticles(articlesData.items || []);
            }
        } catch (err) {
            console.error(err);
            setError('Erro ao carregar dados da fonte');
        } finally {
            setIsLoading(false);
        }
    };
    
    fetchData();
  }, [feedId]);

  if (isLoading) {
      return (
        <MainLayout>
          <Header />
            <div className="flex justify-center py-20 min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-bhub-teal-primary"></div>
            </div>
          <Footer />
        </MainLayout>
      );
  }

  if (error || !feed) {
      return (
        <MainLayout>
          <Header />
            <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center min-h-screen">
                <Icon name="alert" className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{error || 'Fonte não encontrada'}</h1>
                <Button variant="outline" onClick={() => window.history.back()}>Voltar</Button>
            </main>
          <Footer />
        </MainLayout>
      );
  }

  return (
    <MainLayout>
      <Header />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg p-8 shadow-sm border border-gray-100 dark:border-gray-700 mb-12 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-bhub-teal-primary/10 text-bhub-teal-primary mb-6">
                <Icon name="bookmark" size="lg" />
            </div>
            <h1 className="font-display font-bold text-4xl text-bhub-navy-dark dark:text-white mb-4">
                {feed.name}
            </h1>
            {feed.description && (
                <p className="font-body font-light text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto mb-6">
                    {feed.description}
                </p>
            )}
            
            <div className="flex justify-center gap-4">
                {feed.website_url && (
                    <a href={feed.website_url} target="_blank" rel="noopener noreferrer">
                        <Button variant="outline" className="flex items-center gap-2">
                            <Icon name="external" size="sm" />
                            Visitar Website
                        </Button>
                    </a>
                )}
            </div>
        </div>

        {/* Articles */}
        <div className="mb-8">
            <h2 className="font-display font-bold text-2xl text-bhub-navy-dark dark:text-white mb-6">
                Artigos Recentes
            </h2>
            {articles.length > 0 ? (
                <ArticleCardList 
                    articles={articles.map(articleToCardProps)}
                    columns={3}
                />
            ) : (
                <p className="text-gray-500 text-center py-12">Nenhum artigo encontrado desta fonte recentemente.</p>
            )}
        </div>
      </main>
      <Footer />
    </MainLayout>
  );
}
