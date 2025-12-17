'use client';

import React, { useState } from 'react';
import { Category, Feed } from '@/types/article';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

export interface FilterState {
  // Fonte
  sourceType: ('journal' | 'portal')[];
  feedIds: number[];
  
  // Área / Tema
  categoryIds: number[];
  
  // Idioma
  languages: string[];
  
  // Data
  dateFrom: string;
  dateTo: string;
  
  // Autoria
  author: string;
  
  // Tipo de conteúdo
  hasPdf: boolean | null;
  highlighted: boolean | null;
  
  // Ordenação
  sortBy: 'publication_date' | 'title' | 'impact_score' | 'view_count';
  sortOrder: 'asc' | 'desc';
}

interface FilterPanelProps {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  categories: Category[];
  feeds: Feed[];
  onClearFilters: () => void;
  activeFiltersCount: number;
  className?: string;
}

const AREAS_TEMATICAS = [
  { id: 'aba', label: 'ABA' },
  { id: 'clinica', label: 'Clínica' },
  { id: 'educacao', label: 'Educação' },
  { id: 'comportamento-verbal', label: 'Comportamento Verbal' },
  { id: 'behaviorismo-radical', label: 'Behaviorismo Radical' },
  { id: 'pesquisa-experimental', label: 'Pesquisa Experimental' },
];

const IDIOMAS = [
  { value: 'pt', label: 'Português' },
  { value: 'en', label: 'Inglês' },
  { value: 'es', label: 'Espanhol' },
  { value: 'other', label: 'Outros' },
];

export function FilterPanel({
  filters,
  onFiltersChange,
  categories,
  feeds,
  onClearFilters,
  activeFiltersCount,
  className
}: FilterPanelProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const updateFilter = <K extends keyof FilterState>(
    key: K,
    value: FilterState[K]
  ) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const toggleArrayFilter = <K extends keyof FilterState>(
    key: K,
    value: any
  ) => {
    const current = filters[key] as any[];
    const newValue = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    updateFilter(key, newValue as FilterState[K]);
  };

  const FilterContent = () => (
    <div className="space-y-6">
      {/* Fonte */}
      <div>
        <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white mb-3 flex items-center gap-2">
          <Icon name="bookOpen" size="sm" />
          Fonte
        </h3>
        
        <div className="space-y-3">
          <div className="space-y-2">
            <Label className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Tipo de Fonte
            </Label>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="source-journal"
                  checked={filters.sourceType.includes('journal')}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      toggleArrayFilter('sourceType', 'journal');
                    } else {
                      updateFilter('sourceType', filters.sourceType.filter(t => t !== 'journal'));
                    }
                  }}
                />
                <Label
                  htmlFor="source-journal"
                  className="text-sm font-normal cursor-pointer"
                >
                  Periódico científico
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="source-portal"
                  checked={filters.sourceType.includes('portal')}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      toggleArrayFilter('sourceType', 'portal');
                    } else {
                      updateFilter('sourceType', filters.sourceType.filter(t => t !== 'portal'));
                    }
                  }}
                />
                <Label
                  htmlFor="source-portal"
                  className="text-sm font-normal cursor-pointer"
                >
                  Portal / Blog
                </Label>
              </div>
            </div>
          </div>
          
          {feeds.length > 0 && (
            <div className="space-y-2">
              <Label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                Nome da Fonte
              </Label>
              <div className="max-h-48 overflow-y-auto space-y-2 border border-gray-200 dark:border-gray-700 rounded-md p-3">
                {feeds.map((feed) => (
                  <div key={feed.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={`feed-${feed.id}`}
                      checked={filters.feedIds.includes(feed.id)}
                      onCheckedChange={() => {
                        toggleArrayFilter('feedIds', feed.id);
                      }}
                    />
                    <Label
                      htmlFor={`feed-${feed.id}`}
                      className="text-sm font-normal cursor-pointer flex-1"
                    >
                      {feed.name}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <Separator />

      {/* Área / Tema */}
      <div>
        <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white mb-3 flex items-center gap-2">
          <Icon name="bookOpen" size="sm" />
          Área / Tema
        </h3>
        <div className="max-h-64 overflow-y-auto space-y-2 border border-gray-200 dark:border-gray-700 rounded-md p-3">
          {categories.map((category) => (
            <div key={category.id} className="flex items-center space-x-2">
              <Checkbox
                id={`category-${category.id}`}
                checked={filters.categoryIds.includes(category.id)}
                onCheckedChange={() => toggleArrayFilter('categoryIds', category.id)}
              />
              <Label
                htmlFor={`category-${category.id}`}
                className="text-sm font-normal cursor-pointer flex-1"
              >
                {category.name}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Idioma */}
      <div>
        <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white mb-3 flex items-center gap-2">
          <Icon name="globe" size="sm" />
          Idioma
        </h3>
        <div className="space-y-2">
          {IDIOMAS.map((idioma) => (
            <div key={idioma.value} className="flex items-center space-x-2">
              <Checkbox
                id={`lang-${idioma.value}`}
                checked={filters.languages.includes(idioma.value)}
                onCheckedChange={() => toggleArrayFilter('languages', idioma.value)}
              />
              <Label
                htmlFor={`lang-${idioma.value}`}
                className="text-sm font-normal cursor-pointer"
              >
                {idioma.label}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Data */}
      <div>
        <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white mb-3 flex items-center gap-2">
          <Icon name="calendar" size="sm" />
          Data de Publicação
        </h3>
        <div className="space-y-3">
          <div>
            <Label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
              De
            </Label>
            <Input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => updateFilter('dateFrom', e.target.value)}
              className="w-full"
            />
          </div>
          <div>
            <Label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
              Até
            </Label>
            <Input
              type="date"
              value={filters.dateTo}
              onChange={(e) => updateFilter('dateTo', e.target.value)}
              className="w-full"
            />
          </div>
        </div>
      </div>

      <Separator />

      {/* Autoria */}
      <div>
        <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white mb-3 flex items-center gap-2">
          <Icon name="user" size="sm" />
          Autoria
        </h3>
        <Input
          type="text"
          placeholder="Nome do autor"
          value={filters.author}
          onChange={(e) => updateFilter('author', e.target.value)}
          className="w-full"
        />
      </div>

      <Separator />

      {/* Tipo de Conteúdo */}
      <div>
        <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white mb-3 flex items-center gap-2">
          <Icon name="fileText" size="sm" />
          Tipo de Conteúdo
        </h3>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="has-pdf"
              checked={filters.hasPdf === true}
              onCheckedChange={(checked) => 
                updateFilter('hasPdf', checked ? true : null)
              }
            />
            <Label htmlFor="has-pdf" className="text-sm font-normal cursor-pointer">
              Com PDF disponível
            </Label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="highlighted"
              checked={filters.highlighted === true}
              onCheckedChange={(checked) => 
                updateFilter('highlighted', checked ? true : null)
              }
            />
            <Label htmlFor="highlighted" className="text-sm font-normal cursor-pointer">
              Artigos em destaque
            </Label>
          </div>
        </div>
      </div>

      <Separator />

      {/* Ordenação */}
      <div>
        <h3 className="font-display font-semibold text-sm text-bhub-navy-dark dark:text-white mb-3 flex items-center gap-2">
          <Icon name="barChart" size="sm" />
          Ordenação
        </h3>
        <div className="space-y-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                Ordenar por
              </Label>
              {filters.sortBy === 'impact_score' && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button type="button" className="text-xs text-bhub-teal-primary hover:text-bhub-teal-primary/80">
                      <Icon name="barChart" size="sm" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="right" className="max-w-xs">
                    <div className="space-y-1">
                      <p className="font-semibold">Score de Relevância (1-10)</p>
                      <p className="text-xs">
                        Calculado automaticamente com base em:
                      </p>
                      <ul className="text-xs list-disc list-inside space-y-0.5 ml-2">
                        <li>Palavras-chave de alto impacto (meta-análise, revisão sistemática, etc.)</li>
                        <li>Periódico de publicação</li>
                        <li>Presença de DOI</li>
                        <li>Qualidade e completude do abstract</li>
                        <li>Dados quantitativos</li>
                      </ul>
                      <p className="text-xs mt-1 pt-1 border-t border-white/20">
                        <strong>Uso:</strong> Artigos com score ≥7 são considerados de alto impacto.
                      </p>
                    </div>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
            <Select
              value={filters.sortBy}
              onValueChange={(value: FilterState['sortBy']) => 
                updateFilter('sortBy', value)
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="publication_date">Data de publicação</SelectItem>
                <SelectItem value="title">Título</SelectItem>
                <SelectItem value="impact_score">Relevância</SelectItem>
                <SelectItem value="view_count">Mais visualizados</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
              Ordem
            </Label>
            <Select
              value={filters.sortOrder}
              onValueChange={(value: FilterState['sortOrder']) => 
                updateFilter('sortOrder', value)
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desc">Decrescente</SelectItem>
                <SelectItem value="asc">Crescente</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Clear Filters Button */}
      {activeFiltersCount > 0 && (
        <Button
          variant="outline"
          onClick={onClearFilters}
          className="w-full"
        >
          <Icon name="close" size="sm" />
          Limpar Filtros ({activeFiltersCount})
        </Button>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop: Fixed Sidebar */}
      <aside className={cn('hidden lg:block w-80 flex-shrink-0', className)}>
        <div className="sticky top-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 max-h-[calc(100vh-2rem)] overflow-y-auto">
          <div className="mb-4">
            <h2 className="font-display font-bold text-lg text-bhub-navy-dark dark:text-white mb-1">
              Filtros Avançados
            </h2>
            {activeFiltersCount > 0 && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {activeFiltersCount} filtro(s) ativo(s)
              </p>
            )}
          </div>
          <FilterContent />
        </div>
      </aside>

      {/* Mobile: Sheet */}
      <div className="lg:hidden">
        <Sheet open={isMobileOpen} onOpenChange={setIsMobileOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" className="w-full justify-between">
              <span className="flex items-center gap-2">
                <Icon name="filter" size="sm" />
                Filtros
                {activeFiltersCount > 0 && (
                  <span className="bg-bhub-teal-primary text-white text-xs px-2 py-0.5 rounded-full">
                    {activeFiltersCount}
                  </span>
                )}
              </span>
              <Icon name="chevronRight" size="sm" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-[85vw] sm:w-[400px] overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Filtros Avançados</SheetTitle>
              <SheetDescription>
                Use os filtros abaixo para refinar sua busca por artigos científicos.
              </SheetDescription>
            </SheetHeader>
            <div className="mt-6">
              <FilterContent />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}

