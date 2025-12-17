'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icon } from '@/components/Icon/Icon';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export function AdminSidebar() {
  const pathname = usePathname();

  const links = [
    { href: '/admin', label: 'Dashboard', icon: 'grid' },
    { href: '/admin/analytics', label: 'Analytics', icon: 'barChart' },
    { href: '/admin/feeds', label: 'Feeds RSS', icon: 'rss' },
    { href: '/admin/articles', label: 'Artigos', icon: 'bookOpen' },
    // { href: '/admin/crawler', label: 'Crawler', icon: 'spider' }, // spider icon not sure if exists in Icon component wrapper
    // { href: '/admin/users', label: 'Usuários', icon: 'users' },
    // { href: '/admin/settings', label: 'Configurações', icon: 'settings' },
  ];

  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-bhub-navy-dark text-white shadow-lg hidden md:flex flex-col">
      <div className="p-6 border-b border-white/10 flex items-center gap-2">
        <div className="w-8 h-8 bg-bhub-teal-primary rounded-lg flex items-center justify-center">
          <Icon name="grid" className="text-white" />
        </div>
        <span className="font-display font-bold text-xl tracking-tight">BHub Admin</span>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {links.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link key={link.href} href={link.href} passHref>
              <Button
                variant="ghost"
                className={cn(
                  "w-full justify-start text-left font-body",
                  isActive 
                    ? "bg-bhub-teal-primary text-white hover:bg-bhub-teal-primary/90" 
                    : "text-white/70 hover:text-white hover:bg-white/10"
                )}
              >
                <Icon name={link.icon as any} className="mr-2 h-4 w-4" />
                {link.label}
              </Button>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/10">
        <div className="bg-white/5 rounded-lg p-3">
          <p className="text-xs text-white/50 mb-1">Status do Sistema</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs font-medium text-green-400">Online</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
