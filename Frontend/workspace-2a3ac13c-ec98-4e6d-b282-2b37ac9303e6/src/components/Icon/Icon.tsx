'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { 
  Heart, 
  Bookmark, 
  Share2, 
  TrendingUp, 
  Calendar,
  Clock,
  User,
  Search,
  Filter,
  Menu,
  X,
  ChevronRight,
  ChevronLeft,
  Star,
  Eye,
  EyeOff,
  Download,
  ExternalLink,
  Mail,
  Twitter,
  Linkedin,
  Github,
  BookOpen,
  FileText,
  Award,
  Users,
  BarChart3,
  Settings,
  LogOut,
  Sun,
  Moon,
  Bell,
  Home,
  Library,
  Archive,
  Check,
  CheckCircle,
  Play,
  AlertTriangle,
  Folder,
  ArrowRight,
  Phone,
  MapPin,
  Send,
  Rss,
  Globe,
  Languages,
  Loader2,
  Upload,
  RefreshCw,
  Database,
  LayoutGrid
} from 'lucide-react';

export interface IconProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const iconMap = {
  heart: Heart,
  bookmark: Bookmark,
  share: Share2,
  trending: TrendingUp,
  calendar: Calendar,
  clock: Clock,
  user: User,
  search: Search,
  filter: Filter,
  menu: Menu,
  close: X,
  chevronRight: ChevronRight,
  chevronLeft: ChevronLeft,
  star: Star,
  eye: Eye,
  eyeOff: EyeOff,
  download: Download,
  external: ExternalLink,
  mail: Mail,
  twitter: Twitter,
  linkedin: Linkedin,
  github: Github,
  bookOpen: BookOpen,
  fileText: FileText,
  award: Award,
  users: Users,
  barChart: BarChart3,
  settings: Settings,
  logout: LogOut,
  sun: Sun,
  moon: Moon,
  bell: Bell,
  home: Home,
  library: Library,
  archive: Archive,
  check: Check,
  checkCircle: CheckCircle,
  play: Play,
  alert: AlertTriangle,
  folder: Folder,
  arrowRight: ArrowRight,
  phone: Phone,
  mapPin: MapPin,
  send: Send,
  rss: Rss,
  globe: Globe,
  languages: Languages,
  loader: Loader2,
  loader2: Loader2,
  upload: Upload,
  refresh: RefreshCw,
  database: Database,
  grid: LayoutGrid
};

export function Icon({ name, size = 'md', className }: IconProps) {
  const IconComponent = iconMap[name as keyof typeof iconMap];
  
  if (!IconComponent) {
    console.warn(`Icon "${name}" not found`);
    return null;
  }

  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6'
  };

  return (
    <IconComponent className={cn(sizeClasses[size], className)} />
  );
}

// Icon library exports
export {
  Heart,
  Bookmark,
  Share2,
  TrendingUp,
  Calendar,
  Clock,
  User,
  Search,
  Filter,
  Menu,
  X,
  ChevronRight,
  ChevronLeft,
  Star,
  Eye,
  Download,
  ExternalLink,
  Mail,
  Twitter,
  Linkedin,
  Github,
  BookOpen,
  FileText,
  Award,
  Users,
  BarChart3,
  Settings,
  LogOut,
  Sun,
  Moon,
  Bell,
  Home,
  Library,
  Archive,
  Check,
  Play,
  AlertTriangle,
  Folder,
  ArrowRight,
  Phone,
  MapPin,
  Send
};