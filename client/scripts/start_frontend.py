import os
import sys
import subprocess
import argparse
from pathlib import Path

client_dir = Path(__file__).parent.parent
project_root = client_dir.parent
sys.path.insert(0, str(project_root))


def main():
    """Start the Streamlit frontend with environment support."""
    parser = argparse.ArgumentParser(description="Run MCP Frontend")
    parser.add_argument(
        "environment",
        nargs="?",
        default="development",
        choices=["development", "production", "dev", "prod"],
        help="Environment to run (default: development)",
    )
    parser.add_argument("--port", type=int, help="Port to run on (overrides config)")
    parser.add_argument("--host", type=str, help="Host to bind to (overrides config)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()

    env = "production" if args.environment in ["prod", "production"] else "development"

    os.environ["ENVIRONMENT"] = env
    print(f"🌍 Setting environment: {env}")

    try:
        from client.core.core_config import load_config, settings
        from client.shared.logger import setup_logging, get_logger

        config = load_config(env)
        settings.refresh_from_config_manager()

    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        sys.exit(1)

    setup_logging()
    logger = get_logger(__name__)
    frontend_port = args.port or settings.frontend_port
    frontend_host = args.host or "localhost"
    headless = args.headless or (env == "production")

    print("🚀 Starting MCP Client Streamlit Frontend...")
    print(f"🌍 Environment: {env}")
    print(f"🌐 Frontend: http://{frontend_host}:{frontend_port}")
    print(f"🔗 Backend: http://{settings.api_host}:{settings.api_port}")
    print(f"📊 Headless mode: {headless}")
    print("=" * 60)

    backend_available = check_backend_availability(settings, logger, env)

    if not backend_available and env == "development":
        choice = (
            input("\n❓ Backend not available. Continue anyway? (y/N): ")
            .strip()
            .lower()
        )
        if choice not in ["y", "yes"]:
            logger.info("👋 Frontend startup cancelled")
            sys.exit(0)
    elif not backend_available and env == "production":
        logger.warning("⚠️ Backend not available, but continuing in production mode")

    try:
        frontend_dir = client_dir / "frontend"
        app_path = frontend_dir / "app.py"

        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(frontend_port),
            "--server.address",
            frontend_host,
            "--server.headless",
            str(headless).lower(),
        ]

        if env == "production":
            cmd.extend(
                [
                    "--server.enableCORS",
                    "false",
                    "--server.enableXsrfProtection",
                    "true",
                    "--browser.gatherUsageStats",
                    "false",
                ]
            )

        logger.info(f"🎨 Starting Streamlit frontend in {env} mode...")
        logger.info(f"📋 Command: {' '.join(cmd)}")
        subprocess.run(cmd)

    except KeyboardInterrupt:
        logger.info("👋 Frontend stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start frontend: {str(e)}")
        sys.exit(1)


def check_backend_availability(settings, logger, env):
    """Check if backend is available without blocking."""
    try:
        import httpx

        backend_url = f"http://localhost:{settings.api_port}/api/v1/health/health"
        response = httpx.get(backend_url, timeout=5.0)

        if response.status_code == 200:
            logger.info("✅ Backend is running")
            return True
        else:
            logger.warning(f"⚠️ Backend responded with status {response.status_code}")
            return False

    except Exception as e:
        logger.warning(f"⚠️ Cannot reach backend: {str(e)}")
        if env == "development":
            logger.warning(
                "💡 Start backend first: python -m client.scripts.start_backend"
            )
        return False


if __name__ == "__main__":
    main()
