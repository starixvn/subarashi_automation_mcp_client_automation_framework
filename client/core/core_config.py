"""
Unified configuration system for MCP Client.
Combines Settings (Pydantic) and ConfigManager functionality into one module.
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from threading import Lock

from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class MCPClientConfig:
    """Configuration data class for MCP Client."""

    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash-exp"
    mcp_server_url: str = "http://localhost:5000/sse"
    transport_type: str = "sse"  # sse, websocket, or stdio
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    frontend_port: int = 5002
    log_level: str = "INFO"
    log_file: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.2
    max_tool_calls: int = 5
    request_timeout: int = 120
    tool_timeout: int = 60
    environment: str = "development"  # development, production
    config_source: str = "default"  # default, file, frontend


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
            if not self._is_config_loaded:
                env = os.getenv("ENVIRONMENT", "development")
                config = load_config(env)

                self.gemini_api_key = config.gemini_api_key or self.gemini_api_key
                self.gemini_model = config.gemini_model
                self.mcp_server_url = config.mcp_server_url
                self.transport_type = getattr(config, "transport_type", "sse")
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


class ConfigManager:
    """Manages configuration loading and updating."""

    def __init__(self):
        self._config: MCPClientConfig = MCPClientConfig()
        self._lock = Lock()
        self._config_file_path: Optional[Path] = None
        self._is_configured = False

    def load_config(self, environment: str = "development") -> MCPClientConfig:
        """Load configuration based on environment."""
        with self._lock:
            config_loaded = self._load_from_config_file(environment)

            if not config_loaded:
                self._load_from_environment()
            self._config.environment = environment
            logger.info(f"Configuration loaded for environment: {environment}")
            logger.info(f"Config source: {self._config.config_source}")
            logger.info(f"MCP Server URL: {self._config.mcp_server_url}")
            logger.info(f"Transport Type: {self._config.transport_type}")
            logger.info(f"API configured: {self._config.gemini_api_key is not None}")

            return self._config

    def update_config(self, updates: Dict[str, Any], save_to_file: bool = True) -> bool:
        """Update configuration with new values."""
        with self._lock:
            try:
                old_config = asdict(self._config)

                for key, value in updates.items():
                    if hasattr(self._config, key):
                        setattr(self._config, key, value)
                        logger.info(f"Updated config: {key} = {value}")
                    else:
                        logger.warning(f"Unknown config key: {key}")

                if self._config.gemini_api_key:
                    self._is_configured = True
                    self._config.config_source = "frontend"

                if save_to_file and self._config_file_path:
                    self._save_to_config_file()

                logger.info("Configuration updated successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to update configuration: {str(e)}")
                for key, value in old_config.items():
                    setattr(self._config, key, value)
                return False

    def get_config(self) -> MCPClientConfig:
        """Get current configuration."""
        with self._lock:
            return self._config

    def is_configured(self) -> bool:
        """Check if configuration is complete."""
        return self._is_configured and self._config.gemini_api_key is not None

    def _load_from_config_file(self, environment: str) -> bool:
        """Load configuration from JSON file."""
        try:
            config_dir = Path(__file__).parent.parent.parent / "config"
            config_file = config_dir / f"{environment}.json"

            if not config_file.exists():
                logger.info(f"Config file not found: {config_file}")
                return False

            self._config_file_path = config_file

            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            for key, value in config_data.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)

            self._config.config_source = "file"

            if self._config.gemini_api_key:
                self._is_configured = True

            logger.info(f"Configuration loaded from file: {config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to load config from file: {str(e)}")
            return False

    def _load_from_environment(self):
        """Load configuration from environment variables as fallback."""
        try:
            env_mapping = {
                "gemini_api_key": "GEMINI_API_KEY",
                "gemini_model": "GEMINI_MODEL",
                "mcp_server_url": "MCP_SERVER_URL",
                "transport_type": "MCP_TRANSPORT_TYPE",
                "api_host": "API_HOST",
                "api_port": "API_PORT",
                "frontend_port": "FRONTEND_PORT",
                "log_level": "LOG_LEVEL",
                "log_file": "LOG_FILE",
                "max_tokens": "MAX_TOKENS",
                "temperature": "TEMPERATURE",
                "max_tool_calls": "MAX_TOOL_CALLS",
                "request_timeout": "REQUEST_TIMEOUT",
                "tool_timeout": "TOOL_TIMEOUT",
            }

            env_loaded = False
            for attr, env_var in env_mapping.items():
                env_value = os.getenv(env_var)
                if env_value:
                    if attr in [
                        "api_port",
                        "frontend_port",
                        "max_tokens",
                        "max_tool_calls",
                        "request_timeout",
                        "tool_timeout",
                    ]:
                        env_value = int(env_value)
                    elif attr == "temperature":
                        env_value = float(env_value)
                    elif attr == "api_reload":
                        env_value = env_value.lower() in ("true", "1", "yes")

                    setattr(self._config, attr, env_value)
                    env_loaded = True

            if env_loaded:
                self._config.config_source = "environment"
                if self._config.gemini_api_key:
                    self._is_configured = True
                logger.info("Configuration loaded from environment variables")

        except Exception as e:
            logger.error(f"Failed to load from environment: {str(e)}")

    def _save_to_config_file(self):
        """Save current configuration to file."""
        try:
            if not self._config_file_path:
                return

            config_data = asdict(self._config)
            config_data.pop("config_source", None)

            with open(self._config_file_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Configuration saved to: {self._config_file_path}")

        except Exception as e:
            logger.error(f"Failed to save config to file: {str(e)}")

    def create_default_config_files(self):
        """Create default configuration files for different environments."""
        try:
            config_dir = Path(__file__).parent.parent.parent / "config"
            config_dir.mkdir(exist_ok=True)

            dev_config = {
                "environment": "development",
                "gemini_model": "gemini-2.0-flash-exp",
                "mcp_server_url": "http://localhost:5000/sse",
                "transport_type": "sse",
                "api_host": "0.0.0.0",
                "api_port": 8000,
                "api_reload": True,
                "frontend_port": 5002,
                "log_level": "INFO",
                "log_file": None,
                "max_tokens": 3000,
                "temperature": 1.0,
                "max_tool_calls": 10,
                "request_timeout": 120,
                "tool_timeout": 60,
            }

            prod_config = dev_config.copy()
            prod_config.update(
                {
                    "environment": "production",
                    "api_reload": False,
                    "log_level": "WARNING",
                    "max_tokens": 2000,
                    "temperature": 0.2,
                    "max_tool_calls": 5,
                    "request_timeout": 60,
                    "tool_timeout": 30,
                }
            )

            dev_file = config_dir / "development.json"
            prod_file = config_dir / "production.json"

            if not dev_file.exists():
                with open(dev_file, "w", encoding="utf-8") as f:
                    json.dump(dev_config, f, indent=2, ensure_ascii=False)
                logger.info(f"Created development config: {dev_file}")

            if not prod_file.exists():
                with open(prod_file, "w", encoding="utf-8") as f:
                    json.dump(prod_config, f, indent=2, ensure_ascii=False)
                logger.info(f"Created production config: {prod_file}")

        except Exception as e:
            logger.error(f"Failed to create default config files: {str(e)}")


# Global instances and functions
_config_manager: Optional[ConfigManager] = None
_manager_lock = Lock()


def get_config_manager() -> ConfigManager:
    """Get global config manager instance."""
    global _config_manager
    with _manager_lock:
        if _config_manager is None:
            _config_manager = ConfigManager()
            _config_manager.create_default_config_files()
        return _config_manager


def load_config(environment: str = "development") -> MCPClientConfig:
    """Load configuration for specified environment."""
    manager = get_config_manager()
    return manager.load_config(environment)


def get_current_config() -> MCPClientConfig:
    """Get current configuration."""
    manager = get_config_manager()
    return manager.get_config()


def update_config(updates: Dict[str, Any], save_to_file: bool = True) -> bool:
    """Update current configuration."""
    manager = get_config_manager()
    return manager.update_config(updates, save_to_file)


def is_configured() -> bool:
    """Check if system is properly configured."""
    manager = get_config_manager()
    return manager.is_configured()


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Create global settings instance
settings = get_settings()

# Setup logging if possible
try:
    from ..shared.logger import setup_logging

    setup_logging(log_level=settings.log_level, log_file=settings.log_file)
except ImportError:
    import logging

    logging.basicConfig(level=logging.INFO)


# Export everything
__all__ = [
    "MCPClientConfig",
    "Settings",
    "ConfigManager",
    "settings",
    "get_settings",
    "get_config_manager",
    "get_current_config",
    "update_config",
    "is_configured",
    "load_config",
]
