'use client';

import React, { useState } from 'react';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { TranslationService } from '@/services/translationService';
import { cn } from '@/lib/utils';

interface TranslationPanelProps {
  /** Texto original */
  originalText: string;
  /** Idioma de origem (padrão: 'en') */
  sourceLang?: string;
  /** Idioma de destino (padrão: 'pt-BR') */
  targetLang?: string;
  /** Título do painel */
  title?: string;
  /** Classe CSS adicional */
  className?: string;
}

export function TranslationPanel({
  originalText,
  sourceLang = 'en',
  targetLang = 'pt-BR',
  title = 'Tradução',
  className,
}: TranslationPanelProps) {
  const [isTranslating, setIsTranslating] = useState(false);
  const [translatedText, setTranslatedText] = useState<string | null>(null);
  const [wasCached, setWasCached] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(true);

  const handleTranslate = async () => {
    if (!originalText || !originalText.trim()) {
      setError('Texto vazio');
      return;
    }

    setIsTranslating(true);
    setError(null);

    try {
      const response = await TranslationService.translate(
        originalText,
        sourceLang,
        targetLang
      );

      setTranslatedText(response.translated);
      setWasCached(response.cached);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Erro ao traduzir texto';
      setError(errorMessage);
      console.error('Translation error:', err);
    } finally {
      setIsTranslating(false);
    }
  };

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center justify-between">
        <h3 className="font-display font-bold text-lg text-gray-900 dark:text-white">
          {title}
        </h3>
        <div className="flex items-center gap-2">
          <Button
            onClick={handleTranslate}
            disabled={isTranslating || !originalText?.trim()}
            variant="outline"
            size="sm"
          >
            <Icon
              name={isTranslating ? 'loader' : 'languages'}
              className={cn('mr-2', isTranslating && 'animate-spin')}
            />
            {isTranslating ? 'Traduzindo...' : 'Traduzir'}
          </Button>
          {translatedText && (
            <Button
              onClick={() => setShowOriginal(!showOriginal)}
              variant="ghost"
              size="sm"
            >
              <Icon name={showOriginal ? 'eye-off' : 'eye'} className="mr-2" />
              {showOriginal ? 'Ocultar Original' : 'Mostrar Original'}
            </Button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {translatedText && (
        <div className="space-y-4">
          {wasCached && (
            <div className="flex items-center gap-2 text-xs text-bhub-teal-primary">
              <Icon name="check-circle" size="sm" />
              <span>Tradução recuperada do cache</span>
            </div>
          )}

          <div className="prose prose-sm dark:prose-invert max-w-none">
            <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <p className="font-body text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                {translatedText}
              </p>
            </div>
          </div>
        </div>
      )}

      {showOriginal && (
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 font-semibold uppercase">
              Texto Original ({sourceLang})
            </p>
            <p className="font-body text-sm text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-wrap">
              {originalText}
            </p>
          </div>
        </div>
      )}

      {!translatedText && !isTranslating && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Clique em "Traduzir" para ver a tradução do texto
          </p>
        </div>
      )}
    </div>
  );
}

