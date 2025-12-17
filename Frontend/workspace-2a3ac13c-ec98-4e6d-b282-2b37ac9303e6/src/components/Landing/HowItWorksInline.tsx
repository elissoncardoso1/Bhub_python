'use client';

import React from 'react';
import { cn } from '@/lib/utils';

const features = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
    text: 'Coleta automática via RSS'
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
    ),
    text: 'Organização por temas e fontes'
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
      </svg>
    ),
    text: 'Links diretos para o conteúdo original'
  }
];

export function HowItWorksInline() {
  return (
    <div className="w-full mb-10">
      <div className="flex flex-col md:flex-row items-stretch justify-center gap-6">
        {features.map((feature, index) => (
          <div 
            key={index}
            className={cn(
              "flex-1 flex flex-col items-center text-center p-6 rounded-xl border border-gray-100 dark:border-gray-700",
              "bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-all duration-300",
              "group cursor-default"
            )}
          >
            <div className={cn(
              "p-3 rounded-full mb-4 bg-gray-50 dark:bg-gray-700 group-hover:bg-bhub-teal-primary/10 transition-colors",
              "text-gray-400 group-hover:text-bhub-teal-primary"
            )}>
              {feature.icon}
            </div>
            <span className="font-body font-medium text-gray-800 dark:text-gray-100">
              {feature.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
