import { ApiClient } from './api';
import { Article, PaginatedArticleResponse } from '@/types/article';

export interface SearchParams {
  search?: string;
  category_id?: number[];
  author?: string; // Backend supports filtering by one author name currently
  feed_id?: number;
  source_category?: 'journal' | 'portal';
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export const SearchService = {
  async search(params: SearchParams): Promise<PaginatedArticleResponse> {
    const query = new URLSearchParams();
    
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());
    
    if (params.category_id && params.category_id.length > 0) {
      params.category_id.forEach(id => query.append('category_id', id.toString()));
    }
    
    if (params.author) query.append('author', params.author);
    if (params.feed_id) query.append('feed_id', params.feed_id.toString());
    if (params.source_category) query.append('source_category', params.source_category);
    if (params.date_from) query.append('date_from', params.date_from);
    if (params.date_to) query.append('date_to', params.date_to);

    const response = await ApiClient.get<PaginatedArticleResponse>(`/articles?${query.toString()}`);
    return response; // ApiClient.get returns Promise<T> (which is PaginatedResponse<Article>)
  }
};
