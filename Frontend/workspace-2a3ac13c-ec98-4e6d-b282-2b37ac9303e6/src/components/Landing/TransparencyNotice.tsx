'use client';

import React from 'react';
import { cn } from '@/lib/utils';

export function TransparencyNotice() {
  return (
    <div className={cn(
      "w-full bg-blue-50 dark:bg-blue-900/20",
      "border border-blue-200 dark:border-blue-800 rounded-lg",
      "px-6 py-4 mb-8"
    )}>
      <div className="flex items-start gap-3">
        <div className="shrink-0 mt-0.5">
          <svg 
            className="w-5 h-5 text-blue-600 dark:text-blue-400" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
            />
          </svg>
        </div>
        <p className="font-body text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          O BHub atua exclusivamente como <strong className="font-semibold">agregador de conteúdo científico</strong>, 
          respeitando integralmente a autoria, os direitos e os termos das fontes originais.
        </p>
      </div>
    </div>
  );
}
