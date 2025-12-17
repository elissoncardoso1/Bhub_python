'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { Article } from '@/types/article';

interface AbstractHighlightBlockProps {
  article: Article;
  className?: string;
  showTranslationLabel?: boolean;
}

/**
 * AbstractHighlightBlock - Bloco de resumo destacado para screenshots
 * 
 * Designado para ser screenshot-friendly:
 * - Visualmente isolado (card-style ou quote-like)
 * - Largura máxima legível
 * - Aparência de citação acadêmica
 * - Funciona como composição standalone (título + abstract)
 */
export function AbstractHighlightBlock({ 
  article, 
  className,
  showTranslationLabel = false 
}: AbstractHighlightBlockProps) {
  const abstract = article.abstract || 'Resumo não disponível.';
  const isTranslated = !!article.abstract_translated && showTranslationLabel;

  return (
    <section 
      className={cn(
        // Container principal - isolado visualmente
        "relative",
        "bg-gray-50 dark:bg-gray-800/50",
        "rounded-xl md:rounded-2xl",
        "p-6 md:p-8 lg:p-10",
        "border-l-4 border-l-bhub-teal-primary",
        // Margens seguras
        "max-w-3xl mx-auto",
        "mb-6 md:mb-8",
        className
      )}
      aria-label="Resumo do artigo"
    >
      {/* Label de tradução (se aplicável) */}
      {isTranslated && (
        <div className="mb-4">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-bhub-teal-light dark:bg-bhub-teal-primary/20 text-xs font-medium text-bhub-teal-primary dark:text-bhub-teal-light">
            <span className="w-1.5 h-1.5 rounded-full bg-bhub-teal-primary" />
            Traduzido
          </span>
        </div>
      )}

      {/* Abstract Text - Estilo de citação acadêmica */}
      <div className="relative">
        {/* Quote mark decorativo (opcional, sutil) */}
        <div 
          className={cn(
            "absolute -top-2 -left-2",
            "text-4xl md:text-5xl",
            "text-bhub-teal-primary/40 dark:text-bhub-teal-primary/30",
            "font-display font-bold",
            "leading-none",
            "select-none pointer-events-none"
          )}
          aria-hidden="true"
        >
          "
        </div>

        {/* Texto do abstract */}
        <p 
          className={cn(
            "font-body font-light",
            "text-base md:text-lg lg:text-xl",
            "text-gray-700 dark:text-gray-300",
            "leading-relaxed md:leading-loose",
            // Largura máxima para legibilidade
            "max-w-none",
            // Espaçamento para quote mark
            "pl-6 md:pl-8"
          )}
          role="article"
          aria-label="Resumo do artigo científico"
        >
          {abstract}
        </p>
      </div>

      {/* Source reference discreto no final */}
      {article.journal_name && (
        <footer className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700" aria-label="Referência da publicação">
          <p className="font-body text-xs md:text-sm text-gray-500 dark:text-gray-400 font-light italic">
            {article.journal_name}
            {article.publication_date && ` • ${new Date(article.publication_date).getFullYear()}`}
          </p>
        </footer>
      )}
    </section>
  );
}

