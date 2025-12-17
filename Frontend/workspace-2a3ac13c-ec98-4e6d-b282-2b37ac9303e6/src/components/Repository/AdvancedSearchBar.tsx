'use client';

import React, { useState, KeyboardEvent } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { cn } from '@/lib/utils';

interface AdvancedSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  placeholder?: string;
  className?: string;
}

export function AdvancedSearchBar({
  value,
  onChange,
  onSearch,
  placeholder = 'reinforcement AND resurgence NOT animal',
  className
}: AdvancedSearchBarProps) {
  const [isFocused, setIsFocused] = useState(false);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onSearch();
    }
  };

  return (
    <div className={cn('relative w-full', className)}>
      <div className={cn(
        'relative flex items-center gap-2 rounded-lg border transition-all',
        'bg-white dark:bg-gray-800',
        'border-gray-300 dark:border-gray-600',
        isFocused && 'ring-2 ring-bhub-teal-primary/50 border-bhub-teal-primary',
        'shadow-sm'
      )}>
        <div className="absolute left-4 flex items-center pointer-events-none">
          <Icon name="search" className="text-gray-400 dark:text-gray-500" size="md" />
        </div>
        
        <Input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          className={cn(
            'w-full pl-12 pr-32 py-3',
            'text-base font-body',
            'border-0 focus-visible:ring-0 focus-visible:ring-offset-0',
            'bg-transparent'
          )}
        />
        
        <div className="absolute right-2 flex items-center gap-2">
          <Button
            variant="default"
            size="sm"
            onClick={onSearch}
            className="bg-bhub-teal-primary hover:bg-bhub-teal-primary/90 text-white"
          >
            <Icon name="search" size="sm" />
            Buscar
          </Button>
        </div>
      </div>
      
      {/* Help text */}
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        <span className="font-medium">Dica:</span> Use operadores lógicos (AND, OR, NOT) e aspas para frases exatas. 
        Exemplo: <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">"comportamento verbal" AND ABA</code>
      </div>
    </div>
  );
}

