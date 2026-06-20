(function () {
  function metaContent(name) {
    const el = document.querySelector(`meta[name="${name}"]`);
    return el ? el.getAttribute("content") : null;
  }

  function toast(message, kind) {
    const host = document.getElementById("toast");
    if (!host) return;

    const item = document.createElement("div");
    item.className = `toast-item ${kind || ""}`.trim();
    item.textContent = message;

    host.appendChild(item);
    window.setTimeout(() => item.remove(), 4500);
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!window.htmx) return;

    // Garantir que htmx.config.headers existe
    if (!window.htmx.config) {
      window.htmx.config = {};
    }
    if (!window.htmx.config.headers) {
      window.htmx.config.headers = {};
    }

    const csrfToken = metaContent("csrf-token");
    if (csrfToken) {
      window.htmx.config.headers["X-CSRF-Token"] = csrfToken;
    }

    const existingSessionId = window.localStorage.getItem("bhub_session_id");
    if (existingSessionId) {
      window.htmx.config.headers["X-Session-ID"] = existingSessionId;
    }

    document.body.addEventListener("htmx:afterRequest", (evt) => {
      const xhr = evt.detail.xhr;
      if (!xhr) return;

      const sessionId = xhr.getResponseHeader("X-Session-ID");
      if (sessionId) {
        window.localStorage.setItem("bhub_session_id", sessionId);
        window.htmx.config.headers["X-Session-ID"] = sessionId;
      }
    });

    // Função para exibir toast de erro
    function showErrorToast(message, title = "Erro") {
      const container = document.getElementById("toast-container");
      if (!container) return;

      const toast = document.createElement("div");
      toast.setAttribute("role", "alert");
      toast.setAttribute("aria-live", "assertive");
      toast.className = "max-w-sm animate-in slide-in-from-top-5 duration-300";
      toast.innerHTML = `
        <div class="bg-error-50 border-l-4 border-error-500 p-4 rounded-lg shadow-lg">
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <svg class="w-5 h-5 text-error-600" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3 flex-1">
              <h3 class="text-sm font-medium text-error-800">${title}</h3>
              <p class="mt-1 text-sm text-error-700">${message}</p>
            </div>
            <button 
              type="button"
              aria-label="Fechar notificação"
              class="ml-4 flex-shrink-0 text-error-600 hover:text-error-800 focus:outline-none focus:ring-2 focus:ring-error-500 rounded transition-colors"
              onclick="this.closest('[role=alert]').remove()"
            >
              <span class="sr-only">Fechar</span>
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      `;
      container.appendChild(toast);

      // Remover automaticamente após 5 segundos
      setTimeout(() => {
        toast.remove();
      }, 5000);
    }

    // Função para exibir toast de sucesso
    function showSuccessToast(message, title = "Sucesso") {
      const container = document.getElementById("toast-container");
      if (!container) return;

      const toast = document.createElement("div");
      toast.setAttribute("role", "alert");
      toast.setAttribute("aria-live", "polite");
      toast.className = "max-w-sm animate-in slide-in-from-top-5 duration-300";
      toast.innerHTML = `
        <div class="bg-success-50 border-l-4 border-success-500 p-4 rounded-lg shadow-lg">
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <svg class="w-5 h-5 text-success-600" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3 flex-1">
              <h3 class="text-sm font-medium text-success-800">${title}</h3>
              <p class="mt-1 text-sm text-success-700">${message}</p>
            </div>
            <button 
              type="button"
              aria-label="Fechar notificação"
              class="ml-4 flex-shrink-0 text-success-600 hover:text-success-800 focus:outline-none focus:ring-2 focus:ring-success-500 rounded transition-colors"
              onclick="this.closest('[role=alert]').remove()"
            >
              <span class="sr-only">Fechar</span>
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      `;
      container.appendChild(toast);

      // Remover automaticamente após 5 segundos
      setTimeout(() => {
        toast.remove();
      }, 5000);
    }

    // Expor funções globalmente
    window.showErrorToast = showErrorToast;
    window.showSuccessToast = showSuccessToast;

    document.body.addEventListener("htmx:responseError", (evt) => {
      const xhr = evt.detail.xhr;
      const status = xhr ? xhr.status : 0;
      let message = `Erro ao processar requisição (HTTP ${status}).`;
      
      if (status === 404) {
        message = "Recurso não encontrado.";
      } else if (status === 403) {
        message = "Você não tem permissão para realizar esta ação.";
      } else if (status === 500) {
        message = "Erro interno do servidor. Tente novamente mais tarde.";
      }
      
      showErrorToast(message, "Erro");
    });

    document.body.addEventListener("htmx:sendError", () => {
      showErrorToast("Erro de rede ao processar requisição. Verifique sua conexão.", "Erro de Rede");
    });

    document.body.addEventListener("bhub:toast", (evt) => {
      const detail = evt.detail || {};
      toast(detail.message || "OK", detail.kind || "ok");
    });

    // Fechar modal com ESC
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        const modal = document.getElementById("modal-container");
        if (modal && modal.innerHTML.trim() !== "") {
          modal.innerHTML = "";
          // Retornar foco para elemento que abriu o modal
          document.activeElement?.blur();
        }
      }
    });

    // Função global para fechar modal
    window.closeModal = function () {
      const modal = document.getElementById("modal-container");
      if (modal && modal.innerHTML.trim() !== "") {
        // Usar animação de saída do anime.js se disponível
        if (window.bhubAnimations && window.bhubAnimations.animateModalOut) {
          window.bhubAnimations.animateModalOut(modal, function() {
            modal.innerHTML = "";
            document.activeElement?.blur();
            // Retornar foco para elemento que abriu o modal
            const previousActive = document.querySelector("[data-modal-trigger]");
            if (previousActive) {
              previousActive.focus();
              previousActive.removeAttribute("data-modal-trigger");
            }
          });
        } else {
          // Fallback se anime.js não estiver disponível
          modal.innerHTML = "";
          document.activeElement?.blur();
          const previousActive = document.querySelector("[data-modal-trigger]");
          if (previousActive) {
            previousActive.focus();
            previousActive.removeAttribute("data-modal-trigger");
          }
        }
      }
    };

    // Toggle user menu
    window.toggleUserMenu = function () {
      const menu = document.getElementById("user-menu");
      const button = document.getElementById("user-menu-button");
      if (menu && button) {
        const isExpanded = button.getAttribute("aria-expanded") === "true";
        button.setAttribute("aria-expanded", !isExpanded);
        menu.classList.toggle("hidden");
      }
    };

    // Fechar user menu ao clicar fora
    document.addEventListener("click", (e) => {
      const menu = document.getElementById("user-menu");
      const button = document.getElementById("user-menu-button");
      if (menu && button && !button.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add("hidden");
        button.setAttribute("aria-expanded", "false");
      }
    });

    // ==========================================
    // Mobile Menu Functions
    // ==========================================
    
    window.toggleMobileMenu = function () {
      const menu = document.getElementById("mobile-menu");
      const btn = document.getElementById("mobile-menu-btn");
      const isOpen = !menu.classList.contains("hidden");
      
      if (isOpen) {
        closeMobileMenu();
      } else {
        openMobileMenu();
      }
    };

    window.openMobileMenu = function () {
      const menu = document.getElementById("mobile-menu");
      const overlay = document.getElementById("mobile-menu-overlay");
      const drawer = document.getElementById("mobile-menu-drawer");
      const btn = document.getElementById("mobile-menu-btn");
      const iconOpen = document.getElementById("mobile-menu-icon-open");
      const iconClose = document.getElementById("mobile-menu-icon-close");
      
      if (!menu) return;
      
      // Show menu container
      menu.classList.remove("hidden");
      btn?.setAttribute("aria-expanded", "true");
      
      // Toggle icons
      iconOpen?.classList.add("hidden");
      iconClose?.classList.remove("hidden");
      
      // Animate in (requestAnimationFrame para garantir transição)
      requestAnimationFrame(() => {
        overlay?.classList.remove("opacity-0");
        overlay?.classList.add("opacity-100");
        drawer?.classList.remove("translate-x-full");
        drawer?.classList.add("translate-x-0");
      });
      
      // Prevent body scroll
      document.body.style.overflow = "hidden";
      
      // Focus first link
      setTimeout(() => {
        const firstLink = drawer?.querySelector('a');
        firstLink?.focus();
      }, 300);
    };

    window.closeMobileMenu = function () {
      const menu = document.getElementById("mobile-menu");
      const overlay = document.getElementById("mobile-menu-overlay");
      const drawer = document.getElementById("mobile-menu-drawer");
      const btn = document.getElementById("mobile-menu-btn");
      const iconOpen = document.getElementById("mobile-menu-icon-open");
      const iconClose = document.getElementById("mobile-menu-icon-close");
      
      if (!menu) return;
      
      // Animate out
      overlay?.classList.remove("opacity-100");
      overlay?.classList.add("opacity-0");
      drawer?.classList.remove("translate-x-0");
      drawer?.classList.add("translate-x-full");
      
      // Toggle icons
      iconOpen?.classList.remove("hidden");
      iconClose?.classList.add("hidden");
      
      btn?.setAttribute("aria-expanded", "false");
      
      // Hide menu after animation
      setTimeout(() => {
        menu.classList.add("hidden");
        document.body.style.overflow = "";
      }, 300);
      
      // Return focus to menu button
      btn?.focus();
    };

    // ==========================================
    // Mobile Search Functions
    // ==========================================
    
    window.openMobileSearch = function () {
      const modal = document.getElementById("mobile-search-modal");
      const input = document.getElementById("mobile-search-input");
      const btn = document.getElementById("mobile-search-btn");
      
      if (!modal) return;
      
      modal.classList.remove("hidden");
      btn?.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
      
      // Focus input after animation
      setTimeout(() => {
        input?.focus();
      }, 100);
    };

    window.closeMobileSearch = function () {
      const modal = document.getElementById("mobile-search-modal");
      const results = document.getElementById("mobile-search-results");
      const btn = document.getElementById("mobile-search-btn");
      
      if (!modal) return;
      
      modal.classList.add("hidden");
      btn?.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      
      // Clear results
      if (results) {
        results.innerHTML = "";
      }
      
      // Return focus
      btn?.focus();
    };

    // Fechar menus com ESC
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        // Fechar mobile menu se aberto
        const mobileMenu = document.getElementById("mobile-menu");
        if (mobileMenu && !mobileMenu.classList.contains("hidden")) {
          closeMobileMenu();
          return;
        }
        
        // Fechar mobile search se aberto
        const mobileSearch = document.getElementById("mobile-search-modal");
        if (mobileSearch && !mobileSearch.classList.contains("hidden")) {
          closeMobileSearch();
          return;
        }
        
        // Fechar user menu se aberto
        const userMenu = document.getElementById("user-menu");
        if (userMenu && !userMenu.classList.contains("hidden")) {
          userMenu.classList.add("hidden");
          document.getElementById("user-menu-button")?.setAttribute("aria-expanded", "false");
        }
      }
    });

    // Fechar menus ao redimensionar para desktop
    window.addEventListener("resize", () => {
      if (window.innerWidth >= 1024) {
        const mobileMenu = document.getElementById("mobile-menu");
        if (mobileMenu && !mobileMenu.classList.contains("hidden")) {
          closeMobileMenu();
        }
      }
    });

    // ==========================================
    // Mobile Filters Toggle (Home Page)
    // ==========================================
    
    window.toggleMobileFilters = function () {
      const filters = document.getElementById("mobile-filters");
      const button = document.getElementById("mobile-filter-toggle");
      const icon = document.getElementById("filter-toggle-icon");
      
      if (!filters || !button) return;
      
      const isExpanded = button.getAttribute("aria-expanded") === "true";
      
      button.setAttribute("aria-expanded", !isExpanded);
      filters.classList.toggle("hidden");
      
      // Rotate icon
      if (icon) {
        icon.classList.toggle("rotate-180");
      }
    };

    // Focus trap para modais
    function trapFocus(container) {
      const focusableElements = container.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      container.addEventListener("keydown", function (e) {
        if (e.key !== "Tab") return;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      });
    }

    // Aplicar focus trap quando modal é aberto
    document.body.addEventListener("htmx:afterSwap", (e) => {
      if (e.target.id === "modal-container") {
        const modalContent = e.target.querySelector('[role="dialog"]');
        if (modalContent) {
          // Focar no primeiro elemento focável
          const firstFocusable = modalContent.querySelector(
            'button, a, input, textarea, select, [tabindex]:not([tabindex="-1"])'
          );
          firstFocusable?.focus();
          // Aplicar focus trap
          trapFocus(modalContent);
        }
      }
    });

    // Melhorar navegação por teclado nos resultados de busca
    document.body.addEventListener("htmx:afterSwap", (e) => {
      if (e.target.id === "search-results") {
        const results = e.target.querySelectorAll('[role="option"]');
        const searchInput = document.getElementById("search-input");
        if (results.length > 0 && searchInput) {
          searchInput.setAttribute("aria-expanded", "true");
          // Adicionar navegação por teclado
          results.forEach((result, index) => {
            result.setAttribute("tabindex", index === 0 ? "0" : "-1");
            result.addEventListener("keydown", (evt) => {
              if (evt.key === "ArrowDown") {
                evt.preventDefault();
                const next = results[index + 1];
                if (next) {
                  result.setAttribute("tabindex", "-1");
                  next.setAttribute("tabindex", "0");
                  next.focus();
                }
              } else if (evt.key === "ArrowUp") {
                evt.preventDefault();
                const prev = results[index - 1];
                if (prev) {
                  result.setAttribute("tabindex", "-1");
                  prev.setAttribute("tabindex", "0");
                  prev.focus();
                } else {
                  searchInput.focus();
                }
              } else if (evt.key === "Escape") {
                searchInput.focus();
                e.target.innerHTML = "";
                searchInput.setAttribute("aria-expanded", "false");
              }
            });
          });
        }
      }
    });

    // ==========================================
    // Keyboard Navigation Support
    // ==========================================
    
    // Função global para navegação por teclado
    window.handleKeyDown = function(event, callback) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        callback();
      }
    };
    
    // ==========================================
    // Save Article Functionality
    // ==========================================
    
    window.toggleSaveArticle = function(articleId) {
      // TODO: Implementar lógica de salvar/remover artigo
      // Por enquanto, apenas mostra feedback
      const button = document.querySelector(`[onclick*="toggleSaveArticle(${articleId})"]`);
      if (!button) return;
      
      const isSaved = button.getAttribute("aria-pressed") === "true";
      button.setAttribute("aria-pressed", !isSaved);
      
      if (window.showSuccessToast) {
        window.showSuccessToast(
          isSaved ? "Artigo removido da lista de leitura" : "Artigo salvo para leitura posterior"
        );
      }
    };
    
    // ==========================================
    // Share Article Functionality
    // ==========================================
    
    window.shareArticle = function(articleId) {
      const button = document.querySelector(`[data-article-id="${articleId}"].share-article-btn`);
      if (!button) return;
      handleShareArticle(button);
    };
    
    function handleShareArticle(button) {
      const articleId = button.getAttribute("data-article-id");
      const articleTitle = button.getAttribute("data-article-title") || "Artigo";
      const url = window.location.origin + "/articles/" + articleId;
      
      if (navigator.share) {
        navigator.share({
          title: articleTitle,
          url: url
        }).catch((err) => {
          console.log("Erro ao compartilhar:", err);
        });
      } else {
        navigator.clipboard.writeText(url).then(() => {
          if (window.showSuccessToast) {
            window.showSuccessToast("Link copiado para a área de transferência!");
          } else {
            alert("Link copiado!");
          }
        }).catch((err) => {
          console.error("Erro ao copiar:", err);
          if (window.showErrorToast) {
            window.showErrorToast("Erro ao copiar link");
          } else {
            alert("Erro ao copiar link");
          }
        });
      }
    }
    
    // Adicionar event listeners para botões de compartilhar
    document.addEventListener("click", (e) => {
      if (e.target.closest(".share-article-btn")) {
        e.preventDefault();
        handleShareArticle(e.target.closest(".share-article-btn"));
      }
    });
    
    // Aplicar após HTMX swaps
    document.body.addEventListener("htmx:afterSwap", () => {
      const shareButtons = document.querySelectorAll(".share-article-btn");
      shareButtons.forEach((btn) => {
        if (!btn.hasAttribute("data-share-listener")) {
          btn.setAttribute("data-share-listener", "true");
          btn.addEventListener("click", (e) => {
            e.preventDefault();
            handleShareArticle(btn);
          });
        }
      });
    });
  });
})();

