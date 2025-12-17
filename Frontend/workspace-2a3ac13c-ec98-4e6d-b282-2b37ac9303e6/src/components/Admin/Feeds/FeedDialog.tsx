'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icon } from '@/components/Icon/Icon';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from '@/hooks/use-toast';
import { useSession } from 'next-auth/react';

const feedSchema = z.object({
  name: z.string().min(1, 'Nome é obrigatório'),
  url: z.string().url('URL inválida'),
  journal_name: z.string().optional(),
});

type FeedFormValues = z.infer<typeof feedSchema>;

interface FeedDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  feed?: any; // Feed type TODO
  onSuccess: () => void;
}

export function FeedDialog({ open, onOpenChange, feed, onSuccess }: FeedDialogProps) {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(false);
  const isEditing = !!feed;

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FeedFormValues>({
    resolver: zodResolver(feedSchema),
    defaultValues: {
      name: feed?.name || '',
      url: feed?.feed_url || '',
      journal_name: feed?.journal_name || '',
    },
  });

  const onSubmit = async (data: FeedFormValues) => {
    setLoading(true);
    try {
      const url = isEditing 
        ? `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/feeds/${feed.id}`
        : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/admin/feeds`;
      
      const method = isEditing ? 'PUT' : 'POST';
      const body = isEditing 
        ? { ...data, feed_url: data.url } // Map UI to API
        : { ...data, feed_url: data.url, feed_type: 'rss', is_active: true, website_url: '' }; 

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session?.accessToken}`,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Erro ao salvar feed');
      }

      toast({
        title: "Sucesso",
        description: `Feed ${isEditing ? 'atualizado' : 'criado'} com sucesso.`,
      });
      onSuccess();
      onOpenChange(false);
      reset();
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Editar Feed' : 'Novo Feed RSS'}</DialogTitle>
          <DialogDescription>
            Configure a fonte de dados RSS/Atom.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nome do Feed</Label>
            <Input id="name" {...register('name')} placeholder="Ex: Science News" />
            {errors.name && <span className="text-sm text-red-500">{errors.name.message}</span>}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="url">URL do RSS</Label>
            <Input id="url" {...register('url')} placeholder="https://example.com/rss.xml" />
            {errors.url && <span className="text-sm text-red-500">{errors.url.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="journal">Nome do Periódico (Opcional)</Label>
            <Input id="journal" {...register('journal_name')} placeholder="Ex: Nature" />
          </div>

          <DialogFooter>
             <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
             <Button type="submit" disabled={loading} className="bg-bhub-teal-primary text-white">
               {loading ? 'Salvando...' : 'Salvar'}
             </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
