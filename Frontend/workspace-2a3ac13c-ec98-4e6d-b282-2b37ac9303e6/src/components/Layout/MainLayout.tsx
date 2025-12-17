'use client';

import React from 'react';

interface MainLayoutProps {
  children: React.ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-bhub-light-gray dark:bg-gray-900">
      {children}
    </div>
  );
}