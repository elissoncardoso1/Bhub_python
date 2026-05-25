"""
Gerenciador de modelos GGUF para LLM local.
Faz download automático de modelos do HuggingFace e gerencia cache local.
"""

from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download
from huggingface_hub.utils import HfHubHTTPError

from app.config import settings
from app.core.logging import log


class ModelManager:
    """Gerenciador de modelos GGUF para uso local."""

    # Modelos suportados e seus IDs no HuggingFace
    SUPPORTED_MODELS = {
        "Phi-3-mini-4k-instruct": {
            "repo_id": "microsoft/Phi-3-mini-4k-instruct-gguf",
            "filename": "Phi-3-mini-4k-instruct-q4.gguf",
            "alternative_filenames": [
                "Phi-3-mini-4k-instruct-Q4_K_M.gguf",
                "Phi-3-mini-4k-instruct-Q4_0.gguf",
                "Phi-3-mini-4k-instruct-q4_K_M.gguf",
            ],
            "size_gb": 2.3,
        },
    }

    def __init__(self):
        """Inicializa o gerenciador de modelos."""
        self.models_dir = Path(settings.base_dir) / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str | None = None) -> Path | None:
        """
        Retorna o caminho do modelo, fazendo download se necessário.

        Args:
            model_name: Nome do modelo (usa config se None)

        Returns:
            Caminho para o arquivo GGUF ou None se não encontrado
        """
        # Usar modelo da config se não especificado
        if model_name is None:
            model_name = settings.local_llm_model_name

        # Se há caminho customizado, usar diretamente
        if settings.local_llm_model_path:
            custom_path = Path(settings.local_llm_model_path)
            if custom_path.exists():
                log.info(f"Usando modelo customizado: {custom_path}")
                return custom_path
            else:
                log.warning(f"Caminho customizado não encontrado: {custom_path}")

        # Verificar se modelo está suportado
        if model_name not in self.SUPPORTED_MODELS:
            log.error(f"Modelo não suportado: {model_name}")
            log.info(f"Modelos suportados: {list(self.SUPPORTED_MODELS.keys())}")
            return None

        model_info = self.SUPPORTED_MODELS[model_name]
        model_path = self.models_dir / model_info["filename"]

        # Se modelo já existe, retornar
        if model_path.exists():
            log.debug(f"Modelo encontrado localmente: {model_path}")
            return model_path

        # Tentar encontrar arquivo alternativo
        for alt_filename in model_info["alternative_filenames"]:
            alt_path = self.models_dir / alt_filename
            if alt_path.exists():
                log.info(f"Usando arquivo alternativo: {alt_path}")
                return alt_path

        # Modelo não encontrado, tentar download
        log.info(f"Modelo não encontrado localmente. Iniciando download: {model_name}")
        return self.download_model(model_name)

    def download_model(
        self,
        model_name: str | None = None,
        repo_id: str | None = None,
        filename: str | None = None,
    ) -> Path | None:
        """
        Faz download do modelo do HuggingFace.

        Args:
            model_name: Nome do modelo (usa config se None)
            repo_id: ID do repositório no HuggingFace (opcional)
            filename: Nome do arquivo específico (opcional)

        Returns:
            Caminho para o arquivo baixado ou None em caso de erro
        """
        if model_name is None:
            model_name = settings.local_llm_model_name

        if model_name not in self.SUPPORTED_MODELS:
            log.error(f"Modelo não suportado: {model_name}")
            return None

        model_info = self.SUPPORTED_MODELS[model_name]
        repo_id = repo_id or model_info["repo_id"]
        filename = filename or model_info["filename"]

        try:
            log.info(f"Baixando modelo {model_name} do HuggingFace...")
            log.info(f"Repositório: {repo_id}")
            log.info(f"Arquivo: {filename}")
            log.info(f"Tamanho estimado: ~{model_info['size_gb']} GB")

            # Tentar baixar o arquivo específico primeiro
            try:
                model_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=str(self.models_dir),
                    local_dir_use_symlinks=False,
                )
                log.info(f"Modelo baixado com sucesso: {model_path}")
                return Path(model_path)
            except HfHubHTTPError:
                # Se arquivo específico não existe, tentar alternativas
                log.warning(f"Arquivo {filename} não encontrado, tentando alternativas...")
                for alt_filename in model_info["alternative_filenames"]:
                    try:
                        model_path = hf_hub_download(
                            repo_id=repo_id,
                            filename=alt_filename,
                            local_dir=str(self.models_dir),
                            local_dir_use_symlinks=False,
                        )
                        log.info(f"Modelo baixado (alternativo): {model_path}")
                        return Path(model_path)
                    except HfHubHTTPError:
                        continue

                # Se nenhum arquivo específico funcionou, listar arquivos disponíveis
                log.warning("Nenhum arquivo específico encontrado. Listando arquivos disponíveis...")
                try:
                    # Fazer snapshot download para ver o que está disponível
                    snapshot_path = snapshot_download(
                        repo_id=repo_id,
                        local_dir=str(self.models_dir / model_name),
                        local_dir_use_symlinks=False,
                    )
                    # Procurar arquivos .gguf
                    snapshot_dir = Path(snapshot_path)
                    gguf_files = list(snapshot_dir.glob("*.gguf"))
                    if gguf_files:
                        # Usar o primeiro arquivo GGUF encontrado
                        model_path = gguf_files[0]
                        log.info(f"Usando arquivo GGUF encontrado: {model_path}")
                        return model_path
                    else:
                        log.error("Nenhum arquivo .gguf encontrado no repositório")
                        return None
                except Exception as e:
                    log.error(f"Erro ao listar arquivos do repositório: {e}")
                    return None

        except Exception as e:
            log.error(f"Erro ao baixar modelo {model_name}: {e}")
            log.error(
                "Verifique sua conexão com a internet e se o repositório existe no HuggingFace."
            )
            return None

    def verify_model(self, model_path: Path) -> bool:
        """
        Verifica integridade do modelo.

        Args:
            model_path: Caminho para o arquivo do modelo

        Returns:
            True se o modelo parece válido
        """
        if not model_path.exists():
            return False

        # Verificar se é um arquivo GGUF válido
        # GGUF começa com magic bytes "GGUF"
        try:
            with open(model_path, "rb") as f:
                magic = f.read(4)
                if magic != b"GGUF":
                    log.warning(f"Arquivo não parece ser um GGUF válido: {model_path}")
                    return False
        except Exception as e:
            log.error(f"Erro ao verificar modelo: {e}")
            return False

        # Verificar tamanho mínimo (GGUF deve ter pelo menos alguns MB)
        size_mb = model_path.stat().st_size / (1024 * 1024)
        if size_mb < 100:  # Muito pequeno para ser um modelo válido
            log.warning(f"Arquivo muito pequeno para ser um modelo válido: {size_mb:.2f} MB")
            return False

        log.info(f"Modelo verificado: {model_path} ({size_mb:.2f} MB)")
        return True

    def get_model_info(self, model_name: str | None = None) -> dict | None:
        """
        Retorna informações sobre o modelo.

        Args:
            model_name: Nome do modelo (usa config se None)

        Returns:
            Dict com informações do modelo ou None
        """
        if model_name is None:
            model_name = settings.local_llm_model_name

        if model_name not in self.SUPPORTED_MODELS:
            return None

        info = self.SUPPORTED_MODELS[model_name].copy()
        model_path = self.get_model_path(model_name)

        if model_path and model_path.exists():
            info["local_path"] = str(model_path)
            info["exists"] = True
            info["size_mb"] = model_path.stat().st_size / (1024 * 1024)
        else:
            info["exists"] = False

        return info


# Instância global
_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Retorna instância do gerenciador de modelos."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
