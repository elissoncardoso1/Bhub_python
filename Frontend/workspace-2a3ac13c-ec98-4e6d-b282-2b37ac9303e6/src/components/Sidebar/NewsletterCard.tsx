'use client';

import React, { useState } from 'react';
import { Button } from '@/components/Button/Button';
import { Icon } from '@/components/Icon/Icon';
import { cn } from '@/lib/utils';

interface NewsletterCardProps {
  className?: string;
}

export function NewsletterCard({ className }: NewsletterCardProps) {
  const [email, setEmail] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    setIsSubscribed(true);
    setIsLoading(false);
    setEmail('');
  };

  if (isSubscribed) {
    return (
      <div className={cn(
        'bg-gradient-to-br from-bhub-teal-primary to-bhub-navy-dark rounded-lg p-6 text-white',
        className
      )}>
        <div className="text-center">
          <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Icon name="mail" className="text-white" />
          </div>
          <h3 className="font-display font-bold text-lg mb-2">
            Inscrição Confirmada!
          </h3>
          <p className="font-body font-light text-sm text-white/90">
            Obrigado por se inscrever na nossa newsletter.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      'bg-gradient-to-br from-bhub-yellow-primary to-bhub-yellow-light rounded-lg p-6 border border-bhub-yellow-primary/20',
      className
    )}>
      {/* Header */}
      <div className="text-center mb-4">
        <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center mx-auto mb-3">
          <Icon name="mail" className="text-bhub-yellow-primary" />
        </div>
        <h3 className="font-display font-bold text-lg text-bhub-navy-dark mb-2">
          Newsletter BHub
        </h3>
        <p className="font-body font-light text-sm text-bhub-navy-dark/80">
          Receba os melhores artigos semanalmente
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Seu melhor e-mail"
          className="w-full px-3 py-2 border border-bhub-yellow-primary/30 rounded-md bg-white/80 backdrop-blur-sm text-bhub-navy-dark placeholder-bhub-navy-dark/50 font-body font-light text-sm focus:outline-none focus:ring-2 focus:ring-bhub-yellow-primary focus:border-transparent"
          required
        />
        
        <Button
          type="submit"
          variant="default"
          disabled={isLoading}
          className="w-full bg-bhub-navy-dark hover:bg-bhub-navy-dark/90 text-white font-medium"
        >
          {isLoading ? 'Inscrevendo...' : 'Inscrever-se'}
        </Button>
      </form>

      {/* Benefits */}
      <div className="mt-4 pt-4 border-t border-bhub-yellow-primary/20">
        <ul className="space-y-2">
          <li className="flex items-center gap-2 text-xs font-body font-light text-bhub-navy-dark/70">
            <div className="w-3 h-3 bg-bhub-navy-dark rounded-full flex items-center justify-center">
              <Icon name="check" className="text-white" size="sm" />
            </div>
            Artigos selecionados semanalmente
          </li>
          <li className="flex items-center gap-2 text-xs font-body font-light text-bhub-navy-dark/70">
            <div className="w-3 h-3 bg-bhub-navy-dark rounded-full flex items-center justify-center">
              <Icon name="check" className="text-white" size="sm" />
            </div>
            Conteúdo exclusivo
          </li>
          <li className="flex items-center gap-2 text-xs font-body font-light text-bhub-navy-dark/70">
            <div className="w-3 h-3 bg-bhub-navy-dark rounded-full flex items-center justify-center">
              <Icon name="check" className="text-white" size="sm" />
            </div>
            Cancelamento a qualquer momento
          </li>
        </ul>
      </div>
    </div>
  );
}