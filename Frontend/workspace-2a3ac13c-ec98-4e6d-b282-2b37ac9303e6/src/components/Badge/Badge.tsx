'use client';

import React from 'react';
import { BadgeProps } from '@/types/common';
import { cn } from '@/lib/utils';

export function Badge({ 
  label, 
  icon, 
  variant = 'default', 
  className 
}: BadgeProps) {
  const baseClasses = 'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors';
  
  const variantClasses = {
    default: 'bg-bhub-navy-light text-bhub-navy-dark',
    featured: 'border border-bhub-teal-primary text-bhub-teal-primary bg-transparent',
    light: 'bg-bhub-teal-light/50 text-bhub-navy-dark',
    outline: 'border'
  };

  return (
    <span className={cn(baseClasses, variantClasses[variant], className)}>
      {icon && <span className="w-3 h-3">{icon}</span>}
      {label}
    </span>
  );
}

export function BehaviorBadge({ label, className }: { label: string; className?: string }) {
  return (
    <Badge 
      label={label} 
      variant="default" 
      className={className}
    />
  );
}