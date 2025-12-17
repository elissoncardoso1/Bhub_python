'use client';

import React from 'react';
import { ArticleCardProps } from '@/types/article';
import { ArticleCard } from './ArticleCard';
import { cn } from '@/lib/utils';

interface ArticleCardListProps {
  articles: ArticleCardProps[];
  columns?: 1 | 2 | 3 | 4;
  className?: string;
}

export function ArticleCardList({ 
  articles, 
  columns = 1,
  className 
}: ArticleCardListProps) {
  const gridClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
  };

  return (
    <div className={cn(
      'grid gap-4 md:gap-6',
      gridClasses[columns],
      className
    )}>
      {articles.map((article, index) => (
        <ArticleCard 
          key={`${article.title}-${index}`}
          {...article}
        />
      ))}
    </div>
  );
}