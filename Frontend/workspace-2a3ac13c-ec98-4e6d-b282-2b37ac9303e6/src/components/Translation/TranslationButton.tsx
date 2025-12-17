'use client';

import React, { useState } from 'react';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { TranslationService } from '@/services/translationService';
import { cn } from '@/lib/utils';

interface TranslationButtonProps {
  /** Texto a traduzir */
  text: string;
  /** Idioma de origem (padrão: 'en') */
  sourceLang?: string;
  /** Idioma de destino (padrão: 'pt-BR') */
  targetLang?: string;
  /** Callback quando a tradução for concluída */
  onTranslated?: (translatedText: string, cached: boolean) => void;
  /** Tamanho do botão */
  size?: 'sm' | 'md' | 'lg';
  /** Variante do botão */
  variant?: 'default' | 'outline' | 'ghost';
  /** Classe CSS adicional */
  className?: string;
  /** Mostrar indicador de cache */
  showCacheIndicator?: boolean;
}

export function TranslationButton({
  text,
  sourceLang = 'en',
  targetLang = 'pt-BR',
  onTranslated,
  size = 'md',
  variant = 'outline',
  className,
  showCacheIndicator = true,
}: TranslationButtonProps) {
  const [isTranslating, setIsTranslating] = useState(false);
  const [translatedText, setTranslatedText] = useState<string | null>(null);
  const [wasCached, setWasCached] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleTranslate = async () => {
    if (!text || !text.trim()) {
      setError('Texto vazio');
      return;
    }

    setIsTranslating(true);
    setError(null);

    try {
      const response = await TranslationService.translate(
        text,
        sourceLang,
        targetLang
      );

      setTranslatedText(response.translated);
      setWasCached(response.cached);

      if (onTranslated) {
        onTranslated(response.translated, response.cached);
      }
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Erro ao traduzir texto';
      setError(errorMessage);
      console.error('Translation error:', err);
    } finally {
      setIsTranslating(false);
    }
  };

  const buttonText = isTranslating
    ? 'Traduzindo...'
    : translatedText
    ? 'Retraduzir'
    : 'Traduzir';

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <Button
        onClick={handleTranslate}
        disabled={isTranslating || !text?.trim()}
        variant={variant}
        size={size}
        className="w-full sm:w-auto"
      >
        <Icon
          name={isTranslating ? 'loader' : 'languages'}
          className={cn(
            'mr-2',
            isTranslating && 'animate-spin'
          )}
        />
        {buttonText}
      </Button>

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}

      {translatedText && (
        <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-display font-semibold text-sm text-gray-700 dark:text-gray-300">
              Tradução
            </h4>
            {showCacheIndicator && wasCached && (
              <span className="text-xs text-bhub-teal-primary bg-bhub-teal-light px-2 py-1 rounded">
                Do cache
              </span>
            )}
          </div>
          <p className="font-body text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            {translatedText}
          </p>
        </div>
      )}
    </div>
  );
}

