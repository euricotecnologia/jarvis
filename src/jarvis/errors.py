class JarvisError(Exception):
    """Erro base exibivel ao usuário."""


class ConfigurationError(JarvisError):
    """Configuração ausente ou invalida."""


class DatabaseUnavailable(JarvisError):
    """O banco local não pode ser lido/gravado (disco, permissão ou antivirus)."""


class ProviderError(JarvisError):
    """Falha devolvida por um provedor de modelo."""

    status_code: int | None = None


class ProviderUnavailable(ProviderError):
    """Provedor não está acessivel ou não está configurado."""


class NoProviderAvailable(ProviderError):
    """Nenhum provedor conseguiu atender a requisição."""


class ToolError(JarvisError):
    """Falha recuperavel na execução de uma ferramenta do agente."""


class PermissionDenied(ToolError):
    """A ação está fora do que as permissões do agente autorizam."""

