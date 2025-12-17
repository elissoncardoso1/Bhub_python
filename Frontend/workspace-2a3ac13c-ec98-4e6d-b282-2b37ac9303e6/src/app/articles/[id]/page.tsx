import type { Metadata } from 'next';
import { ArticleDetailPage } from '@/pages/ArticleDetailPage';
import { OpenGraphService } from '@/services/opengraphService';

interface ArticlePageProps {
  params: Promise<{ id: string }>;
}

/**
 * Gera metadados Open Graph dinâmicos para a página do artigo.
 * Isso permite que crawlers (Facebook, Twitter, LinkedIn, WhatsApp) 
 * vejam as informações corretas ao compartilhar links.
 */
export async function generateMetadata({ params }: ArticlePageProps): Promise<Metadata> {
  const { id } = await params;
  const articleId = parseInt(id);

  if (isNaN(articleId)) {
    // Retornar metadados padrão se ID inválido
    const defaultMetadata = OpenGraphService.getDefaultMetadata();
    return OpenGraphService.toNextMetadata(defaultMetadata);
  }

  try {
    // Buscar metadados do backend
    const ogMetadata = await OpenGraphService.getArticleMetadata(articleId);
    return OpenGraphService.toNextMetadata(ogMetadata);
  } catch (error) {
    console.error('Error generating metadata:', error);
    // Fallback para metadados padrão
    const defaultMetadata = OpenGraphService.getDefaultMetadata();
    return OpenGraphService.toNextMetadata(defaultMetadata);
  }
}

/**
 * Página de detalhes do artigo com SSR para Open Graph.
 * 
 * A página ainda usa client-side rendering para interatividade,
 * mas os metadados são gerados no servidor para SEO e compartilhamento.
 */
export default async function ArticleDetail({ params }: ArticlePageProps) {
  const { id } = await params;
  
  return <ArticleDetailPage articleId={id} />;
}
