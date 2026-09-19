# Prompt: Implementação de Tradução com Cache Sob Demanda (DeepSeek)

> STATUS: HISTÓRICO
> Este documento não representa necessariamente a arquitetura atual.
> Consulte docs/architecture/CURRENT_ARCHITECTURE.md.
>
> Especificação escrita para a arquitetura daquela fase — "Frontend (TypeScript/Node.js) →
> Backend (Python - API) → Cache Layer (DB + Memória)" —, anterior à migração para SSR/HTMX.
> A implementação atual é `app/services/translation_cache_service.py` +
> `app/models/translation_cache.py` (`docs/architecture/CURRENT_ARCHITECTURE.md` § 7).

## 🎯 Objetivo
Desenvolver uma solução de tradução que utilize a API da DeepSeek com cache inteligente para evitar chamadas repetidas, reduzindo custos e melhorando o desempenho.

## 📋 Requisitos Técnicos

### 1. Arquitetura
```
Frontend (TypeScript/Node.js)
   ↓
Backend (Python - API)
   ↓
Cache Layer (DB + Memória)
   ↓
DeepSeek API
```

### 2. Componentes Principais

#### Frontend
- Solicita tradução sob demanda
- Não chama diretamente a DeepSeek
- Comunicação via endpoint `/api/translate`

#### Backend
- Orquestra o processo completo
- Verificação de cache antes de chamar DeepSeek
- Persistência da tradução

#### DeepSeek API
- Usada para classificação e tradução
- Apenas chamada quando necessário

#### Camada de Cache
- Banco relacional ou NoSQL
- Cache em memória opcional para hot paths

### 3. Fluxo de Tradução
```
Usuário clica em "Traduzir"
→ Frontend → Backend /translate
→ Backend gera chave de cache
→ Consulta cache (DB)
   ├─ HIT → retorna tradução
   └─ MISS → chama DeepSeek → salva tradução → retorna ao frontend
```

### 4. Estratégia de Chave de Cache
```python
def generate_cache_key(text, source_lang, target_lang, model_version):
    normalized = normalize_text(text)  # trim, lowercase, remover espaços duplicados
    key = hash(
        source_lang + 
        target_lang + 
        normalized + 
        model_version
    )
    return key
```

### 5. Modelo de Dados (translations_cache)
```sql
CREATE TABLE translations_cache (
    id UUID PRIMARY KEY,
    content_hash TEXT UNIQUE,
    source_language VARCHAR(10),
    target_language VARCHAR(10),
    original_text TEXT,
    translated_text TEXT,
    model VARCHAR(50),
    created_at TIMESTAMP,
    last_accessed_at TIMESTAMP,
    INDEX(content_hash),
    INDEX(last_accessed_at)
);
```

### 6. Endpoint Backend (/api/translate)
**Request:**
```json
POST /api/translate
{
  "text": "Alternative-reinforcer magnitude effects on resurgence...",
  "source_lang": "en",
  "target_lang": "pt-BR"
}
```

**Response:**
```json
{
  "translated_text": "Efeitos da magnitude do reforçador alternativo na ressurgência...",
  "cached": true
}
```

### 7. Pseudocódigo Backend (Python)
```python
def translate(text, source_lang, target_lang):
    normalized = normalize(text)
    key = generate_hash(normalized, source_lang, target_lang, MODEL_VERSION)
    
    cached = db.find_translation(key)
    if cached:
        db.update_last_accessed(key)
        return cached.translated_text, True
    
    translated = deepseek.translate(
        text=text,
        source_lang=source_lang,
        target_lang=target_lang
    )
    
    db.save_translation(
        content_hash=key,
        original_text=text,
        translated_text=translated,
        source_language=source_lang,
        target_language=target_lang,
        model=MODEL_VERSION
    )
    
    return translated, False
```

### 8. Pseudocódigo Frontend (TypeScript)
```typescript
async function requestTranslation(text: string) {
  const response = await fetch("/api/translate", {
    method: "POST",
    body: JSON.stringify({
      text,
      source_lang: "en",
      target_lang: "pt-BR"
    })
  });

  const data = await response.json();
  return data.translated_text;
}
```

## 🛠️ Implementação

### Backend (Python)
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import hashlib
import re
from datetime import datetime
import httpx

app = FastAPI()

# Configurações
DEEPSEEK_API_KEY = "sua_chave_api_aqui"
MODEL_VERSION = "deepseek-translator-v2"
DB_CONNECTION = "sua_conexao_db"

class TranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

def normalize_text(text: str) -> str:
    """Normaliza texto para consistência no cache"""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # remover espaços duplicados
    return text.lower()  # opcional, dependendo do caso

def generate_cache_key(text: str, source_lang: str, target_lang: str, model_version: str) -> str:
    """Gera chave de cache única"""
    normalized = normalize_text(text)
    key_data = f"{source_lang}{target_lang}{normalized}{model_version}".encode('utf-8')
    return hashlib.sha256(key_data).hexdigest()

@app.post("/api/translate")
async def translate(request: TranslationRequest):
    try:
        # Gerar chave de cache
        cache_key = generate_cache_key(
            request.text, 
            request.source_lang, 
            request.target_lang, 
            MODEL_VERSION
        )
        
        # Verificar cache
        cached_translation = db.get_translation(cache_key)
        if cached_translation:
            db.update_access_time(cache_key)
            return {
                "translated_text": cached_translation.translated_text,
                "cached": True
            }
        
        # Chamar DeepSeek
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepseek.com/translate",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "text": request.text,
                    "source_language": request.source_lang,
                    "target_language": request.target_lang,
                    "model": MODEL_VERSION
                }
            )
            response.raise_for_status()
            result = response.json()
            translated_text = result["translated_text"]
        
        # Salvar no cache
        db.save_translation(
            content_hash=cache_key,
            original_text=request.text,
            translated_text=translated_text,
            source_language=request.source_lang,
            target_language=request.target_lang,
            model=MODEL_VERSION
        )
        
        return {
            "translated_text": translated_text,
            "cached": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Frontend (TypeScript/React)
```typescript
import React, { useState } from 'react';

interface TranslationResponse {
  translated_text: string;
  cached: boolean;
}

const TranslationApp: React.FC = () => {
  const [text, setText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [isTranslating, setIsTranslating] = useState(false);
  const [cached, setCached] = useState(false);

  const requestTranslation = async () => {
    if (!text.trim()) return;
    
    setIsTranslating(true);
    setCached(false);
    
    try {
      const response = await fetch('/api/translate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          source_lang: 'en',
          target_lang: 'pt-BR'
        })
      });
      
      const data: TranslationResponse = await response.json();
      setTranslatedText(data.translated_text);
      setCached(data.cached);
    } catch (error) {
      console.error('Translation failed:', error);
    } finally {
      setIsTranslating(false);
    }
  };

  return (
    <div className="translation-container">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter text to translate..."
      />
      <button 
        onClick={requestTranslation}
        disabled={isTranslating}
      >
        {isTranslating ? 'Translating...' : 'Translate'}
      </button>
      
      {translatedText && (
        <div className="result">
          <p>Translation:</p>
          <p className={cached ? 'cached' : ''}>{translatedText}</p>
          {cached && <small>Retrieved from cache</small>}
        </div>
      )}
    </div>
  );
};

export default TranslationApp;
```

## 🔧 Configurações Adicionais

### Cache em Memória (Redis - Opcional)
```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@app.post("/api/translate")
async def translate(request: TranslationRequest):
    # ... (código anterior)
    
    # Verificar cache Redis primeiro
    cached_text = redis_client.get(cache_key)
    if cached_text:
        db.update_access_time(cache_key)  # Atualizar DB para análise
        return {"translated_text": cached_text.decode('utf-8'), "cached": True}
    
    # ... (resto do código)
    
    # Salvar no Redis
    redis_client.setex(cache_key, 3600, translated_text)  # 1 hora de TTL
```

### Políticas de Limpeza de Cache
```python
def clean_old_translations(days=30):
    """Remove traduções não acessadas há mais de X dias"""
    cutoff_date = datetime.now() - timedelta(days=days)
    db.delete_translations_older_than(cutoff_date)
```

## 📊 Boas Práticas

1. **Rate Limiting**: Implementar limites de chamadas por usuário/IP
2. **Logging**: Registrar todas as chamadas à DeepSeek para monitoramento
3. **Timeouts**: Definir timeouts curtos para chamadas externas
4. **Sanitização**: Validar e sanitizar texto de entrada
5. **Versionamento**: Manter controle de versão do modelo de tradução

## 🚀 Extensões Futuras

- TTL inteligente baseado em acesso
- Cache por parágrafo para textos longos
- Pré-tradução automática para conteúdo popular
- Fallback para outros modelos de tradução
- Análise de custo/benefício do cache

Esta implementação garante:
- ✅ Evita chamadas repetidas à DeepSeek
- ✅ Reduz custos de API
- ✅ Escala bem com uso crescente
- ✅ Transparente para o usuário final
- ✅ Fácil manutenção e atualização