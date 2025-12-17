/**
 * Serviço para buscar metadados Open Graph do backend.
 */

export interface OpenGraphMetadata {
  'og:title'?: string;
  'og:description'?: string;
  'og:type'?: string;
  'og:url'?: string;
  'og:image'?: string;
  'og:image:width'?: string;
  'og:image:height'?: string;
  'og:image:type'?: string;
  'og:site_name'?: string;
  'article:published_time'?: string;
  'article:author'?: string;
  'article:section'?: string;
  'twitter:card'?: string;
  'twitter:title'?: string;
  'twitter:description'?: string;
  'twitter:image'?: string;
  title?: string;
  description?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class OpenGraphService {
  /**
   * Busca metadados Open Graph para um artigo.
   */
  static async getArticleMetadata(articleId: number): Promise<OpenGraphMetadata> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/og/articles/${articleId}/json`, {
        next: { revalidate: 3600 }, // Cache por 1 hora
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch OG metadata: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching Open Graph metadata:', error);
      // Retornar metadados padrão em caso de erro
      return this.getDefaultMetadata();
    }
  }

  /**
   * Retorna metadados padrão.
   */
  static getDefaultMetadata(): OpenGraphMetadata {
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://bhub.com.br';
    
    return {
      'og:title': 'BHub - Repositório de Análise do Comportamento',
      'og:description': 'Repositório científico dedicado à análise do comportamento',
      'og:type': 'website',
      'og:url': baseUrl,
      'og:image': `${baseUrl}/api/v1/og/default/image`,
      'og:site_name': 'BHub',
      'twitter:card': 'summary_large_image',
      'twitter:title': 'BHub - Repositório de Análise do Comportamento',
      'twitter:description': 'Repositório científico dedicado à análise do comportamento',
      'twitter:image': `${baseUrl}/api/v1/og/default/image`,
      title: 'BHub - Repositório de Análise do Comportamento',
      description: 'Repositório científico dedicado à análise do comportamento',
    };
  }

  /**
   * Converte metadados Open Graph para formato Next.js Metadata.
   */
  static toNextMetadata(ogMetadata: OpenGraphMetadata): {
    title: string;
    description: string;
    openGraph: {
      title: string;
      description: string;
      url: string;
      siteName: string;
      images: Array<{
        url: string;
        width: number;
        height: number;
        type?: string;
      }>;
      type: string;
      publishedTime?: string;
      authors?: string[];
      section?: string;
    };
    twitter: {
      card: 'summary_large_image' | 'summary';
      title: string;
      description: string;
      images: string[];
    };
  } {
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://bhub.com.br';
    
    return {
      title: ogMetadata.title || ogMetadata['og:title'] || 'BHub',
      description: ogMetadata.description || ogMetadata['og:description'] || '',
      openGraph: {
        title: ogMetadata['og:title'] || 'BHub',
        description: ogMetadata['og:description'] || '',
        url: ogMetadata['og:url'] || baseUrl,
        siteName: ogMetadata['og:site_name'] || 'BHub',
        images: [
          {
            url: ogMetadata['og:image'] || `${baseUrl}/api/v1/og/default/image`,
            width: parseInt(ogMetadata['og:image:width'] || '1200'),
            height: parseInt(ogMetadata['og:image:height'] || '630'),
            type: ogMetadata['og:image:type'] || 'image/png',
          },
        ],
        type: (ogMetadata['og:type'] as 'article' | 'website') || 'website',
        publishedTime: ogMetadata['article:published_time'],
        authors: ogMetadata['article:author'] ? [ogMetadata['article:author']] : undefined,
        section: ogMetadata['article:section'],
      },
      twitter: {
        card: (ogMetadata['twitter:card'] as 'summary_large_image' | 'summary') || 'summary_large_image',
        title: ogMetadata['twitter:title'] || ogMetadata['og:title'] || 'BHub',
        description: ogMetadata['twitter:description'] || ogMetadata['og:description'] || '',
        images: ogMetadata['twitter:image'] ? [ogMetadata['twitter:image']] : [],
      },
    };
  }
}

