# AI and Machine Learning Architecture

This document outlines the AI and Machine Learning architecture of the BHub backend, emphasizing the intelligent orchestration and fallback strategies between local models and remote APIs.

## 1. Overview

The AI layer in BHub is designed for high availability and progressive fallback. The primary goal is to classify, parse, and extract information from scientific articles efficiently. It coordinates between lightweight local models (embeddings) for fast and cheap classification and heavy remote LLMs (like DeepSeek) for complex extraction and reasoning.

The core components reside in two main directories:
- `app/ai/`: Contains the orchestration logic, fallback managers, and remote LLM integrations.
- `app/ml/`: Houses local Machine Learning models, specifically embedding classifiers using sentence-transformers.

## 2. Key Components

### 2.1 AI Manager (`app/ai/manager.py`)
The `AIManager` is the central orchestrator of all AI tasks. It acts as the facade for the application to request AI services without worrying about the underlying provider.

**Responsibilities:**
- Route requests to the appropriate AI service (e.g., DeepSeek, Local LLM, or Embeddings).
- Implement the **Fallback Strategy**: If a preferred provider (e.g., DeepSeek API) fails, timeouts, or is rate-limited, the `AIManager` automatically falls back to a secondary provider (e.g., a local quantized LLM like Phi-3 or an embedding-based heuristic).

### 2.2 Local LLM Service (`app/ai/local_llm_service.py`)
This service interacts with locally hosted, quantized Large Language Models (e.g., Phi-3-mini-4k-instruct-q4.gguf). 

**Role in the Architecture:**
- Serves as a robust, privacy-preserving, and cost-free fallback when remote APIs are unavailable.
- Handles tasks that require reasoning but can tolerate slightly lower accuracy or higher latency compared to massive remote models.

### 2.3 Embedding Classifier (`app/ml/embedding_classifier.py`)
The `EmbeddingClassifier` utilizes local sentence-transformers to generate vector embeddings of text.

**Role in the Architecture:**
- Provides extremely fast, CPU-friendly classification and similarity scoring.
- Used as the first line of defense for categorizing articles and routing them to the correct processing pipeline before involving an LLM.

## 3. Fallback and Orchestration Strategy

The intelligent orchestration is a core strength of the BHub architecture.

**Workflow Example (Article Parsing & Classification):**
1. **Initial Assessment (Embeddings):** When a new article is ingested, the system first passes the title and abstract through the `EmbeddingClassifier`. This provides a baseline classification based on vector similarity at zero API cost.
2. **Primary Extraction (Remote LLM):** For complex metadata extraction (authors, impact rating, detailed summaries), the `AIManager` calls the primary remote provider (e.g., `DeepSeekService`).
3. **Fallback Trigger:** If the DeepSeek API returns an HTTP 5xx error, a rate limit (429), or a timeout, the `AIManager` catches the exception.
4. **Secondary Extraction (Local LLM):** The `AIManager` transparently routes the failed request to the `LocalLLMService`. The local model processes the prompt and returns the result, ensuring the background job doesn't fail completely.

## 4. Future Improvements

As noted in the architecture review, the orchestration currently lacks detailed observability. Future iterations should incorporate APM (Application Performance Monitoring) to track:
- Latency differences between remote and local providers.
- Frequency of fallback triggers to alert on API stability issues.
- Overall token usage and cost metrics.
