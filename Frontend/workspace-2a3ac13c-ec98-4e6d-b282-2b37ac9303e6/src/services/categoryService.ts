import { Category, CategoryListResponse, Article, PaginatedArticleResponse } from '@/types/article';

const API_BASE = '/api/v1';

export class CategoryService {
  /**
   * Get all categories
   */
  static async getAll(): Promise<Category[]> {
    const response = await fetch(`${API_BASE}/categories`);
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }
    const data: CategoryListResponse = await response.json();
    return data.categories;
  }

  /**
   * Get a single category by ID
   */
  static async getById(id: number | string): Promise<Category> {
    const response = await fetch(`${API_BASE}/categories/${id}`);
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Category not found');
      }
      throw new Error('Failed to fetch category');
    }
    return response.json();
  }

  /**
   * Get category by slug
   */
  static async getBySlug(slug: string): Promise<Category> {
    const response = await fetch(`${API_BASE}/categories/slug/${slug}`);
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Category not found');
      }
      throw new Error('Failed to fetch category');
    }
    return response.json();
  }

  /**
   * Get articles by category ID
   * Uses the articles endpoint with category filter
   */
  static async getArticlesByCategory(categoryId: number | string, page: number = 1, pageSize: number = 10): Promise<PaginatedArticleResponse> {
    const response = await fetch(`${API_BASE}/articles?category_id=${categoryId}&page=${page}&page_size=${pageSize}`);
    if (!response.ok) {
      throw new Error('Failed to fetch articles by category');
    }
    return response.json();
  }
}