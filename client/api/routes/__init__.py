from .chat import router as chat_router
from .config_api import router as config_router
from .health import router as health_router
from .tools import router as tools_router
from .prompts import router as prompts_router
from .resources import router as resources_router

__all__ = [
    "chat_router",
    "config_router", 
    "health_router",
    "tools_router",
    "prompts_router",
    "resources_router",
]
