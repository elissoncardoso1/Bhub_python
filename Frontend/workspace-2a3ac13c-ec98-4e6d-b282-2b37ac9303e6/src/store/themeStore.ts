import { create } from 'zustand';

interface ThemeStore {
  isDark: boolean;
  toggle: () => void;
  setTheme: (isDark: boolean) => void;
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  isDark: false,
  
  toggle: () => {
    const newIsDark = !get().isDark;
    set({ isDark: newIsDark });
    
    // Update DOM and localStorage
    if (typeof window !== 'undefined') {
      document.documentElement.classList.toggle('dark', newIsDark);
      localStorage.setItem('bhub-theme', newIsDark ? 'dark' : 'light');
    }
  },
  
  setTheme: (isDark: boolean) => {
    set({ isDark });
    
    // Update DOM and localStorage
    if (typeof window !== 'undefined') {
      document.documentElement.classList.toggle('dark', isDark);
      localStorage.setItem('bhub-theme', isDark ? 'dark' : 'light');
    }
  }
}));