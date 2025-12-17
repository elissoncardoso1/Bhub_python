export interface ThemeContextType {
  isDark: boolean;
  toggle: () => void;
}

export interface BadgeProps {
  label: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'featured' | 'light' | 'outline';
  className?: string;
}

export interface AvatarProps {
  name: string;
  initials?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'featured';
  src?: string;
  alt?: string;
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'link' | 'cta';
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

export interface IconProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}