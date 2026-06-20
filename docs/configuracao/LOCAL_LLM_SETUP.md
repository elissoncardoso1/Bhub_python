# Configuração do LLM Local (Phi-3 Mini)

Este guia explica como configurar e usar o modelo Phi-3 Mini localmente para classificação de artigos, usando llama.cpp para execução eficiente em CPU.

## Visão Geral

O sistema agora suporta classificação local usando modelos GGUF quantizados rodando via `llama-cpp-python`. Isso oferece:

- **Sem custos de API**: Classificação totalmente local
- **Privacidade**: Dados não saem do servidor
- **Performance**: Roda eficientemente em CPU
- **Confiabilidade**: Não depende de serviços externos

## Requisitos de Sistema

### Mínimos
- **RAM**: 4GB (recomendado 8GB+)
- **CPU**: Qualquer CPU moderno (multi-core recomendado)
- **Disco**: ~3GB para modelo Q4
- **Python**: 3.9+

### Recomendados
- **RAM**: 8GB+
- **CPU**: 4+ cores
- **Disco**: 5GB+ (para cache e múltiplos modelos)

## Instalação

### 1. Instalar Dependências

```bash
pip install llama-cpp-python huggingface-hub
```

Ou usando o requirements.txt:

```bash
pip install -r requirements.txt
```

**Nota**: `llama-cpp-python` pode levar alguns minutos para compilar na primeira instalação.

### 2. Configurar Variáveis de Ambiente

Adicione ao seu arquivo `.env`:

```bash
# Habilitar LLM local
LOCAL_LLM_ENABLED=true

# Nome do modelo (padrão: Phi-3-mini-4k-instruct)
LOCAL_LLM_MODEL_NAME=Phi-3-mini-4k-instruct

# Caminho customizado do modelo (opcional)
# Se não especificado, o modelo será baixado automaticamente
# LOCAL_LLM_MODEL_PATH=/path/to/model.gguf

# Configurações de Performance
LOCAL_LLM_N_THREADS=4      # Threads CPU (0 = auto-detect)
LOCAL_LLM_N_CTX=4096       # Contexto máximo
LOCAL_LLM_N_GPU_LAYERS=0   # Camadas GPU (0 = CPU apenas)
LOCAL_LLM_TEMPERATURE=0.1  # Temperatura para classificação
LOCAL_LLM_MAX_TOKENS=100    # Tokens máximos na resposta
```

### 3. Download do Modelo

O modelo será baixado automaticamente na primeira execução, ou você pode usar o script de setup:

```bash
python scripts/setup_local_llm.py
```

Este script:
- Verifica dependências
- Valida configuração
- Baixa o modelo Phi-3 Mini (~2.3 GB)
- Testa classificação e tradução
- Verifica integridade do modelo

### 4. Verificar Instalação

Execute o script de setup para validar:

```bash
python scripts/setup_local_llm.py
```

Você deve ver:
```
✅ Todos os testes passaram!
O LLM local está pronto para uso.
```

## Uso

### Classificação Automática

O LLM local será usado automaticamente quando `LOCAL_LLM_ENABLED=true`. A ordem de prioridade é:

1. **Local LLM** (Phi-3 Mini) - se habilitado
2. DeepSeek API
3. OpenRouter API
4. HuggingFace API
5. EmbeddingClassifier (ML local)
6. HeuristicClassifier (fallback)

### Classificação Manual via API

```bash
curl -X POST "http://localhost:8000/api/v1/ai/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Applied Behavior Analysis intervention for children with autism",
    "use_external": false
  }'
```

### Verificar Status

```bash
curl "http://localhost:8000/api/v1/ai/status"
```

## Configuração Avançada

### Otimização de Performance

#### Ajustar Threads CPU

Para melhor performance, ajuste `LOCAL_LLM_N_THREADS`:

```bash
# Auto-detect (recomendado)
LOCAL_LLM_N_THREADS=0

# Manual (use número de cores físicos)
LOCAL_LLM_N_THREADS=4
```

#### Ajustar Contexto

Para textos mais longos:

```bash
LOCAL_LLM_N_CTX=8192  # Maior contexto = mais memória
```

#### Usar GPU (se disponível)

```bash
LOCAL_LLM_N_GPU_LAYERS=20  # Número de camadas na GPU
```

**Nota**: Requer `llama-cpp-python` compilado com suporte CUDA/ROCm.

### Modelos Alternativos

O sistema atualmente suporta:
- **Phi-3-mini-4k-instruct** (padrão, ~2.3GB Q4)

Para adicionar outros modelos, edite `app/ai/model_manager.py` e adicione ao dicionário `SUPPORTED_MODELS`.

### Caminho Customizado do Modelo

Se você já tem o modelo baixado:

```bash
LOCAL_LLM_MODEL_PATH=/caminho/para/modelo.gguf
```

O sistema verificará este caminho primeiro antes de tentar download automático.

## Troubleshooting

### Erro: "llama-cpp-python não instalado"

```bash
pip install llama-cpp-python
```

Se houver problemas de compilação, tente:

```bash
# macOS
CMAKE_ARGS="-DCMAKE_OSX_ARCHITECTURES=arm64" pip install llama-cpp-python

# Linux
pip install llama-cpp-python --no-cache-dir
```

### Erro: "Modelo não encontrado"

1. Verifique se `LOCAL_LLM_ENABLED=true`
2. Execute o script de setup: `python scripts/setup_local_llm.py`
3. Verifique espaço em disco (precisa ~3GB)

### Erro: "Out of memory"

1. Reduza `LOCAL_LLM_N_CTX` (ex: 2048)
2. Use quantização menor (Q4_0 ao invés de Q4_K_M)
3. Aumente RAM disponível

### Performance Lenta

1. Aumente `LOCAL_LLM_N_THREADS` (até número de cores)
2. Use quantização menor (Q4_0 é mais rápido que Q4_K_M)
3. Reduza `LOCAL_LLM_N_CTX` se não precisar de contexto longo

### Modelo não carrega

1. Verifique se o arquivo existe: `ls models/`
2. Verifique integridade: `python scripts/setup_local_llm.py`
3. Refaça download: delete `models/` e execute setup novamente

## Performance Esperada

### Latência
- **Classificação**: 1-5 segundos (dependendo do hardware)
- **Tradução**: 2-10 segundos (dependendo do tamanho do texto)

### Throughput
- **CPU 4 cores**: ~5-10 classificações/minuto
- **CPU 8 cores**: ~10-20 classificações/minuto
- **CPU 16+ cores**: ~20-40 classificações/minuto

### Qualidade
- **Classificação**: Similar ou melhor que APIs externas
- **Tradução**: Boa qualidade, mantém termos técnicos

## Comparação com APIs Externas

| Aspecto | LLM Local | APIs Externas |
|---------|-----------|---------------|
| **Custo** | Grátis | Pago por uso |
| **Latência** | 1-5s | 0.5-2s |
| **Privacidade** | 100% local | Dados enviados |
| **Confiabilidade** | Sem dependência externa | Depende de internet |
| **Setup** | Requer download | Pronto para uso |
| **RAM** | 4-8GB | N/A |

## Manutenção

### Atualizar Modelo

Para atualizar o modelo:

1. Delete o modelo antigo: `rm models/Phi-3-mini-4k-instruct-q4.gguf`
2. Execute setup novamente: `python scripts/setup_local_llm.py`

### Limpar Cache

O modelo fica em `models/` na raiz do projeto. Para limpar:

```bash
rm -rf models/
```

### Logs

Logs detalhados estão disponíveis em:
- `logs/combined.log` - Logs gerais
- `logs/error.log` - Apenas erros

Procure por `LocalLLM` ou `llama` nos logs para debug.

## Suporte

Para problemas ou dúvidas:
1. Verifique os logs: `tail -f logs/combined.log`
2. Execute o script de setup: `python scripts/setup_local_llm.py`
3. Verifique configuração: `grep LOCAL_LLM .env`

## Próximos Passos

- [ ] Suporte a mais modelos (Llama 3.2, Mistral, etc.)
- [ ] Batch processing para múltiplos artigos
- [ ] Cache de classificações similares
- [ ] Suporte a quantização Q8 para melhor qualidade
- [ ] Métricas de performance e monitoramento

