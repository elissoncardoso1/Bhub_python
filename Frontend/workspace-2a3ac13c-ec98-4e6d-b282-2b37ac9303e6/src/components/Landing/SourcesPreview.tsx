'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { FeedService, Feed } from '@/services/feedService';

export function SourcesPreview() {
  const [sources, setSources] = useState<Feed[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSources = async () => {
      try {
        const allSources = await FeedService.getAll();
        // Show first 8 sources
        setSources(allSources.slice(0, 8));
      } catch (error) {
        console.error('Error fetching sources:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSources();
  }, []);

  if (loading) {
    return (
      <div className="w-full bg-gray-50 dark:bg-gray-800 rounded-lg px-6 py-8 mb-8">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mx-auto" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      "w-full bg-linear-to-b from-gray-50 to-white dark:from-gray-800 dark:to-gray-900",
      "border border-gray-200 dark:border-gray-700 rounded-xl",
      "px-6 py-10 mb-12 shadow-sm"
    )}>
      <div className="text-center mb-8">
        <h2 className="font-display font-bold text-2xl text-bhub-navy-dark dark:text-white mb-2">
          Fontes científicas monitoradas
        </h2>
        <p className="font-body text-gray-500 dark:text-gray-400 text-sm">
          Acompanhamos os principais periódicos e portais da área
        </p>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {sources.map((source) => (
          <Link
            href={`/source/${source.id}`}
            key={source.id}
            className={cn(
              "group p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700",
              "hover:border-bhub-teal-primary/50 hover:shadow-md transition-all duration-300",
              "flex flex-col items-center text-center gap-2"
            )}
          >
             <div className="w-10 h-10 rounded-full bg-gray-50 dark:bg-gray-900 flex items-center justify-center text-gray-400 group-hover:text-bhub-teal-primary transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
             </div>
             <span className="font-body font-medium text-sm text-gray-700 dark:text-gray-200 line-clamp-2 group-hover:text-bhub-teal-primary transition-colors">
               {source.name}
             </span>
          </Link>
        ))}
      </div>

      <div className="text-center">
        <Link
          href="/repository"
          className={cn(
            "inline-flex items-center gap-2 px-6 py-2.5 rounded-full border border-bhub-teal-primary/30",
            "font-body font-medium text-bhub-teal-primary hover:bg-bhub-teal-primary hover:text-white",
            "transition-all duration-300 shadow-sm hover:shadow-md"
          )}
        >
          Ver todas as fontes
          <svg className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
          </svg>
        </Link>
      </div>
    </div>
  );
}
