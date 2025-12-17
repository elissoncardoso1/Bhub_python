// Types matching the BHUB Python backend schemas

export interface Author {
  id: number;
  name: string;
  orcid?: string | null;
  affiliation?: string | null;
  avatar?: string;
  role?: 'author' | 'editor';
  article_count?: number;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  color: string;
  keywords?: string | null;
  article_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Article {
  id: number;
  title: string;
  abstract?: string | null;
  abstract_translated?: string | null;
  title_translated?: string | null;
  keywords?: string | null;
  original_url?: string | null;
  pdf_url?: string | null;
  image_url?: string | null;
  publication_date?: string | null;
  journal_name?: string | null;
  volume?: string | null;
  issue?: string | null;
  pages?: string | null;
  doi?: string | null;
  language: string;
  external_id?: string | null;
  category_id?: number | null;
  category?: Category | null;
  impact_score: number;
  classification_confidence?: number | null;
  highlighted: boolean;
  is_published: boolean;
  source_type: string;
  source_category?: 'journal' | 'portal';
  feed_id?: number | null;
  feed_name?: string | null;
  pdf_file_path?: string | null;
  pdf_file_size?: number | null;
  view_count: number;
  download_count: number;
  authors: Author[];
  has_pdf: boolean;
  created_at?: string;
  updated_at?: string;
}

// Paginated response from backend
export interface PaginatedArticleResponse {
  items: Article[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Category list response from backend
export interface CategoryListResponse {
  categories: Category[];
}

// Similar articles response
export interface ArticleSimilarResponse {
  articles: Article[];
}

// Frontend-specific props for components
export interface ArticleCardProps {
  id: number;
  title: string;
  excerpt: string;
  category: string;
  author: {
    name: string;
    avatar?: string;
  };
  authors?: Author[]; // Added authors support
  date: string;
  readingTime: number;
  source?: string;
  sourceId?: number;
  sourceCategory?: 'journal' | 'portal';
  imageUrl?: string | null;
  featured?: boolean;
  variant?: 'default' | 'compact';
}

export interface FeaturedArticleCardProps {
  id: number;
  title: string;
  excerpt: string;
  category: {
    label: string;
    icon?: React.ReactNode;
  };
  date: string;
  citations: number;
  author: {
    name: string;
    avatar: string;
    affiliation: string;
  };
  readingTime: number;
  onRead?: () => void;
  onLike?: () => void;
  isLiked?: boolean;
}

export interface ListParams {
  category_id?: number;
  author?: string;
  search?: string;
  page?: number;
  limit?: number;
  sort_by?: 'publication_date' | 'title' | 'impact_score' | 'view_count' | 'created_at';
  sort_order?: 'asc' | 'desc';
  highlighted?: boolean;
  has_pdf?: boolean;
  date_from?: string;
  date_to?: string;
  strategy?: 'default' | 'interleaved';
  source_category?: 'journal' | 'portal';
  feed_id?: number;
}

// Helper functions to transform backend data to frontend component props
export function articleToCardProps(article: Article): ArticleCardProps {
  return {
    id: article.id,
    title: article.title,
    excerpt: article.abstract?.substring(0, 200) || '',
    category: article.category?.name || 'Uncategorized',
    author: {
      name: article.authors[0]?.name || 'Unknown Author',
      avatar: undefined,
    },
    authors: article.authors, // Pass full authors list
    date: article.publication_date || article.created_at || '',
    readingTime: Math.ceil((article.abstract?.length || 0) / 1000) || 5,
    source: article.feed_name || article.journal_name || undefined,
    sourceId: article.feed_id || undefined,
    sourceCategory: article.source_category as 'journal' | 'portal' | undefined,
    imageUrl: article.image_url,
    featured: article.highlighted,
  };
}

export function articleToFeaturedProps(article: Article): Omit<FeaturedArticleCardProps, 'onRead' | 'onLike' | 'isLiked'> {
  return {
    id: article.id,
    title: article.title,
    excerpt: article.abstract?.substring(0, 300) || '',
    category: {
      label: article.category?.name || 'Uncategorized',
    },
    date: article.publication_date || article.created_at || '',
    citations: article.view_count,
    author: {
      name: article.authors[0]?.name || 'Unknown Author',
      avatar: '',
      affiliation: article.authors[0]?.affiliation || '',
    },
    readingTime: Math.ceil((article.abstract?.length || 0) / 1000) || 5,
  };
}