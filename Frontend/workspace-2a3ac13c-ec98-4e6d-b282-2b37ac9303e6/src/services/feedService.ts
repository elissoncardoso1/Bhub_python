import { ApiClient } from './api';

export interface Feed {
  id: number;
  name: string;
  description?: string;
  website_url?: string;
  feed_url?: string;
  is_active?: boolean;
}

export interface FeedListResponse {
  feeds: Feed[];
  total: number;
}

export const FeedService = {
  async getAll(): Promise<Feed[]> {
    try {
        const response = await ApiClient.get<FeedListResponse>('/feeds');
        return response.feeds;
    } catch (error) {
        console.error('Error fetching feeds:', error);
        return [];
    }
  },

  async getById(id: number): Promise<Feed | null> {
    try {
        return await ApiClient.get<Feed>(`/feeds/${id}`);
    } catch (error) {
        console.error(`Error fetching feed ${id}:`, error);
        return null;
    }
  }
};
