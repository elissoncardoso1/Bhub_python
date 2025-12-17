'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Article } from '@/types/article';
import { ArticleCard } from '@/components/ArticleCard/ArticleCard';
import { articleToCardProps } from '@/types/article';
import { Badge } from '@/components/Badge/Badge';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious, PaginationEllipsis } from '@/components/ui/pagination';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn, formatDate } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

interface SearchResultsProps {
  articles: Article[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  searchQuery?: string;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
  className?: string;
}

export function SearchResults({
  articles,
  total,
  page,
  pageSize,
  totalPages,
  searchQuery,
  onPageChange,
  isLoading = false,
  className
}: SearchResultsProps) {
  const router = useRouter();
  const { toast } = useToast();

  // Check if all articles have the same impact_score
  const impactScores = articles.map(a => a.impact_score).filter(s => s > 0);
  const uniqueScores = new Set(impactScores.map(s => s.toFixed(1)));
  const hasVariation = impactScores.length > 0 && uniqueScores.size > 1;

  if (isLoading) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="flex items-center justify-center py-12">
          <Icon name="loader" className="animate-spin text-bhub-teal-primary" size="lg" />
          <span className="ml-3 text-gray-600 dark:text-gray-400">Buscando artigos...</span>
        </div>
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className={cn('space-y-6', className)}>
        <div className="text-center py-12">
          <Icon name="search" className="mx-auto text-gray-400 dark:text-gray-500 mb-4" size="lg" />
          <h3 className="font-display font-semibold text-lg text-bhub-navy-dark dark:text-white mb-2">
            Nenhum resultado encontrado
          </h3>
          <p className="font-body font-light text-gray-600 dark:text-gray-400 mb-4">
            {searchQuery 
              ? `Não encontramos artigos para "${searchQuery}". Tente ajustar seus filtros ou termos de busca.`
              : 'Tente ajustar seus filtros ou realizar uma nova busca.'
            }
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Results Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex-1">
          <h2 className="font-display font-semibold text-lg text-bhub-navy-dark dark:text-white mb-1">
            Resultados da Busca
          </h2>
          <p className="font-body font-light text-sm text-gray-600 dark:text-gray-400">
            {total === 1 
              ? '1 artigo encontrado'
              : `${total.toLocaleString('pt-BR')} artigos encontrados`
            }
            {searchQuery && (
              <span className="ml-2">
                para <span className="font-medium">"{searchQuery}"</span>
              </span>
            )}
          </p>
          {!hasVariation && impactScores.length > 0 && (
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/50 rounded-md p-2 border border-gray-200 dark:border-gray-700">
              <span className="flex items-center gap-1">
                <Icon name="barChart" size="sm" />
                <span>
                  <strong>Nota:</strong> Todos os artigos têm a mesma relevância ({impactScores[0]?.toFixed(1)}/10). 
                  A relevância é calculada automaticamente pelo sistema. 
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button type="button" className="ml-1 text-bhub-teal-primary hover:underline">
                        Saiba mais
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="max-w-xs">
                      <div className="space-y-1">
                        <p className="font-semibold">Score de Relevância</p>
                        <p className="text-xs">
                          Avaliação automática (1-10) baseada em múltiplos fatores. Se todos os artigos têm o mesmo score, pode indicar que:
                        </p>
                        <ul className="text-xs list-disc list-inside space-y-0.5 ml-2">
                          <li>Os artigos ainda não foram processados pelo sistema de avaliação</li>
                          <li>Os artigos têm características similares</li>
                          <li>O cálculo de relevância está usando valores padrão</li>
                        </ul>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </span>
              </span>
            </div>
          )}
          
          {/* Info sobre classificação por IA */}
          {articles.some(a => a.classification_confidence !== null && a.classification_confidence !== undefined) && (
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/20 rounded-md p-2 border border-blue-200 dark:border-blue-800">
              <span className="flex items-start gap-2">
                <Icon name="barChart" size="sm" className="mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Classificação Automática por IA:</strong> Os artigos são automaticamente categorizados usando inteligência artificial. 
                  O sistema tenta primeiro usar IA externa (DeepSeek/OpenRouter), depois ML local (embeddings), e por último heurística (palavras-chave).
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button type="button" className="ml-1 text-bhub-teal-primary hover:underline">
                        Como funciona?
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="max-w-xs">
                      <div className="space-y-1">
                        <p className="font-semibold">Sistema de Classificação em 3 Níveis</p>
                        <ol className="text-xs list-decimal list-inside space-y-1 ml-2">
                          <li><strong>IA Externa</strong>: Análise semântica avançada via DeepSeek/OpenRouter (mais preciso)</li>
                          <li><strong>ML Local</strong>: Embeddings de similaridade usando modelo multilingual (fallback eficiente)</li>
                          <li><strong>Heurística</strong>: Análise por palavras-chave específicas (último recurso)</li>
                        </ol>
                        <p className="text-xs mt-1 pt-1 border-t border-white/20">
                          A classificação acontece automaticamente quando artigos são agregados ao sistema. 
                          A confiança (0-100%) indica o quão certo o sistema está da categoria atribuída.
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </span>
              </span>
            </div>
          )}
        </div>
        
        {/* Share Search Link */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const url = new URL(window.location.href);
              navigator.clipboard.writeText(url.toString());
              toast({
                title: 'Link copiado!',
                description: 'O link da busca foi copiado para a área de transferência.',
              });
            }}
          >
            <Icon name="share" size="sm" />
            Compartilhar busca
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              try {
                const savedSearches = JSON.parse(localStorage.getItem('bhub_saved_searches') || '[]');
                const searchData = {
                  id: Date.now().toString(),
                  query: searchQuery,
                  url: window.location.href,
                  savedAt: new Date().toISOString(),
                };
                savedSearches.unshift(searchData);
                // Keep only last 10 saved searches
                const limitedSearches = savedSearches.slice(0, 10);
                localStorage.setItem('bhub_saved_searches', JSON.stringify(limitedSearches));
                toast({
                  title: 'Busca salva!',
                  description: 'Esta busca foi salva e pode ser acessada posteriormente.',
                });
              } catch (error) {
                toast({
                  title: 'Erro',
                  description: 'Não foi possível salvar a busca.',
                  variant: 'destructive',
                });
              }
            }}
          >
            <Icon name="bookmark" size="sm" />
            Salvar busca
          </Button>
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        {articles.map((article) => {
          const cardProps = articleToCardProps(article);
          return (
            <div key={article.id} className="relative">
              <ArticleCard {...cardProps} variant="default" />
              
              {/* Additional metadata for search results */}
              <div className="mt-2 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                {article.journal_name && (
                  <span className="flex items-center gap-1">
                    <Icon name="bookOpen" size="sm" />
                    {article.journal_name}
                  </span>
                )}
                {article.doi && (
                  <span className="flex items-center gap-1">
                    <Icon name="external" size="sm" />
                    DOI: {article.doi}
                  </span>
                )}
                {article.language && (
                  <Badge 
                    label={article.language.toUpperCase()} 
                    variant="outline"
                    className="text-xs"
                  />
                )}
                {article.impact_score > 0 && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="flex items-center gap-1 cursor-help">
                        <Icon name="star" size="sm" />
                        Relevância: {article.impact_score.toFixed(1)}/10
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs">
                      <div className="space-y-1">
                        <p className="font-semibold">Score de Relevância</p>
                        <p className="text-xs">
                          Avaliação automática (1-10) baseada em:
                        </p>
                        <ul className="text-xs list-disc list-inside space-y-0.5 ml-2">
                          <li>Palavras-chave de impacto (meta-análise, revisão sistemática, etc.)</li>
                          <li>Periódico de publicação</li>
                          <li>Presença de DOI</li>
                          <li>Qualidade do abstract</li>
                          <li>Dados quantitativos</li>
                        </ul>
                        <p className="text-xs mt-1 pt-1 border-t border-white/20">
                          <strong>Uso:</strong> Use este score para identificar artigos com maior potencial de impacto científico. Artigos com score ≥7 são considerados de alto impacto.
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                )}
                {article.classification_confidence !== null && article.classification_confidence !== undefined && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="flex items-center gap-1 cursor-help">
                        <Icon name="barChart" size="sm" />
                        Classificação IA: {(article.classification_confidence * 100).toFixed(0)}%
                      </span>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-xs">
                      <div className="space-y-1">
                        <p className="font-semibold">Confiança da Classificação por IA</p>
                        <p className="text-xs">
                          Este artigo foi automaticamente classificado em sua categoria usando inteligência artificial. A confiança indica o quão certo o sistema está da classificação.
                        </p>
                        <p className="text-xs mt-1 font-semibold">Como funciona:</p>
                        <ul className="text-xs list-disc list-inside space-y-0.5 ml-2">
                          <li><strong>IA Externa</strong> (DeepSeek/OpenRouter): Análise semântica avançada</li>
                          <li><strong>ML Local</strong>: Embeddings de similaridade (fallback)</li>
                          <li><strong>Heurística</strong>: Análise por palavras-chave (último recurso)</li>
                        </ul>
                        <p className="text-xs mt-1 pt-1 border-t border-white/20">
                          <strong>Interpretação:</strong> 
                          <br />• ≥80%: Alta confiança
                          <br />• 50-79%: Confiança moderada
                          <br />• &lt;50%: Baixa confiança (pode precisar revisão manual)
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center pt-6">
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    if (page > 1) onPageChange(page - 1);
                  }}
                  className={page === 1 ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
              
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => {
                // Show first page, last page, current page, and pages around current
                if (
                  pageNum === 1 ||
                  pageNum === totalPages ||
                  (pageNum >= page - 1 && pageNum <= page + 1)
                ) {
                  return (
                    <PaginationItem key={pageNum}>
                      <PaginationLink
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          onPageChange(pageNum);
                        }}
                        isActive={pageNum === page}
                      >
                        {pageNum}
                      </PaginationLink>
                    </PaginationItem>
                  );
                } else if (pageNum === page - 2 || pageNum === page + 2) {
                  return (
                    <PaginationItem key={pageNum}>
                      <PaginationEllipsis />
                    </PaginationItem>
                  );
                }
                return null;
              })}
              
              <PaginationItem>
                <PaginationNext
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    if (page < totalPages) onPageChange(page + 1);
                  }}
                  className={page === totalPages ? 'pointer-events-none opacity-50' : ''}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}
    </div>
  );
}

