import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

try:
    from .config_manager import get_current_config, is_configured, load_config
except ImportError:
    get_current_config = None
    is_configured = None
    load_config = None


class Settings(BaseSettings):
    """Application settings with flexible configuration support."""

    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash-exp", env="GEMINI_MODEL")
    mcp_server_url: str = Field(
        default="http://localhost:5000/sse", env="MCP_SERVER_URL"
    )
    transport_type: str = Field(default="sse", env="MCP_TRANSPORT_TYPE")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_reload: bool = Field(default=True, env="API_RELOAD")
    frontend_port: int = Field(default=5002, env="FRONTEND_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    max_tokens: int = Field(default=2000, env="MAX_TOKENS")
    temperature: float = Field(default=0.2, env="TEMPERATURE")
    max_tool_calls: int = Field(default=5, env="MAX_TOOL_CALLS")
    request_timeout: int = Field(default=120, env="REQUEST_TIMEOUT")
    tool_timeout: int = Field(default=60, env="TOOL_TIMEOUT")

    _is_config_loaded: bool = False

    model_config = {"env_file": ".env", "case_sensitive": False}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sync_with_config_manager()

    def _sync_with_config_manager(self):
        """Sync settings with config manager if available."""
        try:
            if not self._is_config_loaded and load_config:
                env = os.getenv("ENVIRONMENT", "development")
                config = load_config(env)

                self.gemini_api_key = config.gemini_api_key or self.gemini_api_key
                self.gemini_model = config.gemini_model
                self.mcp_server_url = config.mcp_server_url
                self.transport_type = getattr(config, 'transport_type', 'sse')
                self.api_host = config.api_host
                self.api_port = config.api_port
                self.api_reload = config.api_reload
                self.frontend_port = config.frontend_port
                self.log_level = config.log_level
                self.log_file = config.log_file
                self.max_tokens = config.max_tokens
                self.temperature = config.temperature
                self.max_tool_calls = config.max_tool_calls
                self.request_timeout = config.request_timeout
                self.tool_timeout = config.tool_timeout

                self._is_config_loaded = True

        except Exception as e:
            pass

    def refresh_from_config_manager(self):
        """Manually refresh settings from config manager."""
        self._is_config_loaded = False
        self._sync_with_config_manager()

    def is_ai_configured(self) -> bool:
        """Check if AI configuration is complete."""
        return self.gemini_api_key is not None and len(self.gemini_api_key.strip()) > 0

    def validate_critical_config(self) -> tuple[bool, list[str]]:
        """Validate critical configuration and return status with missing items."""
        missing = []

        if not self.is_ai_configured():
            missing.append("gemini_api_key")

        if not self.mcp_server_url:
            missing.append("mcp_server_url")

        return len(missing) == 0, missing


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


settings = get_settings()

try:
    from ..shared.logger import setup_logging

    setup_logging(log_level=settings.log_level, log_file=settings.log_file)
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO)
