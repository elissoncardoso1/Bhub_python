import { Article, ListParams, PaginatedArticleResponse } from '@/types/article';

const API_BASE = '/api/v1';

export class ArticleService {
  /**
   * Get highlighted/featured articles
   */
  static async getFeatured(limit: number = 10): Promise<Article[]> {
    const response = await fetch(`${API_BASE}/articles/highlighted?limit=${limit}`);
    if (!response.ok) {
      throw new Error('Failed to fetch featured articles');
    }
    return response.json();
  }

  /**
   * Get trending articles (most viewed)
   */
  static async getTrending(limit: number = 5): Promise<Article[]> {
    const response = await this.list({
      limit,
      sort_by: 'view_count',
      sort_order: 'desc'
    });
    return response.items;
  }

  /**
   * List articles with pagination and filters
   */
  static async list(params?: ListParams): Promise<PaginatedArticleResponse> {
    const query = new URLSearchParams();
    
    if (params?.category_id) query.append('category_id', params.category_id.toString());
    if (params?.author) query.append('author', params.author);
    if (params?.search) query.append('search', params.search);
    if (params?.page) query.append('page', params.page.toString());
    if (params?.limit) query.append('page_size', params.limit.toString());
    if (params?.sort_by) query.append('sort_by', params.sort_by);
    if (params?.sort_order) query.append('sort_order', params.sort_order);
    if (params?.highlighted !== undefined) query.append('highlighted', params.highlighted.toString());
    if (params?.has_pdf !== undefined) query.append('has_pdf', params.has_pdf.toString());
    if (params?.date_from) query.append('date_from', params.date_from);
    if (params?.date_to) query.append('date_to', params.date_to);
    if (params?.strategy) query.append('strategy', params.strategy);
    if (params?.source_category) query.append('source_category', params.source_category);
    if (params?.feed_id !== undefined && params.feed_id !== null) {
      query.append('feed_id', params.feed_id.toString());
    }

    const url = `${API_BASE}/articles${query.toString() ? `?${query.toString()}` : ''}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Failed to fetch articles');
    }
    
    return response.json();
  }

  /**
   * Get a single article by ID
   */
  static async getById(id: number | string): Promise<Article> {
    const response = await fetch(`${API_BASE}/articles/${id}`);
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Article not found');
      }
      throw new Error('Failed to fetch article');
    }
    return response.json();
  }

  /**
   * Get similar articles for a given article
   */
  static async getSimilar(id: number | string, limit: number = 5): Promise<Article[]> {
    const response = await fetch(`${API_BASE}/articles/${id}/similar?limit=${limit}`);
    if (!response.ok) {
      throw new Error('Failed to fetch similar articles');
    }
    const data = await response.json();
    return data.articles;
  }

  /**
   * Search articles with query string
   */
  static async search(query: string, filters?: Partial<ListParams>): Promise<PaginatedArticleResponse> {
    return this.list({
      search: query,
      ...filters,
    });
  }

  /**
   * Download PDF for an article
   */
  static getDownloadUrl(id: number | string): string {
    return `${API_BASE}/articles/${id}/download`;
  }
}