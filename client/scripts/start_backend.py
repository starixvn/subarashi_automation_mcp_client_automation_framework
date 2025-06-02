import os
import sys
import traceback
import argparse
from pathlib import Path

client_dir = Path(__file__).parent.parent
project_root = client_dir.parent
sys.path.insert(0, str(project_root))

print(f"🔍 Client dir: {client_dir}")
print(f"🔍 Project root: {project_root}")


def main():
    """Start the FastAPI backend server with environment support."""
    parser = argparse.ArgumentParser(description="Run MCP Backend API")
    parser.add_argument("environment", nargs="?", default="development", 
                       choices=["development", "production", "dev", "prod"],
                       help="Environment to run (default: development)")
    parser.add_argument("--port", type=int, help="Port to run on (overrides config)")
    parser.add_argument("--host", type=str, help="Host to bind to (overrides config)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")
    args = parser.parse_args()
    
    env = "production" if args.environment in ["prod", "production"] else "development"
    os.environ["ENVIRONMENT"] = env
    print(f"🌍 Setting environment: {env}")
    
    try:
        from client.core.config_manager import load_config
        from client.core.config import settings
        from client.shared.logger import setup_logging, get_logger
        
        config = load_config(env)
        settings.refresh_from_config_manager()
        
        print("✅ Imports successful")
    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

    setup_logging()
    logger = get_logger(__name__)

    host = args.host or config.api_host
    port = args.port or config.api_port
    reload = args.reload and env == "development"

    print("🚀 Starting MCP Client FastAPI Backend...")
    print("=" * 60)
    print(f"🌍 Environment: {env}")
    print(f"📁 Config Source: {config.config_source}")
    print(f"🔗 MCP Server: {config.mcp_server_url}")
    print(f"🚂 Transport: {config.transport_type}")
    print(f"🤖 Gemini Model: {config.gemini_model}")
    print(f"🌐 API Host: {host}:{port}")
    print(f"🔄 Auto-reload: {reload}")
    print(f"📊 Max Tokens: {config.max_tokens}")
    print(f"🌡️ Temperature: {config.temperature}")
    print(f"🔧 Max Tool Calls: {config.max_tool_calls}")
    
    if hasattr(config, 'log_file') and config.log_file:
        print(f"📝 Log File: {config.log_file}")
    
    print("=" * 60)
    
    if config.gemini_api_key:
        print("✅ Gemini API Key: Configured")
    else:
        print("⚠️ Gemini API Key: Not configured - Configure via frontend")
    
    print("🔄 Testing imports...")
    try:
        import uvicorn
        print("✅ Uvicorn imported")
    except ImportError as e:
        print(f"❌ Failed to import uvicorn: {e}")
        sys.exit(1)

    try:
        print(f"🚀 Starting uvicorn server in {env} mode...")
        
        uvicorn_config = {
            "app": "client.api.main:app",
            "host": host,
            "port": port,
            "reload": reload,
            "log_level": config.log_level.lower(),
        }
        
        if env == "production":
            uvicorn_config.update({
                "workers": 1,
                "access_log": True,
                "use_colors": False,
                "server_header": False,
                "date_header": False,
            })
        
        logger.info(f"Starting FastAPI server with config: {uvicorn_config}")
        uvicorn.run(**uvicorn_config)

    except KeyboardInterrupt:
        logger.info("👋 Backend stopped by user")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
