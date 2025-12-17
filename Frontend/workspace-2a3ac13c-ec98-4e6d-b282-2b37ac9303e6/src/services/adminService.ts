export interface AdminStats {
  total_articles: number;
  total_feeds: number;
  total_categories: number;
  total_authors: number;
  total_pdfs: number;
  articles_this_month: number;
  articles_this_week: number;
  highlighted_articles: number;
  views_total: number;
  downloads_total: number;
}

export interface DetailedStats {
  categories: Array<{ name: string; count: number }>;
  top_feeds: Array<{ name: string; count: number }>;
  top_authors: Array<{ name: string; count: number }>;
  unread_messages: number;
}

export interface FeedSyncResult {
  success: boolean;
  new_articles: number;
  updated_articles: number;
  errors: number;
  duration: number;
  message?: string;
}

export interface FeedSyncAllResult {
  success: boolean;
  total_feeds: number;
  successful: number;
  failed: number;
  total_new_articles: number;
  total_updated_articles: number;
  duration: number;
  results: Array<{
    feed_id: number;
    feed_name: string;
    success: boolean;
    new_articles: number;
    updated_articles: number;
    error?: string;
  }>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL 
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1` 
  : '/api/v1';

export const AdminService = {
  async getStats(token: string): Promise<AdminStats> {
    const response = await fetch(`${API_BASE_URL}/admin/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },

  async getDetailedStats(token: string): Promise<DetailedStats> {
    const response = await fetch(`${API_BASE_URL}/admin/stats/detailed`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch detailed stats');
    return response.json();
  },

  async syncFeed(feedId: number, token: string): Promise<FeedSyncResult> {
    const response = await fetch(`${API_BASE_URL}/admin/feeds/${feedId}/sync`, {
      method: 'POST',
      headers: { 
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('Failed to sync feed');
    return response.json();
  },

  async syncAllFeeds(token: string): Promise<FeedSyncAllResult> {
    const response = await fetch(`${API_BASE_URL}/admin/feeds/sync-all`, {
      method: 'POST',
      headers: { 
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('Failed to sync all feeds');
    return response.json();
  },

  async testFeed(feedUrl: string, token: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/admin/feeds/test`, {
      method: 'POST',
      headers: { 
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ feed_url: feedUrl }),
    });
    if (!response.ok) throw new Error('Failed to test feed');
    return response.json();
  },
};

