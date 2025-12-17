'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { cn } from '@/lib/utils';
import { CategoryService } from '@/services/categoryService';
import { AuthorService } from '@/services/authorService';
import { FeedService, Feed } from '@/services/feedService';
import { Category, Author } from '@/types/article';

interface FilterSidebarProps {
  className?: string;
  onFilter?: (filters: any) => void;
}

export function FilterSidebar({ className, onFilter }: FilterSidebarProps) {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [feeds, setFeeds] = useState<Feed[]>([]);
  
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [selectedAuthors, setSelectedAuthors] = useState<string[]>([]);
  const [selectedFeed, setSelectedFeed] = useState<string>('');
  const [dateRange, setDateRange] = useState<string>('all');
  
  const [loading, setLoading] = useState(true);

  // Date ranges configuration
  const dateRanges = [
    { value: 'all', label: 'Todos os períodos' },
    { value: 'week', label: 'Última semana' },
    { value: 'month', label: 'Último mês' },
    { value: 'quarter', label: 'Último trimestre' },
    { value: 'year', label: 'Último ano' }
  ];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [cats, auths, feedsData] = await Promise.all([
          CategoryService.getAll(),
          AuthorService.getTopAuthors(5),
          FeedService.getAll()
        ]);
        setCategories(cats);
        setAuthors(auths);
        setFeeds(feedsData);
      } catch (error) {
        console.error('Failed to fetch sidebar data', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const toggleCategory = (categoryId: number) => {
    setSelectedCategories(prev => 
      prev.includes(categoryId) 
        ? prev.filter(id => id !== categoryId)
        : [...prev, categoryId]
    );
  };

  const toggleAuthor = (authorName: string) => {
    setSelectedAuthors(prev => 
      prev.includes(authorName) 
        ? prev.filter(name => name !== authorName)
        : [...prev, authorName]
    );
  };

  const clearFilters = () => {
    setSelectedCategories([]);
    setSelectedAuthors([]);
    setSelectedFeed('');
    setDateRange('all');
  };

  const handleApply = () => {
    const params = new URLSearchParams();
    
    // Add selected categories
    selectedCategories.forEach(id => params.append('category_id', id.toString()));
    
    // Add selected author (taking the first one since backend filters by single author string for now)
    if (selectedAuthors.length > 0) {
        params.set('author', selectedAuthors[0]);
    }

    // Add date range
    if (dateRange !== 'all') {
        const now = new Date();
        let fromDate;
        switch(dateRange) {
            case 'week': 
              fromDate = new Date(now.setDate(now.getDate() - 7)); 
              break;
            case 'month': 
              fromDate = new Date(now.setMonth(now.getMonth() - 1)); 
              break;
            case 'quarter': 
              fromDate = new Date(now.setMonth(now.getMonth() - 3)); 
              break;
            case 'year': 
              fromDate = new Date(now.setFullYear(now.getFullYear() - 1)); 
              break;
        }
        if (fromDate) {
             params.set('date_from', fromDate.toISOString());
        }
    }

    if (selectedFeed) {
        params.set('feed_id', selectedFeed);
    }
    
    if (onFilter) {
      // If used in a context where we want to callback (e.g. internal state of ArticlesPage)
      // For now we assume redirect behavior or we could pass params object
      onFilter({
         category_id: selectedCategories,
         author: selectedAuthors[0],
         date_range: dateRange,
         feed_id: selectedFeed
      });
    } else {
       router.push(`/articles?${params.toString()}`);
    }
  };

  const hasActiveFilters = selectedCategories.length > 0 || 
                          selectedAuthors.length > 0 || 
                          selectedFeed !== '' ||
                          dateRange !== 'all';

  if (loading) {
    return (
      <aside className={cn('bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700', className)}>
        <div className="animate-pulse space-y-6">
           <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
           <div className="space-y-3">
             <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
             <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
           </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className={cn('bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-display font-bold text-lg text-bhub-navy-dark dark:text-white">
          Filtros
        </h3>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="text-bhub-teal-primary hover:text-bhub-teal-primary/80"
          >
            Limpar
          </Button>
        )}
      </div>

      {/* Categories */}
      <div className="mb-8">
        <h4 className="font-body font-semibold text-sm text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Icon name="filter" size="sm" />
          Categorias
        </h4>
        <div className="space-y-2 max-h-60 overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-200 dark:scrollbar-thumb-gray-700">
          {categories.map((category) => (
            <label
              key={category.id}
              className="flex items-center justify-between p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedCategories.includes(category.id)}
                  onChange={() => toggleCategory(category.id)}
                  className="rounded border-gray-300 text-bhub-teal-primary focus:ring-bhub-teal-primary"
                />
                <span className="font-body font-light text-sm text-gray-700 dark:text-gray-300">
                  {category.name}
                </span>
              </div>
              <span className="font-body font-light text-xs text-gray-500 dark:text-gray-400">
                {category.article_count || 0}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Authors */}
      <div className="mb-8">
        <h4 className="font-body font-semibold text-sm text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Icon name="user" size="sm" />
          Autores (Top)
        </h4>
        <div className="space-y-2">
          {authors.map((author) => (
            <label
              key={author.id}
              className="flex items-center justify-between p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedAuthors.includes(author.name)}
                  onChange={() => toggleAuthor(author.name)}
                  className="rounded border-gray-300 text-bhub-teal-primary focus:ring-bhub-teal-primary"
                />
                <span className="font-body font-light text-sm text-gray-700 dark:text-gray-300 line-clamp-1" title={author.name}>
                  {author.name}
                </span>
              </div>
              <span className="font-body font-light text-xs text-gray-500 dark:text-gray-400">
                {author.article_count || 0}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Sources */}
      <div className="mb-8">
        <h4 className="font-body font-semibold text-sm text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Icon name="bookmark" size="sm" />
          Fonte / Periódico
        </h4>
        <select
          value={selectedFeed}
          onChange={(e) => setSelectedFeed(e.target.value)}
          className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-body font-light text-sm focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent"
        >
          <option value="">Todas as fontes</option>
          {feeds.map((feed) => (
            <option key={feed.id} value={feed.id}>
              {feed.name}
            </option>
          ))}
        </select>
      </div>

      {/* Date Range */}
      <div className="mb-6">
        <h4 className="font-body font-semibold text-sm text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Icon name="calendar" size="sm" />
          Período
        </h4>
        <select
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
          className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-body font-light text-sm focus:ring-2 focus:ring-bhub-teal-primary focus:border-transparent"
        >
          {dateRanges.map((range) => (
            <option key={range.value} value={range.value}>
              {range.label}
            </option>
          ))}
        </select>
      </div>

      {/* Apply Filters Button */}
      <Button
        variant="default"
        className="w-full bg-bhub-teal-primary hover:bg-bhub-teal-primary/90 text-white"
        disabled={!hasActiveFilters}
        onClick={handleApply}
      >
        Aplicar Filtros
      </Button>
    </aside>
  );
}