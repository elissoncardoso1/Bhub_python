'use client';

import React from 'react';
import { ButtonProps } from '@/types/common';
import { cn } from '@/lib/utils';

export function Button({ 
  children,
  variant = 'default',
  size = 'md',
  icon,
  iconPosition = 'left',
  className,
  disabled,
  ...props 
}: ButtonProps) {
  const baseClasses = 'inline-flex items-center justify-center gap-2 rounded-md font-body font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bhub-teal-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
  
  const variantClasses = {
    default: 'bg-bhub-teal-primary text-white hover:bg-bhub-teal-primary/90',
    outline: 'border border-bhub-navy-dark dark:border-gray-400 text-bhub-navy-dark dark:text-gray-200 hover:bg-bhub-navy-light dark:hover:bg-gray-700',
    ghost: 'text-bhub-navy-dark dark:text-gray-200 hover:bg-bhub-navy-light dark:hover:bg-gray-700',
    link: 'text-bhub-teal-primary underline-offset-4 hover:underline',
    cta: 'bg-gradient-to-r from-bhub-teal-primary to-bhub-navy-dark text-white hover:from-bhub-teal-primary/90 hover:to-bhub-navy-dark/90 px-6 py-3'
  };

  const sizeClasses = {
    sm: 'h-8 px-3 text-sm',
    md: 'h-10 px-4 text-base',
    lg: 'h-12 px-6 text-lg'
  };

  const renderContent = () => {
    if (icon && iconPosition === 'left') {
      return (
        <>
          <span className="w-4 h-4">{icon}</span>
          {children}
        </>
      );
    }
    
    if (icon && iconPosition === 'right') {
      return (
        <>
          {children}
          <span className="w-4 h-4">{icon}</span>
        </>
      );
    }
    
    return children;
  };

  return (
    <button
      className={cn(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      disabled={disabled}
      {...props}
    >
      {renderContent()}
    </button>
  );
}

export function IconButton({ 
  icon,
  size = 'md',
  variant = 'ghost',
  className,
  ...props 
}: { 
  icon: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline' | 'ghost';
  className?: string;
} & Omit<ButtonProps, 'children'>) {
  return (
    <Button
      variant={variant}
      size={size}
      icon={icon}
      className={cn('p-2', className)}
      {...props}
    />
  );
}

export function CTAButton({ 
  children,
  className,
  ...props 
}: ButtonProps) {
  return (
    <Button
      variant="cta"
      className={cn('font-display font-bold', className)}
      {...props}
    >
      {children}
    </Button>
  );
}