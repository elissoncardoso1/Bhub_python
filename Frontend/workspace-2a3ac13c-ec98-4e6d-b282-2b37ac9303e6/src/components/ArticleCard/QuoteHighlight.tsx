'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface QuoteHighlightProps {
  text: string;
  source?: string;
  className?: string;
}

/**
 * QuoteHighlight - Componente para destacar frases-chave
 * 
 * Designado para micro-content sharing:
 * - Frase ou sentença destacada
 * - Ênfase visual
 * - Tom acadêmico
 * - Perfeito para screenshots de Stories (9:16)
 */
export function QuoteHighlight({ text, source, className }: QuoteHighlightProps) {
  return (
    <div 
      className={cn(
        // Container principal - vertical, otimizado para Stories
        "relative",
        "bg-gradient-to-br from-bhub-navy-dark to-bhub-navy-dark/90 dark:from-gray-900 dark:to-gray-800",
        "rounded-2xl md:rounded-3xl",
        "p-8 md:p-12 lg:p-16",
        "border border-gray-200 dark:border-gray-700",
        "shadow-lg",
        // Altura mínima para Stories (9:16)
        "min-h-[400px] md:min-h-[500px]",
        "flex flex-col justify-center",
        "max-w-2xl mx-auto",
        "mb-6 md:mb-8",
        className
      )}
    >
      {/* Quote mark decorativo grande */}
      <div 
        className={cn(
          "absolute top-6 left-6 md:top-8 md:left-8",
          "text-6xl md:text-7xl lg:text-8xl",
          "text-bhub-teal-primary/20 dark:text-bhub-teal-primary/10",
          "font-display font-bold",
          "leading-none",
          "select-none pointer-events-none"
        )}
        aria-hidden="true"
      >
        "
      </div>

      {/* Texto da citação */}
      <blockquote 
        className={cn(
          "relative z-10",
          "font-display font-bold",
          "text-xl md:text-2xl lg:text-3xl",
          "text-white dark:text-gray-100",
          "leading-relaxed md:leading-loose",
          "mb-6 md:mb-8",
          // Espaçamento para quote mark
          "pl-8 md:pl-12"
        )}
      >
        {text}
      </blockquote>

      {/* Source - Discreto no final */}
      {source && (
        <div className="relative z-10 mt-auto pt-6 border-t border-white/20 dark:border-gray-600/20">
          <p className="font-body text-sm md:text-base text-white/80 dark:text-gray-300 font-light italic">
            — {source}
          </p>
        </div>
      )}

      {/* BHub watermark - Canto inferior direito */}
      <div 
        className={cn(
          "absolute bottom-4 right-4 md:bottom-6 md:right-6",
          "opacity-10",
          "pointer-events-none",
          "select-none"
        )}
      >
        <span className="font-body text-xs font-light text-white">
          bhub.online
        </span>
      </div>
    </div>
  );
}

