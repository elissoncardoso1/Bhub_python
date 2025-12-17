'use client';

import React from 'react';
import { Icon } from '@/components/Icon/Icon';
import { Button } from '@/components/Button/Button';
import { cn } from '@/lib/utils';

export function Footer() {
  const currentYear = new Date().getFullYear();

  const footerLinks = {
    explore: [
      { name: 'Artigos Recentes', href: '/articles' },
      { name: 'Artigos em Destaque', href: '/featured' },
      { name: 'Categorias', href: '/categories' },
      { name: 'Autores', href: '/authors' }
    ],
    resources: [
      { name: 'Guia de Autores', href: '/author-guide' },
      { name: 'Política Editorial', href: '/editorial-policy' },
      { name: 'Diretrizes de Submissão', href: '/submission-guidelines' },
      { name: 'FAQ', href: '/faq' }
    ],
    connect: [
      { name: 'Newsletter', href: '/newsletter' },
      { name: 'Contato', href: '/contact' },
      { name: 'Twitter', href: 'https://twitter.com/bhub' },
      { name: 'LinkedIn', href: 'https://linkedin.com/company/bhub' }
    ]
  };

  return (
    <footer className="bg-bhub-dark-gray text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="lg:col-span-1">
            <a href="/" className="inline-block mb-4">
              <img
                src="/Dark_logo.svg"
                alt="BHub"
                className="h-7 w-auto"
              />
            </a>
            <p className="font-body font-light text-sm text-gray-300 mb-6 leading-relaxed">
              Repositório científico dedicado à análise do comportamento, 
              conectando pesquisadores e promovendo o conhecimento científico.
            </p>
            <div className="flex space-x-3">
              <Button
                variant="ghost"
                size="sm"
                className="text-gray-400 hover:text-bhub-teal-primary p-2"
                aria-label="Twitter"
              >
                <Icon name="twitter" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-gray-400 hover:text-bhub-teal-primary p-2"
                aria-label="LinkedIn"
              >
                <Icon name="linkedin" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-gray-400 hover:text-bhub-teal-primary p-2"
                aria-label="GitHub"
              >
                <Icon name="github" />
              </Button>
            </div>
          </div>

          {/* Explore Links */}
          <div>
            <h4 className="font-body font-semibold text-base text-white mb-4">
              Explorar
            </h4>
            <ul className="space-y-2">
              {footerLinks.explore.map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    className="font-body font-light text-sm text-gray-300 hover:text-bhub-teal-primary transition-colors"
                  >
                    {link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources Links */}
          <div>
            <h4 className="font-body font-semibold text-base text-white mb-4">
              Recursos
            </h4>
            <ul className="space-y-2">
              {footerLinks.resources.map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    className="font-body font-light text-sm text-gray-300 hover:text-bhub-teal-primary transition-colors"
                  >
                    {link.name}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Connect Links */}
          <div>
            <h4 className="font-body font-semibold text-base text-white mb-4">
              Conectar
            </h4>
            <ul className="space-y-2">
              {footerLinks.connect.map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    className={cn(
                      "font-body font-light text-sm text-gray-300 hover:text-bhub-teal-primary transition-colors",
                      link.href.startsWith('http') && "flex items-center gap-1"
                    )}
                  >
                    {link.name}
                    {link.href.startsWith('http') && (
                      <Icon name="external" size="sm" />
                    )}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom section */}
        <div className="mt-12 pt-8 border-t border-gray-700">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex flex-col items-center md:items-start gap-2">
              <p className="font-body font-light text-sm text-gray-400">
                © {currentYear} BHub. Todos os direitos reservados.
              </p>
              {/* Powered by DeepSeek - Discreto */}
              <div className="flex items-center gap-1.5 opacity-40 hover:opacity-60 transition-opacity">
                <span className="font-body font-light text-[10px]" style={{ color: '#D8FFDB' }}>
                  Powered by
                </span>
                <a
                  href="https://www.deepseek.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center"
                  aria-label="DeepSeek AI"
                >
                  <img
                    src="/icons/deepseek-text.svg"
                    alt="DeepSeek"
                    className="h-3.5 w-auto"
                    style={{ filter: 'brightness(0) invert(1)' }}
                  />
                </a>
              </div>
            </div>
            <div className="flex space-x-6 mt-4 md:mt-0">
              <a
                href="/privacy"
                className="font-body font-light text-sm text-gray-400 hover:text-bhub-teal-primary transition-colors"
              >
                Privacidade
              </a>
              <a
                href="/terms"
                className="font-body font-light text-sm text-gray-400 hover:text-bhub-teal-primary transition-colors"
              >
                Termos
              </a>
              <a
                href="/accessibility"
                className="font-body font-light text-sm text-gray-400 hover:text-bhub-teal-primary transition-colors"
              >
                Acessibilidade
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}