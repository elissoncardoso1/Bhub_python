'use client';

import React from 'react';
import { cn } from '@/lib/utils';

export function LandingIntroBanner() {
  return (
    <div className={cn(
      "w-full bg-linear-to-r from-bhub-teal-primary/5 to-blue-50/50 dark:from-bhub-teal-primary/10 dark:to-gray-800",
      "border-l-4 border-bhub-teal-primary",
      "p-6 md:p-8 rounded-lg shadow-sm backdrop-blur-sm",
      "mb-8 flex flex-col md:flex-row items-center justify-between gap-6"
    )}>
      <div className="flex-1 space-y-2 text-center md:text-left">
        <h1 className="font-display font-bold text-xl md:text-2xl text-bhub-navy-dark dark:text-white">
          Agregador científico em Análise do Comportamento
        </h1>
        <p className="font-body text-sm md:text-base text-gray-600 dark:text-gray-300 max-w-2xl leading-relaxed">
          Centralizamos o conhecimento científico através da curadoria automática de periódicos e portais via RSS, 
          facilitando o acesso à informação de qualidade.
        </p>
      </div>
      
      <div className="shrink-0 hidden md:flex items-center justify-center bg-white dark:bg-gray-700 p-4 rounded-full shadow-sm border border-gray-100 dark:border-gray-600">
        <svg 
          className="w-8 h-8 text-bhub-teal-primary" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
        </svg>
      </div>
    </div>
  );
}
