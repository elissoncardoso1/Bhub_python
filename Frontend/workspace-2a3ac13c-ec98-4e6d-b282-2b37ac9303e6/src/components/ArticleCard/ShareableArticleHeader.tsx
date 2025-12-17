'use client';

import React from 'react';
import { Badge } from '@/components/Badge/Badge';
import { Icon } from '@/components/Icon/Icon';
import { cn, formatDate, getCategoryColor } from '@/lib/utils';
import { Article } from '@/types/article';

interface ShareableArticleHeaderProps {
  article: Article;
  className?: string;
}

/**
 * ShareableArticleHeader - Header otimizado para screenshots
 * 
 * Designado para ser screenshot-friendly:
 * - Layout contido e centrado
 * - Hierarquia tipográfica clara
 * - Background neutro (light/dark)
 * - Margens seguras para cropping
 * - Funciona como card visual standalone
 */
export function ShareableArticleHeader({ article, className }: ShareableArticleHeaderProps) {
  const categoryLabel = article.category?.name || 'Sem categoria';
  const publicationDate = formatDate(article.publication_date || undefined) || 'Data não disponível';
  const journalName = article.journal_name || article.feed_name || 'Fonte não especificada';

  return (
    <header 
      className={cn(
        // Container principal - screenshot-safe
        "relative",
        "bg-white dark:bg-gray-900",
        "rounded-2xl md:rounded-3xl",
        "p-6 md:p-8 lg:p-10",
        "border border-gray-200 dark:border-gray-800",
        "shadow-sm",
        // Margens seguras para cropping
        "max-w-3xl mx-auto",
        // Espaçamento vertical adequado
        "mb-6 md:mb-8",
        className
      )}
      role="banner"
      aria-label="Cabeçalho do artigo científico"
    >
      {/* BHub Watermark - Sutil, canto inferior direito */}
      <div 
        className={cn(
          "absolute bottom-4 right-4 md:bottom-6 md:right-6",
          "pointer-events-none",
          "select-none"
        )}
      >
        <span className="font-body text-xs font-light text-gray-500 dark:text-gray-400">
          bhub.online
        </span>
      </div>

      {/* Source Category Badge - Tag gráfica para Periódico/Portal/Blog */}
      {article.source_category && (
        <div className="mb-4 md:mb-6">
          {article.source_category === 'journal' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full border border-blue-200 dark:border-blue-700/50">
              <Icon name="bookOpen" size="sm" className="text-blue-600 dark:text-blue-400 w-3.5 h-3.5" />
              <span className="text-xs font-bold uppercase tracking-wider text-blue-700 dark:text-blue-300">
                Periódico Científico
              </span>
            </div>
          )}
          {article.source_category === 'portal' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full border border-green-200 dark:border-green-700/50">
              <Icon name="rss" size="sm" className="text-green-600 dark:text-green-400 w-3.5 h-3.5" />
              <span className="text-xs font-bold uppercase tracking-wider text-green-700 dark:text-green-300">
                Portal / Blog
              </span>
            </div>
          )}
        </div>
      )}

      {/* Category Badge e Data - Topo */}
      <div className="flex items-center justify-between mb-4 md:mb-6 flex-wrap gap-3">
        <Badge 
          label={categoryLabel}
          variant="outline"
          className={cn(
            "text-xs md:text-sm font-medium",
            getCategoryColor(categoryLabel)
          )}
        />
        <time 
          className="font-body text-xs md:text-sm text-gray-500 dark:text-gray-400 font-light"
          dateTime={article.publication_date || undefined}
          aria-label={`Data de publicação: ${publicationDate}`}
        >
          {publicationDate}
        </time>
      </div>

      {/* Título - Hierarquia principal */}
      <h1 
        className={cn(
          "font-display font-bold",
          "text-2xl md:text-3xl lg:text-4xl",
          "text-bhub-navy-dark dark:text-white",
          "mb-4 md:mb-6",
          "leading-tight",
          // Largura máxima para legibilidade em screenshots
          "max-w-4xl"
        )}
      >
        {article.title}
      </h1>

      {/* Source/Journal - Contexto científico */}
      <div className="flex items-center gap-2 mb-4 md:mb-6" role="group" aria-label="Informações da publicação">
        <div className="flex items-center gap-2">
          <div className="w-1 h-1 rounded-full bg-bhub-teal-primary" aria-hidden="true" />
          <span className="font-body text-sm md:text-base text-gray-600 dark:text-gray-400 font-medium">
            {journalName}
          </span>
        </div>
        {article.doi && (
          <>
            <span className="text-gray-300 dark:text-gray-700" aria-hidden="true">•</span>
            <span className="font-body text-xs md:text-sm text-gray-500 dark:text-gray-400 font-light">
              <abbr title="Digital Object Identifier">DOI</abbr>: {article.doi}
            </span>
          </>
        )}
      </div>

      {/* Metadata adicional - Opcional, discreto */}
      <div className="flex flex-wrap items-center gap-4 text-xs md:text-sm text-gray-400 dark:text-gray-400 pt-4 border-t border-gray-100 dark:border-gray-800">
        {article.language && (
          <span className="font-body font-light">
            Idioma: {article.language === 'pt' ? 'Português' : article.language === 'en' ? 'Inglês' : article.language}
          </span>
        )}
        {article.impact_score && article.impact_score > 0 && (
          <span className="font-body font-light">
            Impacto: {article.impact_score.toFixed(1)}
          </span>
        )}
      </div>
    </header>
  );
}

