'use client';

import React, { useState, useEffect } from 'react';
import { useTheme } from '@/components/Theme/ThemeProvider';
import { IconButton } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { cn } from '@/lib/utils';

export function Header() {
  const { isDark, toggle } = useTheme();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch by only rendering theme toggle after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  const navigation = [
    { name: 'Início', href: '/', icon: 'home' },
    { name: 'Artigos', href: '/articles', icon: 'fileText' },
    { name: 'Repositório', href: '/repository', icon: 'library' },
    { name: 'Sobre', href: '/about', icon: 'users' }
  ];

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <a href="/" className="flex-shrink-0 flex items-center">
              {mounted ? (
                <img
                  src={isDark ? "/Dark_logo.svg" : "/Light_logo.svg"}
                  alt="BHub"
                  className="h-7 w-auto"
                />
              ) : (
                <img
                  src="/Light_logo.svg"
                  alt="BHub"
                  className="h-7 w-auto"
                />
              )}
            </a>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            {navigation.map((item) => (
              <a
                key={item.name}
                href={item.href}
                className="flex items-center gap-2 text-gray-700 dark:text-gray-300 hover:text-bhub-teal-primary dark:hover:text-bhub-teal-primary transition-colors font-body font-medium"
              >
                <Icon name={item.icon as any} size="sm" />
                {item.name}
              </a>
            ))}
          </nav>

          {/* Right side actions */}
          <div className="flex items-center gap-3">
            {/* Search button */}
            <IconButton
              icon={<Icon name="search" />}
              variant="ghost"
              className="text-gray-600 dark:text-gray-400 hover:text-bhub-teal-primary"
              aria-label="Pesquisar"
            />

            {/* Theme toggle - only render after mount to prevent hydration mismatch */}
            {mounted ? (
              <IconButton
                icon={<Icon name={isDark ? 'sun' : 'moon'} />}
                variant="ghost"
                className="text-gray-600 dark:text-gray-400 hover:text-bhub-teal-primary"
                onClick={toggle}
                aria-label="Alternar tema"
              />
            ) : (
              <div className="w-10 h-10" /> // Placeholder to prevent layout shift
            )}

            {/* Notifications */}
            <IconButton
              icon={<Icon name="bell" />}
              variant="ghost"
              className="text-gray-600 dark:text-gray-400 hover:text-bhub-teal-primary"
              aria-label="Notificações"
            />

            {/* Mobile menu button */}
            <IconButton
              icon={<Icon name={isMobileMenuOpen ? 'close' : 'menu'} />}
              variant="ghost"
              className="md:hidden text-gray-600 dark:text-gray-400 hover:text-bhub-teal-primary"
              onClick={toggleMobileMenu}
              aria-label="Menu"
            />
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-gray-200 dark:border-gray-700 py-4">
            <nav className="flex flex-col space-y-3">
              {navigation.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2 text-gray-700 dark:text-gray-300 hover:text-bhub-teal-primary dark:hover:text-bhub-teal-primary hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors font-body font-medium"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <Icon name={item.icon as any} size="sm" />
                  {item.name}
                </a>
              ))}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}