'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { ArticleCardList } from '@/components/ArticleCard/ArticleCardList';
import { FilterSidebar } from '@/components/Sidebar/FilterSidebar';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { useArticleStore } from '@/store/articleStore';
import { useFilterStore } from '@/store/filterStore';
import { Article, articleToCardProps } from '@/types/article';

export function ArticlesPage() {
  const { 
    articles, 
    loading, 
    error, 
    fetchArticles,
    totalArticles,
    currentPage,
    totalPages,
    setPage
  } = useArticleStore();
  
  const { 
    categories, 
    authors, 
    dateRange, 
    searchTerm, 
    sortBy, 
    sortOrder,
    clearFilters 
  } = useFilterStore();
  
  const articlesPerPage = 12;

  useEffect(() => {
    // Fetch articles with current filters
    fetchArticles({
      search: searchTerm || undefined,
      category_id: categories.length > 0 ? Number(categories[0]) : undefined,
      sort_by: sortBy === 'date' ? 'publication_date' : sortBy === 'citations' ? 'view_count' : 'title',
      sort_order: sortOrder,
      page: currentPage,
      limit: articlesPerPage,
    });
  }, [fetchArticles, searchTerm, categories, sortBy, sortOrder, currentPage]);

  // Client-side additional filtering (for author filter which backend supports)
  const filteredArticles = articles.filter(article => {
    const matchesSearch = !searchTerm || 
      article.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (article.abstract?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false);
    
    // Author matching - check if any author name contains the filter
    const matchesAuthor = authors.length === 0 || 
      article.authors.some(a => authors.some(filterAuthor => 
        a.name.toLowerCase().includes(filterAuthor.toLowerCase())
      ));
    
    return matchesSearch && matchesAuthor;
  });

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages && page !== currentPage) {
      setPage(page);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Generate smart page numbers (show first, last, and around current)
  const getPageNumbers = (): (number | string)[] => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    
    const pages: (number | string)[] = [];
    
    // Always show first page
    pages.push(1);
    
    // Show ellipsis if current page is far from start
    if (currentPage > 3) {
      pages.push('...');
    }
    
    // Show pages around current
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
      if (!pages.includes(i)) {
        pages.push(i);
      }
    }
    
    // Show ellipsis if current page is far from end
    if (currentPage < totalPages - 2) {
      pages.push('...');
    }
    
    // Always show last page
    if (!pages.includes(totalPages)) {
      pages.push(totalPages);
    }
    
    return pages;
  };


  const hasActiveFilters = categories.length > 0 || authors.length > 0 || dateRange !== 'all' || searchTerm !== '';

  if (loading) {
    return (
      <MainLayout>
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-center min-h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-bhub-teal-primary"></div>
          </div>
        </main>
        <Footer />
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout>
        <Header />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-12">
            <Icon name="alert" className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="font-display font-bold text-xl text-gray-900 dark:text-white mb-2">
              Erro ao carregar artigos
            </h2>
            <p className="font-body font-light text-gray-600 dark:text-gray-400 mb-4">
              {error}
            </p>
            <Button onClick={() => fetchArticles()}>
              Tentar novamente
            </Button>
          </div>
        </main>
        <Footer />
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Desktop Layout */}
        <div className="hidden lg:grid grid-cols-[240px_1fr] gap-6">
          {/* Sidebar */}
          <div className="space-y-6">
            <FilterSidebar />
          </div>
          
          {/* Main Content */}
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="font-display font-bold text-2xl text-bhub-navy-dark dark:text-white mb-2">
                  Todos os Artigos
                </h1>
                <p className="font-body font-light text-gray-600 dark:text-gray-400">
                  {totalArticles} artigo{totalArticles !== 1 ? 's' : ''} encontrado{totalArticles !== 1 ? 's' : ''}
                </p>
              </div>
              
              {hasActiveFilters && (
                <Button
                  variant="outline"
                  onClick={clearFilters}
                  className="flex items-center gap-2"
                >
                  <Icon name="close" size="sm" />
                  Limpar Filtros
                </Button>
              )}
            </div>
            
            {/* Articles Grid */}
            {filteredArticles.length > 0 ? (
              <>
                <ArticleCardList 
                  articles={filteredArticles.map(article => articleToCardProps(article))}
                  columns={3}
                />
                
                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center gap-2 pt-6">
                    <Button
                      variant="outline"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="flex items-center gap-2"
                    >
                      <Icon name="chevronLeft" size="sm" />
                      Anterior
                    </Button>
                    
                    <div className="flex items-center gap-1">
                      {getPageNumbers().map((page, index) => (
                        typeof page === 'number' ? (
                          <Button
                            key={page}
                            variant={currentPage === page ? "default" : "outline"}
                            onClick={() => handlePageChange(page)}
                            className="w-10 h-10 p-0"
                          >
                            {page}
                          </Button>
                        ) : (
                          <span key={`ellipsis-${index}`} className="px-2 text-gray-400">
                            {page}
                          </span>
                        )
                      ))}
                    </div>
                    
                    <Button
                      variant="outline"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="flex items-center gap-2"
                    >
                      Próximo
                      <Icon name="chevronRight" size="sm" />
                    </Button>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-12">
                <Icon name="search" className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="font-display font-bold text-lg text-gray-900 dark:text-white mb-2">
                  Nenhum artigo encontrado
                </h3>
                <p className="font-body font-light text-gray-600 dark:text-gray-400 mb-4">
                  Tente ajustar seus filtros ou termos de busca
                </p>
                <Button onClick={clearFilters}>
                  Limpar todos os filtros
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Mobile/Tablet Layout */}
        <div className="lg:hidden space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white mb-2">
                Todos os Artigos
              </h1>
              <p className="font-body font-light text-gray-600 dark:text-gray-400">
                {totalArticles} artigo{totalArticles !== 1 ? 's' : ''} encontrado{totalArticles !== 1 ? 's' : ''}
              </p>
            </div>
            
            {hasActiveFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={clearFilters}
                className="flex items-center gap-2"
              >
                <Icon name="close" size="sm" />
                Limpar
              </Button>
            )}
          </div>
          
          {/* Filter Sidebar (Mobile) */}
          <FilterSidebar />
          
          {/* Articles Grid */}
          {filteredArticles.length > 0 ? (
            <>
              <ArticleCardList 
                articles={filteredArticles.map(article => articleToCardProps(article))}
                columns={1}
              />
              
              {/* Mobile Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    <Icon name="chevronLeft" size="sm" />
                  </Button>
                  
                  <span className="font-body font-medium text-sm text-gray-600 dark:text-gray-400">
                    {currentPage} de {totalPages}
                  </span>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    <Icon name="chevronRight" size="sm" />
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-12">
              <Icon name="search" className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="font-display font-bold text-lg text-gray-900 dark:text-white mb-2">
                Nenhum artigo encontrado
              </h3>
              <p className="font-body font-light text-gray-600 dark:text-gray-400 mb-4">
                Tente ajustar seus filtros ou termos de busca
              </p>
              <Button onClick={clearFilters}>
                Limpar todos os filtros
              </Button>
            </div>
          )}
        </div>
      </main>
      
      <Footer />
    </MainLayout>
  );
}