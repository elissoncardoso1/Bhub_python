/**
 * Serviço de tradução com cache.
 * Comunica com o backend para traduzir textos usando DeepSeek API.
 */

import { ApiClient } from './api';

export interface TranslationRequest {
  text: string;
  source_lang?: string;
  target_lang?: string;
}

export interface TranslationResponse {
  original: string;
  translated: string;
  provider: string | null;
  cached: boolean;
}

export class TranslationService {
  /**
   * Solicita tradução de um texto.
   * O backend verifica o cache antes de chamar a API externa.
   * 
   * @param text - Texto a traduzir
   * @param sourceLang - Idioma de origem (padrão: 'en')
   * @param targetLang - Idioma de destino (padrão: 'pt-BR')
   * @returns Resposta com texto traduzido e informações de cache
   */
  static async translate(
    text: string,
    sourceLang: string = 'en',
    targetLang: string = 'pt-BR'
  ): Promise<TranslationResponse> {
    if (!text || !text.trim()) {
      throw new Error('Texto não pode estar vazio');
    }

    if (text.length > 10000) {
      throw new Error('Texto muito longo. Máximo de 10000 caracteres.');
    }

    return ApiClient.post<TranslationResponse>('/ai/translate', {
      text: text.trim(),
      source_lang: sourceLang,
      target_lang: targetLang,
    });
  }

  /**
   * Traduz apenas o título de um artigo.
   */
  static async translateTitle(
    title: string,
    sourceLang: string = 'en',
    targetLang: string = 'pt-BR'
  ): Promise<string> {
    const response = await this.translate(title, sourceLang, targetLang);
    return response.translated;
  }

  /**
   * Traduz o resumo de um artigo.
   */
  static async translateAbstract(
    abstract: string,
    sourceLang: string = 'en',
    targetLang: string = 'pt-BR'
  ): Promise<string> {
    const response = await this.translate(abstract, sourceLang, targetLang);
    return response.translated;
  }
}

