'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/Icon/Icon';
import { FeedDialog } from './FeedDialog';
import { toast } from '@/hooks/use-toast';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from '@/components/Badge/Badge';

export function FeedsPageClient() {
  const { data: session } = useSession();
  const [feeds, setFeeds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedFeed, setSelectedFeed] = useState<any>(null);
  const [syncing, setSyncing] = useState<number | null>(null);

  const fetchFeeds = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/feeds?pagination.page_size=100`, {
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      });
      const data = await res.json();
      setFeeds(data.feeds);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.accessToken) {
       fetchFeeds();
    }
  }, [session]);

  const handleEdit = (feed: any) => {
    setSelectedFeed(feed);
    setIsDialogOpen(true);
  };

  const handleCreate = () => {
    setSelectedFeed(null);
    setIsDialogOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir este feed?')) return;
    
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/feeds/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      });
      toast({ title: 'Sucesso', description: 'Feed removido.' });
      fetchFeeds();
    } catch (error) {
      toast({ title: 'Erro', description: 'Falha ao remover.', variant: 'destructive' });
    }
  };

  const handleSync = async (id: number) => {
    setSyncing(id);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/feeds/${id}/sync`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session?.accessToken}` },
      });
      
      const data = await res.json();
      toast({ 
        title: 'Sincronização Concluída', 
        description: `${data.new_articles} novos artigos encontrados.`,
      });
      fetchFeeds();
    } catch (error) {
      toast({ title: 'Erro', description: 'Falha na sincronização.', variant: 'destructive' });
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-display font-bold text-gray-900 dark:text-white">Gerenciar Feeds</h1>
        <Button onClick={handleCreate} className="bg-bhub-teal-primary text-white">
          <Icon name="plus" className="mr-2 h-4 w-4" />
          Novo Feed
        </Button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>URL</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Última Sinc.</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
               <TableRow>
                 <TableCell colSpan={5} className="text-center py-8 text-gray-500">Carregando...</TableCell>
               </TableRow>
            ) : feeds.length === 0 ? (
               <TableRow>
                 <TableCell colSpan={5} className="text-center py-8 text-gray-500">Nenhum feed cadastrado.</TableCell>
               </TableRow>
            ) : (
              feeds.map((feed) => (
                <TableRow key={feed.id}>
                  <TableCell className="font-medium">{feed.name}</TableCell>
                  <TableCell className="max-w-[200px] truncate" title={feed.feed_url}>{feed.feed_url}</TableCell>
                  <TableCell>
                    <Badge 
                      label={feed.is_active ? 'Ativo' : 'Inativo'} 
                      variant="outline" 
                      className={feed.is_active ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-700'} 
                    />
                  </TableCell>
                  <TableCell>
                    {feed.last_sync_at ? new Date(feed.last_sync_at).toLocaleDateString() : '-'}
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => handleSync(feed.id)}
                      disabled={syncing === feed.id}
                    >
                      <Icon name="refreshCw" className={`h-4 w-4 ${syncing === feed.id ? 'animate-spin' : ''}`} />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleEdit(feed)}>
                      <Icon name="edit" className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(feed.id)} className="text-red-500 hover:text-red-700">
                      <Icon name="trash" className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <FeedDialog 
        open={isDialogOpen} 
        onOpenChange={setIsDialogOpen} 
        feed={selectedFeed}
        onSuccess={fetchFeeds}
      />
    </div>
  );
}
