import { create } from 'zustand';

interface FilterStore {
  categories: string[];
  authors: string[];
  dateRange: string;
  searchTerm: string;
  sortBy: 'date' | 'citations' | 'title';
  sortOrder: 'asc' | 'desc';
  
  // Actions
  setCategories: (categories: string[]) => void;
  setAuthors: (authors: string[]) => void;
  setDateRange: (range: string) => void;
  setSearchTerm: (term: string) => void;
  setSortBy: (sort: 'date' | 'citations' | 'title') => void;
  setSortOrder: (order: 'asc' | 'desc') => void;
  clearFilters: () => void;
}

export const useFilterStore = create<FilterStore>((set) => ({
  categories: [],
  authors: [],
  dateRange: 'all',
  searchTerm: '',
  sortBy: 'date',
  sortOrder: 'desc',
  
  setCategories: (categories: string[]) => set({ categories }),
  setAuthors: (authors: string[]) => set({ authors }),
  setDateRange: (dateRange: string) => set({ dateRange }),
  setSearchTerm: (searchTerm: string) => set({ searchTerm }),
  setSortBy: (sortBy: 'date' | 'citations' | 'title') => set({ sortBy }),
  setSortOrder: (sortOrder: 'asc' | 'desc') => set({ sortOrder }),
  
  clearFilters: () => set({
    categories: [],
    authors: [],
    dateRange: 'all',
    searchTerm: '',
    sortBy: 'date',
    sortOrder: 'desc'
  })
}));