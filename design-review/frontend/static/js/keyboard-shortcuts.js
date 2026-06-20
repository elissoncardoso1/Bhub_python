/**
 * BHUB - Keyboard Shortcuts
 * =========================
 * Atalhos de teclado para melhorar navegação
 * 
 * Atalhos disponíveis:
 *   /         - Focar campo de busca
 *   Esc       - Fechar modais/menus
 *   ?         - Mostrar ajuda de atalhos
 *   g + h     - Ir para Home
 *   g + a     - Ir para Artigos
 *   g + c     - Ir para Categorias
 *   j / k     - Navegar cards (próximo/anterior)
 */

(function() {
  'use strict';

  // Estado para sequências de teclas
  let keySequence = [];
  let keySequenceTimeout = null;

  // Verificar se usuário está em campo de texto
  function isTyping() {
    const activeElement = document.activeElement;
    const tagName = activeElement.tagName.toLowerCase();
    const isEditable = activeElement.isContentEditable;
    const isInput = ['input', 'textarea', 'select'].includes(tagName);
    
    return isEditable || isInput;
  }

  // Focar campo de busca
  function focusSearch() {
    const desktopSearch = document.getElementById('search-input');
    const mobileSearchBtn = document.getElementById('mobile-search-btn');
    
    // Em telas grandes, focar input diretamente
    if (desktopSearch && window.innerWidth >= 640) {
      desktopSearch.focus();
      desktopSearch.select();
      return true;
    }
    
    // Em mobile, abrir modal de busca
    if (mobileSearchBtn && window.innerWidth < 640) {
      mobileSearchBtn.click();
      return true;
    }
    
    return false;
  }

  // Fechar elementos abertos
  function closeOpenElements() {
    // Fechar modal
    const modal = document.getElementById('modal-container');
    if (modal && modal.innerHTML.trim() !== '') {
      if (typeof window.closeModal === 'function') {
        window.closeModal();
      } else {
        modal.innerHTML = '';
      }
      return true;
    }
    
    // Fechar menu mobile
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
      if (typeof window.closeMobileMenu === 'function') {
        window.closeMobileMenu();
      }
      return true;
    }
    
    // Fechar busca mobile
    const mobileSearch = document.getElementById('mobile-search-modal');
    if (mobileSearch && !mobileSearch.classList.contains('hidden')) {
      if (typeof window.closeMobileSearch === 'function') {
        window.closeMobileSearch();
      }
      return true;
    }
    
    // Fechar menu de usuário
    const userMenu = document.getElementById('user-menu');
    if (userMenu && !userMenu.classList.contains('hidden')) {
      userMenu.classList.add('hidden');
      const button = document.getElementById('user-menu-button');
      if (button) {
        button.setAttribute('aria-expanded', 'false');
      }
      return true;
    }
    
    // Fechar resultados de busca
    const searchResults = document.getElementById('search-results');
    if (searchResults && searchResults.innerHTML.trim() !== '') {
      searchResults.innerHTML = '';
      const searchInput = document.getElementById('search-input');
      if (searchInput) {
        searchInput.setAttribute('aria-expanded', 'false');
      }
      return true;
    }
    
    return false;
  }

  // Navegar para URL
  function navigateTo(url) {
    window.location.href = url;
  }

  // Mostrar modal de atalhos
  function showShortcutsHelp() {
    const modalContainer = document.getElementById('modal-container');
    if (!modalContainer) return;
    
    modalContainer.innerHTML = `
      <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" onclick="closeModal()"></div>
      <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div role="dialog" aria-modal="true" aria-labelledby="shortcuts-title" class="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[80vh] overflow-y-auto modal-content-enter">
          <div class="p-6">
            <div class="flex items-center justify-between mb-4">
              <h2 id="shortcuts-title" class="text-xl font-bold text-slate-900">Atalhos de Teclado</h2>
              <button 
                type="button"
                onclick="closeModal()"
                aria-label="Fechar"
                class="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
            
            <div class="space-y-4">
              <div>
                <h3 class="text-sm font-semibold text-slate-500 uppercase mb-2">Geral</h3>
                <ul class="space-y-2">
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Focar busca</span>
                    <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">/</kbd>
                  </li>
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Fechar modais</span>
                    <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">Esc</kbd>
                  </li>
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Mostrar atalhos</span>
                    <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">?</kbd>
                  </li>
                </ul>
              </div>
              
              <div class="border-t border-slate-100 pt-4">
                <h3 class="text-sm font-semibold text-slate-500 uppercase mb-2">Navegação</h3>
                <ul class="space-y-2">
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Ir para Início</span>
                    <div class="flex gap-1">
                      <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">g</kbd>
                      <span class="text-slate-400">+</span>
                      <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">h</kbd>
                    </div>
                  </li>
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Ir para Artigos</span>
                    <div class="flex gap-1">
                      <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">g</kbd>
                      <span class="text-slate-400">+</span>
                      <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">a</kbd>
                    </div>
                  </li>
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Ir para Categorias</span>
                    <div class="flex gap-1">
                      <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">g</kbd>
                      <span class="text-slate-400">+</span>
                      <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">c</kbd>
                    </div>
                  </li>
                </ul>
              </div>
              
              <div class="border-t border-slate-100 pt-4">
                <h3 class="text-sm font-semibold text-slate-500 uppercase mb-2">Cards</h3>
                <ul class="space-y-2">
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Próximo card</span>
                    <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">j</kbd>
                  </li>
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Card anterior</span>
                    <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">k</kbd>
                  </li>
                  <li class="flex items-center justify-between">
                    <span class="text-slate-700">Abrir card</span>
                    <kbd class="px-2 py-1 bg-slate-100 rounded text-sm font-mono text-slate-600">Enter</kbd>
                  </li>
                </ul>
              </div>
            </div>
            
            <div class="mt-6 pt-4 border-t border-slate-100">
              <p class="text-xs text-slate-400 text-center">
                Pressione <kbd class="px-1.5 py-0.5 bg-slate-100 rounded text-xs font-mono">?</kbd> para ver esta ajuda
              </p>
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Focar no botão de fechar
    const closeButton = modalContainer.querySelector('button[aria-label="Fechar"]');
    if (closeButton) {
      closeButton.focus();
    }
  }

  // Navegar entre cards
  let currentCardIndex = -1;
  
  function navigateCards(direction) {
    const cards = document.querySelectorAll('article[itemtype*="Article"]');
    if (cards.length === 0) return;
    
    // Calcular novo índice
    if (direction === 'next') {
      currentCardIndex = Math.min(currentCardIndex + 1, cards.length - 1);
    } else {
      currentCardIndex = Math.max(currentCardIndex - 1, 0);
    }
    
    // Focar no card
    const card = cards[currentCardIndex];
    if (card) {
      // Remover destaque anterior (usar .is-active em vez de classes Tailwind)
      cards.forEach(c => c.classList.remove('is-active'));
      
      // Adicionar destaque usando classe estável .is-active
      card.classList.add('is-active');
      
      // Scroll para o card
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Focar no link do título
      const link = card.querySelector('h3 a');
      if (link) {
        link.focus();
      }
    }
  }

  // Handler principal de teclas
  function handleKeydown(event) {
    // Ignorar se estiver digitando
    if (isTyping()) {
      // Exceção: Esc sempre funciona
      if (event.key === 'Escape') {
        const closed = closeOpenElements();
        if (closed) {
          event.preventDefault();
        }
      }
      return;
    }
    
    // Ignorar se tiver modificadores (exceto Shift para ?)
    if (event.ctrlKey || event.altKey || event.metaKey) {
      return;
    }
    
    const key = event.key.toLowerCase();
    
    // Teclas de ação direta
    switch (event.key) {
      case '/':
        event.preventDefault();
        focusSearch();
        return;
        
      case 'Escape':
        closeOpenElements();
        return;
        
      case '?':
        event.preventDefault();
        showShortcutsHelp();
        return;
        
      case 'j':
        event.preventDefault();
        navigateCards('next');
        return;
        
      case 'k':
        event.preventDefault();
        navigateCards('prev');
        return;
    }
    
    // Sequências de teclas (g + ...)
    clearTimeout(keySequenceTimeout);
    keySequence.push(key);
    
    // Limpar sequência após 1 segundo
    keySequenceTimeout = setTimeout(() => {
      keySequence = [];
    }, 1000);
    
    // Verificar sequências
    const sequence = keySequence.join('');
    
    switch (sequence) {
      case 'gh':
        event.preventDefault();
        navigateTo('/');
        keySequence = [];
        return;
        
      case 'ga':
        event.preventDefault();
        navigateTo('/articles');
        keySequence = [];
        return;
        
      case 'gc':
        event.preventDefault();
        navigateTo('/categories');
        keySequence = [];
        return;
    }
    
    // Limitar tamanho da sequência
    if (keySequence.length > 2) {
      keySequence = [key];
    }
  }

  // Inicializar
  document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('keydown', handleKeydown);
    
    // Resetar índice de cards quando conteúdo mudar
    document.body.addEventListener('htmx:afterSwap', function() {
      currentCardIndex = -1;
      // Remover destaque de todos os cards (usar .is-active)
      document.querySelectorAll('article[itemtype*="Article"]').forEach(card => {
        card.classList.remove('is-active');
      });
    });
    
    console.log('⌨️ Keyboard shortcuts loaded. Press ? for help.');
  });
})();

