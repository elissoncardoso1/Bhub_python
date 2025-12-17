import { ApiClient } from './api';

export interface ArticleAdminFilters {
  category_id?: number;
  feed_id?: number;
  is_published?: boolean;
  page?: number;
  page_size?: number;
}

export interface ArticleCreateData {
  title: string;
  abstract?: string;
  keywords?: string[];
  original_url?: string;
  pdf_url?: string;
  image_url?: string;
  publication_date?: string;
  journal_name?: string;
  volume?: string;
  issue?: string;
  pages?: string;
  doi?: string;
  language?: string;
  category_id?: number;
  feed_id?: number;
  authors?: string[];
}

export interface ArticleUpdateData extends Partial<ArticleCreateData> {
  highlighted?: boolean;
  is_published?: boolean;
}

export interface PDFUploadResponse {
  success: boolean;
  article_id?: number;
  message: string;
  duplicate?: boolean;
}

export interface ScrapeResponse {
  success: boolean;
  article?: any;
  error?: string;
}

export const ArticleAdminService = {
  async list(filters: ArticleAdminFilters = {}) {
    const params = new URLSearchParams();
    
    if (filters.category_id) params.append('category_id', filters.category_id.toString());
    if (filters.feed_id) params.append('feed_id', filters.feed_id.toString());
    if (filters.is_published !== undefined) params.append('is_published', filters.is_published.toString());
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());

    const query = params.toString();
    const url = `/admin/articles${query ? `?${query}` : ''}`;
    
    return ApiClient.get<any>(url);
  },

  async create(data: ArticleCreateData) {
    return ApiClient.post<any>('/admin/articles', data);
  },

  async update(id: number, data: ArticleUpdateData) {
    return ApiClient.put<any>(`/admin/articles/${id}`, data);
  },

  async delete(id: number) {
    return ApiClient.delete<any>(`/admin/articles/${id}`);
  },

  async toggleHighlight(id: number, highlighted: boolean) {
    return ApiClient.patch<any>(`/admin/articles/${id}/highlight`, { highlighted });
  },

  async uploadPDF(file: File, categoryId?: number) {
    const formData = new FormData();
    formData.append('file', file);
    if (categoryId) {
      formData.append('category_id', categoryId.toString());
    }

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/admin/articles/upload-pdf`, {
      method: 'POST',
      body: formData,
      // Note: Don't set Content-Type for FormData, browser will set it with boundary
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Upload failed' }));
      throw new Error(error.message || 'Upload failed');
    }

    return response.json() as Promise<PDFUploadResponse>;
  },

  async scrapeURL(url: string, categoryId?: number) {
    return ApiClient.post<ScrapeResponse>('/admin/articles/scrape', {
      url,
      category_id: categoryId,
    });
  },
};
