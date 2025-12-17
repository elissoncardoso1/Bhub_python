import { Author, Article, PaginatedArticleResponse } from '@/types/article';

const API_BASE = '/api/v1';

/**
 * Author service for working with article authors.
 * Note: The BHUB backend doesn't have dedicated author endpoints,
 * so we work with author data from article responses.
 */
export class AuthorService {
  /**
   * Get top authors with article counts
   */
  static async getTopAuthors(limit: number = 10): Promise<Author[]> {
    const response = await fetch(`${API_BASE}/authors?limit=${limit}`);
    if (!response.ok) {
      throw new Error('Failed to fetch authors');
    }
    return response.json();
  }

  /**
   * Get articles by a specific author name
   * Uses the articles endpoint with author filter
   */
  static async getArticlesByAuthor(
    authorName: string, 
    page: number = 1, 
    pageSize: number = 10
  ): Promise<PaginatedArticleResponse> {
    const response = await fetch(
      `${API_BASE}/articles?author=${encodeURIComponent(authorName)}&page=${page}&page_size=${pageSize}`
    );
    if (!response.ok) {
      throw new Error('Failed to fetch articles by author');
    }
    return response.json();
  }

  /**
   * Extract unique authors from a list of articles
   * Useful for building an author list from article data
   */
  static extractAuthorsFromArticles(articles: Article[]): Author[] {
    const authorMap = new Map<number, Author>();
    
    for (const article of articles) {
      for (const author of article.authors) {
        if (!authorMap.has(author.id)) {
          authorMap.set(author.id, author);
        }
      }
    }
    
    return Array.from(authorMap.values());
  }

  /**
   * Get author details from an article
   */
  static getPrimaryAuthor(article: Article): Author | null {
    return article.authors[0] || null;
  }
}