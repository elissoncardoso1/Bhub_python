'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArticleCardProps } from '@/types/article';
import { Badge } from '@/components/Badge/Badge';
import { Avatar } from '@/components/Avatar/Avatar';
import { IconButton, Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { cn, formatDate, getCategoryColor } from '@/lib/utils';

export function ArticleCard({
  id,
  title,
  excerpt,
  category,
  author,
  authors,
  date,
  readingTime,
  source,
  sourceId,
  sourceCategory,
  imageUrl,
  featured = false,
  variant = 'default'
}: ArticleCardProps) {
  const router = useRouter();
  const [isLiked, setIsLiked] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);

  const handleLike = () => {
    setIsLiked(!isLiked);
  };

  const handleBookmark = () => {
    setIsBookmarked(!isBookmarked);
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title,
        text: excerpt,
        url: `${window.location.origin}/articles/${id}`
      });
    } else {
      navigator.clipboard.writeText(`${window.location.origin}/articles/${id}`);
    }
  };

  const handleReadArticle = () => {
    router.push(`/articles/${id}`);
  };

  const isCompact = variant === 'compact';

  return (
    <article 
      className={cn(
        "bg-white dark:bg-gray-800 rounded-lg p-4 md:p-6 border border-gray-200 dark:border-gray-700 transition-all hover:shadow-md cursor-pointer",
        featured && "ring-2 ring-bhub-teal-primary/20",
        // Scientific Style (Blue)
        sourceCategory === 'journal' && "border-l-4 border-l-blue-500 bg-blue-50/30 dark:bg-blue-900/10",
        // Blog Style (Green)
        sourceCategory === 'portal' && "border-l-4 border-l-green-500 bg-green-50/30 dark:bg-green-900/10"
      )}
      onClick={handleReadArticle}
    >
      {/* Article Image for Portals */}
      {sourceCategory === 'portal' && imageUrl && (
        <div className="mb-4 relative h-48 w-full overflow-hidden rounded-md">
           <img 
             src={imageUrl} 
             alt={title}
             className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-500"
             loading="lazy"
             onError={(e) => {
               (e.target as HTMLImageElement).style.display = 'none';
             }}
           />
           <div className="absolute top-2 right-2">
             <div className="flex items-center gap-1.5 px-2 py-1 bg-green-100 dark:bg-green-900/80 text-green-700 dark:text-green-300 rounded-full border border-green-200 dark:border-green-700/50 shadow-sm backdrop-blur-sm">
               <Icon name="rss" size="sm" className="text-green-600 dark:text-green-400 w-3 h-3" />
               <span className="text-[10px] font-bold uppercase tracking-wider text-green-700 dark:text-green-300">Portal / Blog</span>
             </div>
           </div>
        </div>
      )}

      {/* Journal Indicator (No Image) */}
      {sourceCategory === 'journal' && (
        <div className="mb-3 flex items-center justify-between">
           <div className="flex items-center gap-2 px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full border border-blue-200 dark:border-blue-700/50">
             <Icon name="bookOpen" size="sm" className="text-blue-600 dark:text-blue-400 w-3 h-3" />
             <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 dark:text-blue-300">Periódico Científico</span>
           </div>
        </div>
      )}

      {/* Portal/Blog Indicator (No Image) */}
      {sourceCategory === 'portal' && !imageUrl && (
        <div className="mb-3 flex items-center justify-between">
           <div className="flex items-center gap-2 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full border border-green-200 dark:border-green-700/50">
             <Icon name="rss" size="sm" className="text-green-600 dark:text-green-400 w-3 h-3" />
             <span className="text-[10px] font-bold uppercase tracking-wider text-green-700 dark:text-green-300">Portal / Blog</span>
           </div>
        </div>
      )}

      {/* Header with metadata */}
      <header className={cn("mb-3", isCompact && "mb-2")}>
        <div className="flex items-center justify-between mb-2">
          <Badge 
            label={category}
            variant="outline"
            className={cn("text-xs border", getCategoryColor(category))}
          />
          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            <span>{formatDate(date)}</span>
          </div>
        </div>
        
        <h2 className={cn(
          "font-display font-bold text-bhub-navy-dark dark:text-white mb-2 leading-tight",
          isCompact ? "text-lg" : "text-xl"
        )}>
          {title}
        </h2>
        
        {!isCompact && (
          <p className="font-body font-light text-sm text-gray-600 dark:text-gray-300 mb-3 leading-relaxed line-clamp-3">
            {excerpt}
          </p>
        )}
      </header>

      {/* Author and metadata */}
      <div className={cn(
        "flex items-center justify-between mb-4",
        isCompact && "mb-3"
      )}>
        <div className="flex items-center gap-3">
          <Avatar 
            name={author.name}
            initials={author.avatar}
            size={isCompact ? "sm" : "md"}
          />
          <div>
            <p className="font-body font-medium text-sm text-gray-900 dark:text-white">
              {(() => {
                if (authors && authors.length > 0) {
                   const formattedAuthors = authors.map(a => 
                     a.role === 'editor' ? `${a.name} (Editor)` : a.name
                   );
                   if (formattedAuthors.length === 1) return formattedAuthors[0];
                   return `${formattedAuthors.slice(0, -1).join(', ')} e ${formattedAuthors.slice(-1)}`;
                }
                return author.name;
              })()}
            </p>
            {!isCompact && source && (
              <p 
                className={cn(
                  "font-body font-light text-xs text-gray-500 dark:text-gray-400",
                  sourceId && "hover:text-bhub-teal-primary cursor-pointer hover:underline"
                )}
                onClick={(e) => {
                  if (sourceId) {
                    e.stopPropagation();
                    router.push(`/source/${sourceId}`);
                  }
                }}
              >
                {source}
              </p>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          <Icon name="clock" size="sm" />
          {readingTime} min
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-1">
          <IconButton
            icon={<Icon name="heart" />}
            variant="ghost"
            size="sm"
            className={cn(
              "text-gray-400 hover:text-bhub-red-accent",
              isLiked && "text-bhub-red-accent"
            )}
            onClick={handleLike}
            aria-label="Curtir artigo"
          />
          <IconButton
            icon={<Icon name="bookmark" />}
            variant="ghost"
            size="sm"
            className={cn(
              "text-gray-400 hover:text-bhub-yellow-primary",
              isBookmarked && "text-bhub-yellow-primary"
            )}
            onClick={handleBookmark}
            aria-label="Salvar artigo"
          />
          <IconButton
            icon={<Icon name="share" />}
            variant="ghost"
            size="sm"
            className="text-gray-400 hover:text-bhub-teal-primary"
            onClick={handleShare}
            aria-label="Compartilhar artigo"
          />
        </div>
        
        <Button
          variant="ghost"
          size="sm"
          className="text-bhub-teal-primary hover:text-bhub-teal-primary/80 hover:bg-bhub-teal-light/20 font-medium"
          onClick={handleReadArticle}
        >
          Ler Artigo
          <Icon name="chevronRight" size="sm" />
        </Button>
      </div>
    </article>
  );
}