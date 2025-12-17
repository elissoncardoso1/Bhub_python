'use client';

import { useSession, signOut } from 'next-auth/react';
import { Icon } from '@/components/Icon/Icon';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function AdminHeader() {
  const { data: session } = useSession();
  const userInitials = session?.user?.email?.substring(0, 2).toUpperCase() || 'AD';

  return (
    <header className="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 h-16 flex items-center px-6 justify-between shadow-sm">
      <div className="flex items-center gap-4">
        {/* Mobile menu trigger could go here */}
        <h1 className="font-display font-bold text-lg text-gray-800 dark:text-white md:hidden">
          BHub Admin
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {/* <Button variant="ghost" size="icon" className="text-gray-500">
          <Icon name="bell" />
        </Button> */}
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full">
              <Avatar className="h-9 w-9 border border-gray-200">
                <AvatarFallback className="bg-bhub-teal-light text-bhub-teal-primary font-bold">
                  {userInitials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{session?.user?.name || 'Administrador'}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {session?.user?.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => signOut({ callbackUrl: '/auth/signin' })}>
              <Icon name="logout" className="mr-2 h-4 w-4" />
              <span>Sair</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
