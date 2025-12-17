'use client';

import React from 'react';
import { AvatarProps } from '@/types/common';
import { cn } from '@/lib/utils';

export function Avatar({ 
  name, 
  initials, 
  size = 'md', 
  variant = 'default',
  src,
  alt = name,
  className 
}: AvatarProps) {
  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-sm',
    lg: 'w-12 h-12 text-base'
  };

  const variantClasses = {
    default: 'bg-bhub-navy-light text-bhub-navy-dark',
    featured: 'bg-gradient-to-br from-bhub-teal-primary to-bhub-navy-dark text-white'
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const displayInitials = initials || getInitials(name);

  return (
    <div 
      className={cn(
        'relative inline-flex items-center justify-center rounded-full font-display font-bold',
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
    >
      {src ? (
        <img 
          src={src} 
          alt={alt}
          className="w-full h-full rounded-full object-cover"
        />
      ) : (
        <span>{displayInitials}</span>
      )}
    </div>
  );
}

export function AuthorAvatar({ 
  name, 
  initials, 
  size = 'md',
  src,
  className 
}: { 
  name: string; 
  initials?: string; 
  size?: 'sm' | 'md' | 'lg';
  src?: string;
  className?: string;
}) {
  return (
    <Avatar 
      name={name}
      initials={initials}
      size={size}
      variant="featured"
      src={src}
      className={className}
    />
  );
}