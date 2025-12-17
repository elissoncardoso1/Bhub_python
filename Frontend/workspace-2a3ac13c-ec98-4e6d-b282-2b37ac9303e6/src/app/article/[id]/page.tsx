import type { Metadata } from 'next';
import { ArticleDetailPage } from '@/pages/ArticleDetailPage';
import { OpenGraphService } from '@/services/opengraphService';

interface ArticlePageProps {
  params: Promise<{ id: string }>;
}

/**
 * Gera metadados Open Graph dinâmicos para a página do artigo.
 */
export async function generateMetadata({ params }: ArticlePageProps): Promise<Metadata> {
  const { id } = await params;
  const articleId = parseInt(id);

  if (isNaN(articleId)) {
    const defaultMetadata = OpenGraphService.getDefaultMetadata();
    return OpenGraphService.toNextMetadata(defaultMetadata);
  }

  try {
    const ogMetadata = await OpenGraphService.getArticleMetadata(articleId);
    return OpenGraphService.toNextMetadata(ogMetadata);
  } catch (error) {
    console.error('Error generating metadata:', error);
    const defaultMetadata = OpenGraphService.getDefaultMetadata();
    return OpenGraphService.toNextMetadata(defaultMetadata);
  }
}

export default async function ArticleDetail({ params }: ArticlePageProps) {
  const { id } = await params;
  
  return <ArticleDetailPage articleId={id} />;
}