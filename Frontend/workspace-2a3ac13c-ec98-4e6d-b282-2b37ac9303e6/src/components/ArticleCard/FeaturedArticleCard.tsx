'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FeaturedArticleCardProps } from '@/types/article';
import { Badge } from '@/components/Badge/Badge';
import { AuthorAvatar } from '@/components/Avatar/Avatar';
import { IconButton, CTAButton } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { cn, formatDate } from '@/lib/utils';

export function FeaturedArticleCard({
  id,
  title,
  excerpt,
  category,
  date,
  citations,
  author,
  readingTime,
  onRead,
  onLike,
  isLiked = false
}: FeaturedArticleCardProps) {
  const router = useRouter();
  const [liked, setLiked] = useState(isLiked);
  const [bookmarked, setBookmarked] = useState(false);

  const handleLike = () => {
    setLiked(!liked);
    onLike?.();
  };

  const handleBookmark = () => {
    setBookmarked(!bookmarked);
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
    onRead?.();
  };

  return (
    <article 
      className={cn(
        "relative overflow-hidden rounded-lg p-6 text-white transition-all hover:shadow-lg cursor-pointer",
        "bg-gradient-to-br from-bhub-dark-gray to-bhub-navy-dark"
      )}
      onClick={handleReadArticle}
    >
      {/* Decorative overlay */}
      <div 
        className={cn(
          "absolute top-0 right-0 w-48 h-48 pointer-events-none",
          "bg-gradient-to-br from-bhub-teal-primary/10 to-transparent"
        )}
      />
      
      {/* Content */}
      <div className="relative z-10">
        {/* Header with metadata */}
        <header className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <Badge 
              label={category.label}
              icon={category.icon}
              variant="featured"
              className="text-bhub-teal-light border-bhub-teal-primary/50"
            />
            <div className="flex items-center gap-4 text-sm text-bhub-teal-light">
              <span className="flex items-center gap-1">
                <Icon name="calendar" size="sm" />
                {formatDate(date)}
              </span>
              <span className="flex items-center gap-1">
                <Icon name="star" size="sm" />
                {citations} citações
              </span>
            </div>
          </div>
          
          <h1 className="font-display font-bold text-2xl md:text-3xl text-bhub-teal-light mb-3 leading-tight">
            {title}
          </h1>
          
          <p className="font-body font-light text-base md:text-lg text-white/90 mb-4 leading-relaxed">
            {excerpt}
          </p>
        </header>

        {/* Author section */}
        <div className="flex items-center gap-3 mb-6">
          <AuthorAvatar 
            name={author.name}
            initials={author.avatar}
            size="lg"
          />
          <div>
            <p className="font-body font-medium text-white">
              Dr. {author.name}
            </p>
            <p className="font-body font-light text-sm text-white/70">
              {author.affiliation}
            </p>
          </div>
          <div className="ml-auto flex items-center gap-1 text-sm text-white/70">
            <Icon name="clock" size="sm" />
            {readingTime} min
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-between" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-2">
            <IconButton
              icon={<Icon name="heart" />}
              variant="ghost"
              className={cn(
                "text-white/70 hover:text-white hover:bg-white/10",
                liked && "text-bhub-red-accent"
              )}
              onClick={handleLike}
              aria-label={liked ? "Remover dos favoritos" : "Adicionar aos favoritos"}
            />
            <IconButton
              icon={<Icon name="bookmark" />}
              variant="ghost"
              className={cn(
                "text-white/70 hover:text-white hover:bg-white/10",
                bookmarked && "text-bhub-yellow-primary"
              )}
              onClick={handleBookmark}
              aria-label={bookmarked ? "Remover dos salvos" : "Salvar artigo"}
            />
            <IconButton
              icon={<Icon name="share" />}
              variant="ghost"
              className="text-white/70 hover:text-white hover:bg-white/10"
              onClick={handleShare}
              aria-label="Compartilhar artigo"
            />
          </div>
          
          <CTAButton
            onClick={handleReadArticle}
            className="bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20"
          >
            Ler Artigo
            <Icon name="chevronRight" />
          </CTAButton>
        </div>
      </div>
    </article>
  );
}