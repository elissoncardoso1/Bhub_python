'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { Badge } from '@/components/Badge/Badge';
import { AuthorAvatar } from '@/components/Avatar/Avatar';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { TranslationPanel } from '@/components/Translation/TranslationPanel';
import { ShareableArticleHeader } from '@/components/ArticleCard/ShareableArticleHeader';
import { AbstractHighlightBlock } from '@/components/ArticleCard/AbstractHighlightBlock';
import { formatDate, getCategoryColor, cn } from '@/lib/utils';
import { Article } from '@/types/article';
import { ArticleService } from '@/services/articleService';

interface ArticleDetailPageProps {
  articleId?: string;
}

export function ArticleDetailPage({ articleId }: ArticleDetailPageProps) {
  const [isLiked, setIsLiked] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [activeTab, setActiveTab] = useState('abstract');
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!articleId) {
      setError('ID do artigo não fornecido');
      setLoading(false);
      return;
    }

    const fetchArticle = async () => {
      try {
        setLoading(true);
        const data = await ArticleService.getById(Number(articleId));
        setArticle(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching article:', err);
        setError('Erro ao carregar artigo');
      } finally {
        setLoading(false);
      }
    };

    fetchArticle();
  }, [articleId]);

  const handleLike = () => {
    setIsLiked(!isLiked);
  };

  const handleBookmark = () => {
    setIsBookmarked(!isBookmarked);
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: article?.title || '',
        text: article?.abstract || '',
        url: window.location.href
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
    }
  };

  const handleDownload = () => {
    if (article?.pdf_url) {
      window.open(article.pdf_url, '_blank');
    } else if (article?.original_url) {
      window.open(article.original_url, '_blank');
    }
  };

  const tabs = [
    { id: 'abstract', label: 'Resumo' },
    { id: 'content', label: 'Conteúdo Completo' },
    { id: 'metrics', label: 'Métricas' }
  ];

  // Loading state
  if (loading) {
    return (
      <MainLayout>
        <Header />
        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center min-h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-bhub-teal-primary"></div>
          </div>
        </main>
        <Footer />
      </MainLayout>
    );
  }

  // Error state
  if (error || !article) {
    return (
      <MainLayout>
        <Header />
        <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-12">
            <Icon name="alert" className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="font-display font-bold text-xl text-gray-900 dark:text-white mb-2">
              {error || 'Artigo não encontrado'}
            </h2>
            <Button onClick={() => window.history.back()}>
              Voltar
            </Button>
          </div>
        </main>
        <Footer />
      </MainLayout>
    );
  }

  // Get primary author and format data
  const primaryAuthor = article.authors?.[0];
  const authorName = primaryAuthor?.name || 'Autor desconhecido';
  const authorInitials = authorName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  const categoryLabel = article.category?.name || 'Sem categoria';

  const readingTime = Math.ceil((article.abstract?.length || 500) / 1000) + 3;


  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-8 lg:py-10">
        {/* 
          SCREENSHOT-FRIENDLY LAYOUT
          ==========================
          Layout otimizado para screenshots com:
          - Header contido e visualmente isolado
          - Abstract destacado como bloco standalone
          - Margens seguras para cropping (1:1, 9:16, 4:5)
          - Branding sutil do BHub
        */}

        {/* Shareable Article Header - Screenshot-Safe Card */}
        <ShareableArticleHeader article={article} />

        {/* Abstract Highlight Block - Standalone Visual Card */}
        <AbstractHighlightBlock 
          article={article} 
          showTranslationLabel={!!article.abstract_translated}
        />

        {/* Authors Section - Discreto, abaixo do abstract */}
        {primaryAuthor && (
          <div className="max-w-3xl mx-auto mb-6 md:mb-8">
            <div className="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-800">
              <AuthorAvatar 
                name={authorName}
                initials={authorInitials}
                size="md"
              />
              <div className="flex-1 min-w-0">
                <p className="font-body font-medium text-sm md:text-base text-gray-900 dark:text-white truncate">
                  {authorName}
                </p>
                <p className="font-body font-light text-xs md:text-sm text-gray-600 dark:text-gray-400 truncate">
                  {primaryAuthor?.affiliation || article.journal_name || 'Afiliação não disponível'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons - Posicionados após conteúdo principal para não interferir em screenshots */}
        <div className="max-w-3xl mx-auto mb-8">
          <div className="flex flex-wrap items-center gap-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
            <Button
              variant="default"
              onClick={handleDownload}
              className="bg-bhub-teal-primary hover:bg-bhub-teal-primary/90"
              size="sm"
            >
              <Icon name="download" size="sm" />
              {article.original_url ? 'Ver Original' : 'Baixar PDF'}
            </Button>
            
            <Button
              variant="outline"
              onClick={handleLike}
              className={isLiked ? 'text-bhub-red-accent dark:text-red-400 border-bhub-red-accent dark:border-red-400' : ''}
              size="sm"
            >
              <Icon name="heart" size="sm" />
              {isLiked ? 'Curtido' : 'Curtir'}
            </Button>
            
            <Button
              variant="outline"
              onClick={handleBookmark}
              className={isBookmarked ? 'text-bhub-yellow-primary dark:text-yellow-400 border-bhub-yellow-primary dark:border-yellow-400' : ''}
              size="sm"
            >
              <Icon name="bookmark" size="sm" />
              {isBookmarked ? 'Salvo' : 'Salvar'}
            </Button>
            
            <Button
              variant="outline"
              onClick={handleShare}
              size="sm"
            >
              <Icon name="share" size="sm" />
              Compartilhar
            </Button>
          </div>
        </div>

        {/* Content Tabs - Secundário, não interfere em screenshots principais */}
        <div className="max-w-3xl mx-auto mb-8">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex space-x-8">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-bhub-teal-primary text-bhub-teal-primary'
                      : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Tab Content - Conteúdo secundário */}
        <div className="max-w-3xl mx-auto">
          <div className="prose prose-lg dark:prose-invert max-w-none">
          {activeTab === 'abstract' && (
            <div className="space-y-4">
              <div className="font-body font-light text-gray-700 dark:text-gray-300 leading-relaxed">
                {article.abstract || 'Resumo não disponível.'}
              </div>
              {article.abstract && (
                <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                  <TranslationPanel
                    originalText={article.abstract}
                    sourceLang="en"
                    targetLang="pt-BR"
                    title="Traduzir Resumo"
                  />
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'content' && (
            <div className="font-body font-light text-gray-700 dark:text-gray-300 leading-relaxed">
              {article.abstract_translated ? (
                <>
                  <h3 className="font-display font-bold text-lg mb-4">Versão Traduzida</h3>
                  <p>{article.abstract_translated}</p>
                  <hr className="my-6" />
                  <h3 className="font-display font-bold text-lg mb-4">Versão Original</h3>
                  <p>{article.abstract}</p>
                </>
              ) : (
                <div className="space-y-6">
                  <p>{article.abstract || 'Conteúdo completo não disponível. Acesse o link original para mais informações.'}</p>
                  {article.abstract && (
                    <TranslationPanel
                      originalText={article.abstract}
                      sourceLang="en"
                      targetLang="pt-BR"
                      title="Traduzir Conteúdo"
                    />
                  )}
                </div>
              )}
              {article.original_url && (
                <div className="mt-6">
                  <a 
                    href={article.original_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-bhub-teal-primary hover:underline"
                  >
                    Acessar artigo original →
                  </a>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'metrics' && (
            <div className="space-y-6">
              <h3 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white mb-4">
                Métricas e Impacto
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <h4 className="font-body font-semibold text-gray-900 dark:text-white mb-2">
                    Engajamento
                  </h4>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-400">Visualizações</span>
                      <span className="font-medium">{article.view_count || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-400">Downloads</span>
                      <span className="font-medium">{article.download_count || 0}</span>
                    </div>
                  </div>
                </div>
                
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                  <h4 className="font-body font-semibold text-gray-900 dark:text-white mb-2">
                    Informações da Publicação
                  </h4>
                  <div className="space-y-2">
                    {article.journal_name && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Periódico</span>
                        <span className="font-medium">{article.journal_name}</span>
                      </div>
                    )}
                    {article.language && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">Idioma</span>
                        <span className="font-medium">{article.language === 'pt' ? 'Português' : article.language === 'en' ? 'Inglês' : article.language}</span>
                      </div>
                    )}
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600 dark:text-gray-400">Score de Impacto</span>
                      <span className="font-medium">{article.impact_score?.toFixed(1) || 'N/A'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          </div>
        </div>

        {/* Keywords - Secundário, não interfere em screenshots */}
        {article.keywords && (
          <div className="max-w-3xl mx-auto mt-8 pt-8 border-t border-gray-200 dark:border-gray-700">
            <h3 className="font-body font-semibold text-sm text-gray-900 dark:text-white mb-3">
              Palavras-chave
            </h3>
            <div className="flex flex-wrap gap-2">
              {article.keywords.split(',').map((keyword) => (
                <Badge
                  key={keyword.trim()}
                  label={keyword.trim()}
                  variant="light"
                  className="text-xs"
                />
              ))}
            </div>
          </div>
        )}
      </main>
      
      <Footer />
    </MainLayout>
  );
}