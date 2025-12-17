'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Header } from '@/components/Layout/Header';
import { Footer } from '@/components/Layout/Footer';
import { MainLayout } from '@/components/Layout/MainLayout';
import { AdvancedSearchBar } from '@/components/Repository/AdvancedSearchBar';
import { FilterPanel, FilterState } from '@/components/Repository/FilterPanel';
import { SearchResults } from '@/components/Repository/SearchResults';
import { ActiveFilters } from '@/components/Repository/ActiveFilters';
import { Icon } from '@/components/Icon/Icon';
import { ArticleService } from '@/services/articleService';
import { CategoryService } from '@/services/categoryService';
import { FeedService } from '@/services/feedService';
import { Article, Category, PaginatedArticleResponse } from '@/types/article';
import { Feed } from '@/services/feedService';

const DEFAULT_FILTERS: FilterState = {
  sourceType: [],
  feedIds: [],
  categoryIds: [],
  languages: [],
  dateFrom: '',
  dateTo: '',
  author: '',
  hasPdf: null,
  highlighted: null,
  sortBy: 'publication_date',
  sortOrder: 'desc',
};

export function RepositoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 0,
  });

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [categoriesData, feedsData] = await Promise.all([
          CategoryService.getAll(),
          FeedService.getAll(),
        ]);
        setCategories(categoriesData);
        setFeeds(feedsData);
      } catch (error) {
        console.error('Error loading initial data:', error);
      }
    };
    loadInitialData();
  }, []);

  // Load filters from URL params
  useEffect(() => {
    const query = searchParams.get('q') || '';
    const page = parseInt(searchParams.get('page') || '1', 10);
    
    setSearchQuery(query);
    setPagination(prev => ({ ...prev, page }));

    // Load filters from URL if present
    const urlFilters: Partial<FilterState> = {};
    const sourceType = searchParams.get('source_type');
    if (sourceType) {
      urlFilters.sourceType = sourceType.split(',') as ('journal' | 'portal')[];
    }
    const categoryIds = searchParams.get('category_id');
    if (categoryIds) {
      urlFilters.categoryIds = categoryIds.split(',').map(Number);
    }
    const feedIds = searchParams.get('feed_id');
    if (feedIds) {
      urlFilters.feedIds = feedIds.split(',').map(Number);
    }
    const languages = searchParams.get('language');
    if (languages) {
      urlFilters.languages = languages.split(',');
    }
    const dateFrom = searchParams.get('date_from');
    if (dateFrom) {
      urlFilters.dateFrom = dateFrom;
    }
    const dateTo = searchParams.get('date_to');
    if (dateTo) {
      urlFilters.dateTo = dateTo;
    }
    const author = searchParams.get('author');
    if (author) {
      urlFilters.author = author;
    }
    const hasPdf = searchParams.get('has_pdf');
    if (hasPdf) {
      urlFilters.hasPdf = hasPdf === 'true';
    }
    const highlighted = searchParams.get('highlighted');
    if (highlighted) {
      urlFilters.highlighted = highlighted === 'true';
    }
    const sortBy = searchParams.get('sort_by');
    if (sortBy) {
      urlFilters.sortBy = sortBy as FilterState['sortBy'];
    }
    const sortOrder = searchParams.get('sort_order');
    if (sortOrder) {
      urlFilters.sortOrder = sortOrder as FilterState['sortOrder'];
    }

    if (Object.keys(urlFilters).length > 0) {
      setFilters(prev => ({ ...prev, ...urlFilters }));
    }
  }, [searchParams]);

  // Update URL with current search state
  const updateURL = useCallback((query: string, filters: FilterState, page: number) => {
    const params = new URLSearchParams();
    
    if (query) params.set('q', query);
    if (page > 1) params.set('page', page.toString());
    
    if (filters.sourceType.length > 0) {
      params.set('source_type', filters.sourceType.join(','));
    }
    if (filters.categoryIds.length > 0) {
      params.set('category_id', filters.categoryIds.join(','));
    }
    if (filters.feedIds.length > 0) {
      params.set('feed_id', filters.feedIds.join(','));
    }
    if (filters.languages.length > 0) {
      params.set('language', filters.languages.join(','));
    }
    if (filters.dateFrom) {
      params.set('date_from', filters.dateFrom);
    }
    if (filters.dateTo) {
      params.set('date_to', filters.dateTo);
    }
    if (filters.author) {
      params.set('author', filters.author);
    }
    if (filters.hasPdf !== null) {
      params.set('has_pdf', filters.hasPdf.toString());
    }
    if (filters.highlighted !== null) {
      params.set('highlighted', filters.highlighted.toString());
    }
    if (filters.sortBy !== DEFAULT_FILTERS.sortBy) {
      params.set('sort_by', filters.sortBy);
    }
    if (filters.sortOrder !== DEFAULT_FILTERS.sortOrder) {
      params.set('sort_order', filters.sortOrder);
    }

    const newURL = params.toString() ? `?${params.toString()}` : '';
    router.replace(`/repository${newURL}`, { scroll: false });
  }, [router]);

  // Perform search
  const performSearch = useCallback(async (query: string, currentFilters: FilterState, page: number) => {
    setIsLoading(true);
    try {
      const params: any = {
        page,
        limit: pagination.pageSize,
        sort_by: currentFilters.sortBy,
        sort_order: currentFilters.sortOrder,
      };

      if (query) {
        params.search = query;
      }

      // Apply filters
      if (currentFilters.categoryIds.length > 0) {
        // Backend expects single category_id, but we can pass multiple
        params.category_id = currentFilters.categoryIds[0]; // TODO: Support multiple categories
      }
      
      if (currentFilters.sourceType.length > 0) {
        // If both selected, don't filter; if only one, filter
        if (currentFilters.sourceType.length === 1) {
          params.source_category = currentFilters.sourceType[0];
        }
      }
      
      // Backend only supports single feed_id, so we use the first selected feed
      // If multiple feeds are selected, we'll need to make multiple requests or update backend
      if (currentFilters.feedIds.length > 0 && currentFilters.feedIds[0]) {
        params.feed_id = currentFilters.feedIds[0];
      }
      
      if (currentFilters.dateFrom) {
        params.date_from = currentFilters.dateFrom;
      }
      
      if (currentFilters.dateTo) {
        params.date_to = currentFilters.dateTo;
      }
      
      if (currentFilters.author) {
        params.author = currentFilters.author;
      }
      
      if (currentFilters.hasPdf !== null) {
        params.has_pdf = currentFilters.hasPdf;
      }
      
      if (currentFilters.highlighted !== null) {
        params.highlighted = currentFilters.highlighted;
      }

      // Note: Language filter is not supported by backend yet
      // We'll filter on frontend if needed (but this affects pagination)
      // TODO: Add language filter to backend API

      const response: PaginatedArticleResponse = await ArticleService.list(params);
      
      // Apply language filter on frontend if needed (temporary solution)
      // Note: This affects pagination accuracy, but backend doesn't support language filter yet
      let filteredArticles = response.items;
      if (currentFilters.languages.length > 0) {
        filteredArticles = response.items.filter(article => {
          const articleLang = article.language?.toLowerCase() || '';
          return currentFilters.languages.some(lang => {
            if (lang === 'pt') return articleLang.startsWith('pt');
            if (lang === 'en') return articleLang.startsWith('en');
            if (lang === 'es') return articleLang.startsWith('es');
            return true; // 'other' matches anything not pt/en/es
          });
        });
      }
      
      setArticles(filteredArticles);
      setPagination({
        total: response.total,
        page: response.page,
        pageSize: response.page_size,
        totalPages: response.total_pages,
      });

      // Update URL
      updateURL(query, currentFilters, page);
    } catch (error) {
      console.error('Error performing search:', error);
      setArticles([]);
      setPagination(prev => ({ ...prev, total: 0, totalPages: 0 }));
    } finally {
      setIsLoading(false);
    }
  }, [pagination.pageSize, updateURL]);

  // Initial search on mount or when URL changes
  useEffect(() => {
    // Only perform initial search if we have query params or active filters
    const hasQuery = searchParams.get('q');
    const hasFilters = hasActiveFilters(filters);
    
    if (hasQuery || hasFilters) {
      performSearch(searchQuery || '', filters, pagination.page);
    }
  }, []); // Only on mount

  // Handle search
  const handleSearch = useCallback(() => {
    performSearch(searchQuery, filters, 1);
  }, [searchQuery, filters, performSearch]);

  // Handle filter change
  const handleFiltersChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    performSearch(searchQuery, newFilters, 1);
  }, [searchQuery, performSearch]);

  // Handle page change
  const handlePageChange = useCallback((newPage: number) => {
    setPagination(prev => ({ ...prev, page: newPage }));
    performSearch(searchQuery, filters, newPage);
  }, [searchQuery, filters, performSearch]);

  // Handle remove filter
  const handleRemoveFilter = useCallback((filterKey: keyof FilterState, value?: any) => {
    const newFilters = { ...filters };
    
    if (Array.isArray(filters[filterKey])) {
      (newFilters[filterKey] as any[]) = (filters[filterKey] as any[]).filter(v => v !== value);
    } else if (filterKey === 'hasPdf' || filterKey === 'highlighted') {
      (newFilters[filterKey] as any) = null;
    } else {
      (newFilters[filterKey] as any) = filterKey === 'sortBy' ? 'publication_date' : filterKey === 'sortOrder' ? 'desc' : '';
    }
    
    handleFiltersChange(newFilters);
  }, [filters, handleFiltersChange]);

  // Handle clear all filters
  const handleClearAllFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
    performSearch(searchQuery, DEFAULT_FILTERS, 1);
  }, [searchQuery, performSearch]);

  // Count active filters
  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.sourceType.length > 0) count += filters.sourceType.length;
    if (filters.feedIds.length > 0) count += filters.feedIds.length;
    if (filters.categoryIds.length > 0) count += filters.categoryIds.length;
    if (filters.languages.length > 0) count += filters.languages.length;
    if (filters.dateFrom) count++;
    if (filters.dateTo) count++;
    if (filters.author) count++;
    if (filters.hasPdf !== null) count++;
    if (filters.highlighted !== null) count++;
    return count;
  }, [filters]);

  // Helper to check if filters are active
  function hasActiveFilters(f: FilterState): boolean {
    return (
      f.sourceType.length > 0 ||
      f.feedIds.length > 0 ||
      f.categoryIds.length > 0 ||
      f.languages.length > 0 ||
      !!f.dateFrom ||
      !!f.dateTo ||
      !!f.author ||
      f.hasPdf !== null ||
      f.highlighted !== null
    );
  }

  return (
    <MainLayout>
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-display font-bold text-3xl md:text-4xl text-bhub-navy-dark dark:text-white mb-2">
            Repositório
          </h1>
          <p className="font-body font-light text-lg text-gray-600 dark:text-gray-400 mb-4">
            Busca avançada em periódicos e portais científicos de Análise do Comportamento.
          </p>
          
          {/* Info sobre métricas */}
          <div className="bg-gradient-to-r from-bhub-teal-light/20 to-bhub-navy-light/20 dark:from-bhub-teal-primary/10 dark:to-bhub-navy-dark/20 rounded-lg p-4 border border-bhub-teal-primary/20 dark:border-bhub-teal-primary/30">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-0.5">
                <Icon name="barChart" className="text-bhub-teal-primary" size="md" />
              </div>
              <div className="flex-1 space-y-2">
                <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white">
                  Métricas Disponíveis
                </h3>
                <div className="space-y-2 text-xs text-gray-700 dark:text-gray-300">
                  <div>
                    <strong className="text-bhub-teal-primary">Score de Relevância (1-10):</strong> Avaliação automática baseada em palavras-chave de impacto, periódico, DOI, qualidade do abstract e dados quantitativos. 
                    <span className="text-gray-600 dark:text-gray-400"> Passe o mouse sobre o score em cada artigo para mais detalhes.</span>
                  </div>
                  <div>
                    <strong className="text-bhub-teal-primary">Confiança de Classificação (0-100%):</strong> Indica o quão certo o sistema está da categoria atribuída pela IA. 
                    <span className="text-gray-600 dark:text-gray-400"> Baseado em análise semântica (IA externa), embeddings (ML local) ou heurística.</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <AdvancedSearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            onSearch={handleSearch}
            placeholder="reinforcement AND resurgence NOT animal"
          />
        </div>

        {/* Active Filters */}
        {activeFiltersCount > 0 && (
          <div className="mb-6">
            <ActiveFilters
              filters={filters}
              categories={categories}
              feeds={feeds}
              onRemoveFilter={handleRemoveFilter}
              onClearAll={handleClearAllFilters}
            />
          </div>
        )}

        {/* Main Content: Filters + Results */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Filter Panel */}
          <FilterPanel
            filters={filters}
            onFiltersChange={handleFiltersChange}
            categories={categories}
            feeds={feeds}
            onClearFilters={handleClearAllFilters}
            activeFiltersCount={activeFiltersCount}
          />

          {/* Results */}
          <div className="flex-1 min-w-0">
            <SearchResults
              articles={articles}
              total={pagination.total}
              page={pagination.page}
              pageSize={pagination.pageSize}
              totalPages={pagination.totalPages}
              searchQuery={searchQuery}
              onPageChange={handlePageChange}
              isLoading={isLoading}
            />
          </div>
        </div>
      </main>
      
      <Footer />
    </MainLayout>
  );
}
