'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import { Icon } from '@/components/Icon/Icon';
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
import { ArticleAdminService } from '@/services/articleAdminService';

export function ArticlesPageClient() {
  const { data: session } = useSession();
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const fetchArticles = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', pageSize.toString());
      
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/articles?${params.toString()}`,
        {
          headers: { Authorization: `Bearer ${session?.accessToken}` },
        }
      );
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      setArticles(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error(error);
      toast({ title: 'Erro', description: 'Falha ao carregar artigos', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (session?.accessToken) {
       fetchArticles();
    }
  }, [session, page]);

  const handleDelete = async (id: number) => {
    if (!confirm('Tem certeza que deseja excluir este artigo?')) return;
    
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/articles/${id}`,
        {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${session?.accessToken}` },
        }
      );
      
      if (!res.ok) {
        throw new Error('Failed to delete');
      }
      
      toast({ title: 'Sucesso', description: 'Artigo removido.' });
      fetchArticles();
    } catch (error) {
      toast({ title: 'Erro', description: 'Falha ao remover', variant: 'destructive' });
    }
  };

  const handleToggleHighlight = async (id: number, currentState: boolean) => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/articles/${id}/highlight`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session?.accessToken}`,
          },
          body: JSON.stringify({ highlighted: !currentState }),
        }
      );
      
      if (!res.ok) {
        throw new Error('Failed to toggle highlight');
      }
      
      toast({ 
        title: 'Sucesso', 
        description: currentState ? 'Artigo desmarcado como destacado' : 'Artigo marcado como destacado' 
      });
      fetchArticles();
    } catch (error) {
      toast({ title: 'Erro', description: 'Falha ao atualizar', variant: 'destructive' });
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-gray-900 dark:text-white">Gerenciar Artigos</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{total} artigos encontrados</p>
        </div>
        <Button 
          className="bg-bhub-teal-primary text-white"
          onClick={() => toast({ 
            title: 'Em desenvolvimento', 
            description: 'Função de criar artigo será implementada em breve.' 
          })}
        >
          <Icon name="plus" className="mr-2 h-4 w-4" />
          Novo Artigo
        </Button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Título</TableHead>
              <TableHead>Categoria</TableHead>
              <TableHead>Fonte</TableHead>
              <TableHead>Data</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">Carregando...</TableCell>
              </TableRow>
            ) : articles.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">Nenhum artigo encontrado.</TableCell>
              </TableRow>
            ) : (
              articles.map((article) => (
                <TableRow key={article.id}>
                  <TableCell className="font-medium max-w-[300px]">
                    <div className="truncate" title={article.title}>{article.title}</div>
                  </TableCell>
                  <TableCell>
                    {article.category ? (
                      <Badge label={article.category.name} variant="outline" className="bg-blue-50 text-blue-700" />
                    ) : '-'}
                  </TableCell>
                  <TableCell className="max-w-[150px] truncate text-sm" title={article.feed?.name}>
                    {article.feed?.name || '-'}
                  </TableCell>
                  <TableCell className="text-sm">
                    {article.created_at ? new Date(article.created_at).toLocaleDateString('pt-BR') : '-'}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {article.is_published && (
                        <Badge label="Publicado" variant="outline" className="bg-green-50 text-green-700" />
                      )}
                      {article.highlighted && (
                        <Icon name="star" className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleToggleHighlight(article.id, article.highlighted)}
                      title={article.highlighted ? 'Remover destaque' : 'Destacar'}
                    >
                      <Icon 
                        name="star" 
                        className={`h-4 w-4 ${article.highlighted ? 'fill-yellow-500 text-yellow-500' : ''}`} 
                      />
                    </Button>
                    <Button variant="ghost" size="sm" title="Editar">
                      <Icon name="edit" className="h-4 w-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleDelete(article.id)} 
                      className="text-red-500 hover:text-red-700"
                      title="Deletar"
                    >
                      <Icon name="trash" className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Página {page} de {totalPages}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              Próximo
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
