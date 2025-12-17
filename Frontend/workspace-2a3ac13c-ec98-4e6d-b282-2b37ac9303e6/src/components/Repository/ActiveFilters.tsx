'use client';

import React from 'react';
import { FilterState } from './FilterPanel';
import { Category } from '@/types/article';
import { Badge } from '@/components/Badge/Badge';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { cn } from '@/lib/utils';

interface ActiveFiltersProps {
  filters: FilterState;
  categories: Category[];
  feeds: { id: number; name: string }[];
  onRemoveFilter: (filterKey: keyof FilterState, value?: any) => void;
  onClearAll: () => void;
  className?: string;
}

export function ActiveFilters({
  filters,
  categories,
  feeds,
  onRemoveFilter,
  onClearAll,
  className
}: ActiveFiltersProps) {
  const activeFilters: Array<{ key: keyof FilterState; label: string; value: any }> = [];

  // Source Type
  filters.sourceType.forEach(type => {
    activeFilters.push({
      key: 'sourceType',
      label: type === 'journal' ? 'Periódico científico' : 'Portal / Blog',
      value: type
    });
  });

  // Feed IDs
  filters.feedIds.forEach(feedId => {
    const feed = feeds.find(f => f.id === feedId);
    if (feed) {
      activeFilters.push({
        key: 'feedIds',
        label: feed.name,
        value: feedId
      });
    }
  });

  // Category IDs
  filters.categoryIds.forEach(categoryId => {
    const category = categories.find(c => c.id === categoryId);
    if (category) {
      activeFilters.push({
        key: 'categoryIds',
        label: category.name,
        value: categoryId
      });
    }
  });

  // Languages
  filters.languages.forEach(lang => {
    const langLabels: Record<string, string> = {
      'pt': 'Português',
      'en': 'Inglês',
      'es': 'Espanhol',
      'other': 'Outros'
    };
    activeFilters.push({
      key: 'languages',
      label: langLabels[lang] || lang,
      value: lang
    });
  });

  // Date From
  if (filters.dateFrom) {
    activeFilters.push({
      key: 'dateFrom',
      label: `De: ${new Date(filters.dateFrom).toLocaleDateString('pt-BR')}`,
      value: filters.dateFrom
    });
  }

  // Date To
  if (filters.dateTo) {
    activeFilters.push({
      key: 'dateTo',
      label: `Até: ${new Date(filters.dateTo).toLocaleDateString('pt-BR')}`,
      value: filters.dateTo
    });
  }

  // Author
  if (filters.author) {
    activeFilters.push({
      key: 'author',
      label: `Autor: ${filters.author}`,
      value: filters.author
    });
  }

  // Has PDF
  if (filters.hasPdf === true) {
    activeFilters.push({
      key: 'hasPdf',
      label: 'Com PDF',
      value: true
    });
  }

  // Highlighted
  if (filters.highlighted === true) {
    activeFilters.push({
      key: 'highlighted',
      label: 'Em destaque',
      value: true
    });
  }

  if (activeFilters.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap items-center gap-2 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700', className)}>
      <div className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
        <Icon name="filter" size="sm" />
        Filtros ativos:
      </div>
      
      {activeFilters.map((filter, index) => (
        <Badge
          key={`${filter.key}-${filter.value}-${index}`}
          label={
            <span className="flex items-center gap-1.5">
              {filter.label}
              <button
                onClick={() => onRemoveFilter(filter.key, filter.value)}
                className="ml-1 hover:text-red-500 transition-colors"
                aria-label={`Remover filtro ${filter.label}`}
              >
                <Icon name="close" size="sm" className="w-3 h-3" />
              </button>
            </span>
          }
          variant="outline"
          className="text-xs"
        />
      ))}
      
      {activeFilters.length > 1 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearAll}
          className="text-xs text-gray-600 dark:text-gray-400 hover:text-red-500"
        >
          Limpar todos
        </Button>
      )}
    </div>
  );
}

