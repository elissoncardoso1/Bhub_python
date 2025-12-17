import { create } from 'zustand';
import { Article, PaginatedArticleResponse, ListParams } from '@/types/article';
import { ArticleService } from '@/services/articleService';

interface ArticleStore {
  articles: Article[];
  articlesJournal: Article[];
  articlesPortal: Article[];
  featured: Article[];
  favorites: Set<number>;
  loading: boolean;
  error: string | null;
  
  // Pagination
  totalArticles: number;
  currentPage: number;
  pageSize: number;
  totalPages: number;
  
  // Actions
  fetchArticles: (params?: ListParams) => Promise<void>;
  fetchJournalArticles: (limit?: number) => Promise<void>;
  fetchPortalArticles: (limit?: number) => Promise<void>;
  fetchFeatured: (limit?: number) => Promise<void>;
  fetchArticleById: (id: number | string) => Promise<Article | null>;
  toggleFavorite: (id: number) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPage: (page: number) => void;
}

export const useArticleStore = create<ArticleStore>((set, get) => ({
  articles: [],
  articlesJournal: [],
  articlesPortal: [],
  featured: [],
  favorites: new Set(),
  loading: false,
  error: null,
  
  // Pagination defaults
  totalArticles: 0,
  currentPage: 1,
  pageSize: 12,
  totalPages: 0,
  
  fetchArticles: async (params?: ListParams) => {
    set({ loading: true, error: null });
    
    try {
      const { currentPage, pageSize } = get();
      const response: PaginatedArticleResponse = await ArticleService.list({
        page: params?.page ?? currentPage,
        limit: params?.limit ?? pageSize,
        strategy: params?.strategy ?? 'interleaved',
        ...params,
      });
      
      set({ 
        articles: response.items, 
        totalArticles: response.total,
        currentPage: response.page,
        totalPages: response.total_pages,
        loading: false 
      });
    } catch (error) {
      console.error('Failed to fetch articles:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Falha ao carregar artigos', 
        loading: false 
      });
    }
  },

  fetchJournalArticles: async (limit: number = 6) => {
    try {
      const response = await ArticleService.list({
        limit,
        source_category: 'journal',
        sort_by: 'publication_date',
        sort_order: 'desc'
      });
      set({ articlesJournal: response.items });
    } catch (error) {
      console.error('Failed to fetch journal articles:', error);
    }
  },

  fetchPortalArticles: async (limit: number = 6) => {
    try {
      const response = await ArticleService.list({
        limit,
        source_category: 'portal',
        sort_by: 'publication_date',
        sort_order: 'desc'
      });
      set({ articlesPortal: response.items });
    } catch (error) {
      console.error('Failed to fetch portal articles:', error);
    }
  },
  
  fetchFeatured: async (limit: number = 5) => {
    set({ loading: true, error: null });
    
    try {
      const featured = await ArticleService.getFeatured(limit);
      set({ featured, loading: false });
    } catch (error) {
      console.error('Failed to fetch featured articles:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Falha ao carregar artigos em destaque', 
        loading: false 
      });
    }
  },
  
  fetchArticleById: async (id: number | string) => {
    set({ loading: true, error: null });
    
    try {
      const article = await ArticleService.getById(id);
      set({ loading: false });
      return article;
    } catch (error) {
      console.error('Failed to fetch article:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Falha ao carregar artigo', 
        loading: false 
      });
      return null;
    }
  },
  
  toggleFavorite: (id: number) => {
    set((state) => {
      const newFavorites = new Set(state.favorites);
      if (newFavorites.has(id)) {
        newFavorites.delete(id);
      } else {
        newFavorites.add(id);
      }
      return { favorites: newFavorites };
    });
  },
  
  setLoading: (loading: boolean) => set({ loading }),
  setError: (error: string | null) => set({ error }),
  setPage: (page: number) => set({ currentPage: page }),
}));