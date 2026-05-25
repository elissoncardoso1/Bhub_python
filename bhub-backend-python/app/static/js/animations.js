/**
 * BHUB - Animações com Anime.js
 * ==============================
 * Integração da biblioteca anime.js para animações avançadas
 * Compatível com o sistema existente de animações CSS
 */

(function() {
  'use strict';

  // Verificar se anime.js está disponível
  if (typeof anime === 'undefined') {
    console.warn('anime.js não está disponível. Animações avançadas desabilitadas.');
    return;
  }

  // Respeitar prefers-reduced-motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /**
   * Animações de entrada para cards de artigos
   */
  function animateArticleCards() {
    const cards = document.querySelectorAll('.article-card:not(.animated)');

    if (cards.length === 0 || prefersReducedMotion) return;

    anime({
      targets: cards,
      opacity: [0, 1],
      translateY: [30, 0],
      scale: [0.95, 1],
      duration: 600,
      easing: 'easeOutCubic',
      delay: anime.stagger(100, { start: 0 }),
      complete: function() {
        cards.forEach(card => card.classList.add('animated'));
      }
    });
  }

  /**
   * Animações de scroll (substitui Intersection Observer)
   */
  function initScrollAnimations() {
    if (prefersReducedMotion) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !entry.target.classList.contains('anime-visible')) {
          entry.target.classList.add('anime-visible');

          const animationType = entry.target.dataset.animeType || 'fadeInUp';

          switch(animationType) {
            case 'fadeInUp':
              anime({
                targets: entry.target,
                opacity: [0, 1],
                translateY: [30, 0],
                duration: 600,
                easing: 'easeOutCubic'
              });
              break;
            case 'fadeInDown':
              anime({
                targets: entry.target,
                opacity: [0, 1],
                translateY: [-30, 0],
                duration: 600,
                easing: 'easeOutCubic'
              });
              break;
            case 'fadeInScale':
              anime({
                targets: entry.target,
                opacity: [0, 1],
                scale: [0.9, 1],
                duration: 600,
                easing: 'easeOutCubic'
              });
              break;
            case 'slideInLeft':
              anime({
                targets: entry.target,
                opacity: [0, 1],
                translateX: [-50, 0],
                duration: 600,
                easing: 'easeOutCubic'
              });
              break;
            case 'slideInRight':
              anime({
                targets: entry.target,
                opacity: [0, 1],
                translateX: [50, 0],
                duration: 600,
                easing: 'easeOutCubic'
              });
              break;
          }

          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    // Observar elementos com classe animate-on-scroll
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
      observer.observe(el);
    });
  }

  /**
   * Animação de entrada para modais
   */
  function animateModal(modalElement) {
    if (!modalElement || prefersReducedMotion) return;

    const backdrop = modalElement.querySelector('.modal-backdrop');
    const content = modalElement.querySelector('.modal-content') || modalElement;

    // Reset
    if (backdrop) {
      backdrop.style.opacity = '0';
    }
    content.style.opacity = '0';
    content.style.transform = 'scale(0.9)';

    // Animar backdrop
    if (backdrop) {
      anime({
        targets: backdrop,
        opacity: [0, 1],
        duration: 300,
        easing: 'easeOutCubic'
      });
    }

    // Animar conteúdo
    anime({
      targets: content,
      opacity: [0, 1],
      scale: [0.9, 1],
      duration: 400,
      easing: 'easeOutCubic',
      delay: 100
    });
  }

  /**
   * Animação de saída para modais
   */
  function animateModalOut(modalElement, callback) {
    if (!modalElement || prefersReducedMotion) {
      if (callback) callback();
      return;
    }

    const backdrop = modalElement.querySelector('.modal-backdrop');
    const content = modalElement.querySelector('.modal-content') || modalElement;

    anime({
      targets: content,
      opacity: [1, 0],
      scale: [1, 0.9],
      duration: 300,
      easing: 'easeInCubic'
    });

    if (backdrop) {
      anime({
        targets: backdrop,
        opacity: [1, 0],
        duration: 300,
        easing: 'easeInCubic',
        complete: callback
      });
    } else {
      setTimeout(callback, 300);
    }
  }

  /**
   * Animação de toast/notificação
   */
  function animateToast(toastElement) {
    if (!toastElement || prefersReducedMotion) return;

    toastElement.style.opacity = '0';
    toastElement.style.transform = 'translateX(100px)';

    anime({
      targets: toastElement,
      opacity: [0, 1],
      translateX: [100, 0],
      duration: 400,
      easing: 'easeOutCubic'
    });
  }

  /**
   * Animação de saída para toast
   */
  function animateToastOut(toastElement, callback) {
    if (!toastElement || prefersReducedMotion) {
      if (callback) callback();
      return;
    }

    anime({
      targets: toastElement,
      opacity: [1, 0],
      translateX: [0, 100],
      duration: 300,
      easing: 'easeInCubic',
      complete: callback
    });
  }

  /**
   * Animação de hover para cards
   */
  function initCardHoverAnimations() {
    if (prefersReducedMotion) return;

    const cards = document.querySelectorAll('.article-card');

    cards.forEach(card => {
      card.addEventListener('mouseenter', function() {
        anime({
          targets: this,
          scale: [1, 1.02],
          duration: 300,
          easing: 'easeOutCubic'
        });
      });

      card.addEventListener('mouseleave', function() {
        anime({
          targets: this,
          scale: [1.02, 1],
          duration: 300,
          easing: 'easeOutCubic'
        });
      });
    });
  }

  /**
   * Animação de loading (skeleton fade out)
   */
  function animateSkeletonOut(skeletonElement) {
    if (!skeletonElement || prefersReducedMotion) return;

    anime({
      targets: skeletonElement,
      opacity: [1, 0],
      duration: 300,
      easing: 'easeOutCubic',
      complete: function() {
        skeletonElement.style.display = 'none';
      }
    });
  }

  /**
   * Animação stagger para lista de cards
   */
  function animateStaggerCards(container) {
    if (!container || prefersReducedMotion) return;

    const cards = container.querySelectorAll('.article-card:not(.animated)');

    if (cards.length === 0) return;

    anime({
      targets: cards,
      opacity: [0, 1],
      translateY: [20, 0],
      duration: 500,
      easing: 'easeOutCubic',
      delay: anime.stagger(80),
      complete: function() {
        cards.forEach(card => card.classList.add('animated'));
      }
    });
  }

  /**
   * Inicialização quando DOM estiver pronto
   */
  function init() {
    // Animar cards existentes
    animateArticleCards();

    // Inicializar animações de scroll
    initScrollAnimations();

    // Inicializar hover animations
    initCardHoverAnimations();

    // Animar cards após HTMX swap
    document.body.addEventListener('htmx:afterSwap', function(event) {
      // Pequeno delay para garantir que o DOM foi atualizado
      setTimeout(() => {
        const target = event.detail.target;

        // Se for o grid de artigos, animar os cards
        if (target.id === 'articles-grid' || target.id === 'search-results') {
          animateStaggerCards(target);
        }

        // Re-inicializar hover animations
        initCardHoverAnimations();
      }, 50);
    });

    // Animar modais quando abertos
    document.body.addEventListener('htmx:afterSwap', function(event) {
      const modal = document.getElementById('modal-container');
      if (modal && modal.innerHTML.trim() !== '') {
        setTimeout(() => animateModal(modal), 50);
      }
    });

    // Animar toasts
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer) {
      const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
          mutation.addedNodes.forEach(function(node) {
            if (node.nodeType === 1) { // Element node
              animateToast(node);
            }
          });
        });
      });

      observer.observe(toastContainer, { childList: true });
    }
  }

  // Exportar funções globalmente
  window.bhubAnimations = {
    animateArticleCards,
    animateModal,
    animateModalOut,
    animateToast,
    animateToastOut,
    animateStaggerCards,
    animateSkeletonOut,
    initScrollAnimations,
    initCardHoverAnimations
  };

  // Inicializar quando DOM estiver pronto
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
