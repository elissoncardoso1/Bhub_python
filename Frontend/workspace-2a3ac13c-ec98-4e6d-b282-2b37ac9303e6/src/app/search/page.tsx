'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { ArticleCardList } from '@/components/ArticleCard/ArticleCardList';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { SearchService } from '@/services/searchService';
import { CategoryService } from '@/services/categoryService';
import { Article, Category } from '@/types/article';
import { articleToCardProps } from '@/types/article';

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams?.get('q') || '';
  
  const [searchTerm, setSearchTerm] = useState(initialQuery);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [isSearched, setIsSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<Article[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch categories for the dropdown
    CategoryService.getAll().then(setCategories).catch(console.error);
    
    // Initial search if query param exists
    if (initialQuery) {
        performSearch(initialQuery);
    }
  }, []);

  const performSearch = async (term: string, categoryId?: string) => {
    if (!term.trim()) return;

    setIsLoading(true);
    setIsSearched(true);
    setError(null);

    try {
        const catId = categoryId && categoryId !== 'all' ? [parseInt(categoryId)] : undefined;
        const response = await SearchService.search({
            search: term,
            category_id: catId,
            page_size: 20
        });
        setResults(response.items || []); // Backend uses 'items' in PaginatedResponse usually, check Api types
        setTotalResults(response.total || 0);
    } catch (err) {
        console.error('Search error:', err);
        setError('Ocorreu um erro ao buscar artigos. Tente novamente.');
        setResults([]);
    } finally {
        setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    performSearch(searchTerm, selectedCategory);
  };

  const clearSearch = () => {
    setSearchTerm('');
    setSelectedCategory('');
    setIsSearched(false);
    setResults([]);
    setError(null);
  };

  const articleCards = results.map(articleToCardProps);

  return (
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Search Header */}
          <div className="text-center mb-12">
            <h1 className="font-display font-bold text-4xl text-bhub-navy-dark dark:text-white mb-4">
              Buscar Artigos
            </h1>
            <p className="font-body font-light text-lg text-gray-600 dark:text-gray-400">
              Encontre artigos, autores e tópicos de seu interesse
            </p>
          </div>

          {/* Search Form */}
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700 mb-8">
            <form onSubmit={handleSearch} className="space-y-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Icon 
                      name="search" 
                      className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                    />
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Buscar artigos, autores ou palavras-chave..."
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>
                </div>
                
                <div className="md:w-64">
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="">Todas as categorias</option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </div>

                <Button
                  type="submit"
                  variant="default"
                  className="bg-bhub-teal-primary hover:bg-bhub-teal-primary/90"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="animate-spin mr-2">⟳</span>
                  ) : (
                    <Icon name="search" size="sm" />
                  )}
                  Buscar
                </Button>
              </div>

            <div className="flex flex-wrap gap-2">
                <span className="font-body font-medium text-sm text-gray-700 dark:text-gray-300">
                  Buscas populares:
                </span>
                {['Autismo', 'Comportamento Verbal', 'Terapia', 'Educação'].map((term) => (
                  <Button
                    key={term}
                    variant="outline"
                    size="sm"
                    type="button"
                    onClick={() => {
                        setSearchTerm(term);
                        performSearch(term, selectedCategory);
                    }}
                    className="text-xs"
                  >
                    {term}
                  </Button>
                ))}
            </div>
            </form>
          </div>

          {/* Search Results */}
          {isSearched && (
            <div>
              {/* Results Header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="font-display font-bold text-2xl text-bhub-navy-dark dark:text-white mb-2">
                    Resultados da Busca
                  </h2>
                  <p className="font-body font-light text-gray-600 dark:text-gray-400">
                    {isLoading 
                        ? 'Buscando...' 
                        : `${totalResults} resultados encontrados para "${searchTerm}"`
                    }
                  </p>
                </div>
                
                <Button
                  variant="outline"
                  onClick={clearSearch}
                  className="flex items-center gap-2"
                >
                  <Icon name="close" size="sm" />
                  Limpar Busca
                </Button>
              </div>

              {/* Error Message */}
              {error && (
                   <div className="bg-red-50 text-red-600 p-4 rounded-md mb-6">
                       {error}
                   </div>
              )}

              {/* Results List */}
              {!isLoading && (
                  results.length > 0 ? (
                    <ArticleCardList 
                      articles={articleCards}
                      columns={2}
                    />
                  ) : (
                    <div className="text-center py-12">
                      <Icon name="search" className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                      <h3 className="font-display font-bold text-xl text-gray-900 dark:text-white mb-2">
                        Nenhum resultado encontrado
                      </h3>
                      <p className="font-body font-light text-gray-600 dark:text-gray-400 mb-6">
                        Tente usar termos diferentes ou verifique a ortografia
                      </p>
                      <Button
                        variant="outline"
                        onClick={clearSearch}
                      >
                        Nova Busca
                      </Button>
                    </div>
                  )
              )}
              
              {isLoading && (
                  <div className="flex justify-center py-20">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-bhub-teal-primary"></div>
                  </div>
              )}
            </div>
          )}

          {/* Search Tips */}
          {!isSearched && !isLoading && (
            <div className="bg-bhub-navy-light dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
              <h3 className="font-display font-bold text-xl text-bhub-navy-dark dark:text-white mb-4">
                Dicas de Busca
              </h3>
              <div className="space-y-3 font-body font-light text-gray-700 dark:text-gray-300">
                <p className="flex items-start gap-2">
                  <span className="text-bhub-teal-primary">•</span>
                  <span>Use termos específicos como "análise funcional" em vez de "comportamento"</span>
                </p>
                <p className="flex items-start gap-2">
                  <span className="text-bhub-teal-primary">•</span>
                  <span>Busque por nomes de autores ou palavras-chave específicas</span>
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
  );
}

export default function Search() {
  return (
    <MainLayout>
      <Header />
      <Suspense fallback={<div>Carregando...</div>}>
        <SearchContent />
      </Suspense>
      <Footer />
    </MainLayout>
  );
}