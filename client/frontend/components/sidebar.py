import streamlit as st
import time
from typing import Dict, Any
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from client.frontend.utils.api_client import get_api_client, run_async

SIDEBAR_CACHE_TIMEOUT = 90


def get_cached_sidebar_status():
    """Get sidebar status with caching to reduce API calls."""
    current_time = time.time()

    if hasattr(st.session_state, "sidebar_status_cache"):
        cache_time, cached_data = st.session_state.sidebar_status_cache
        if current_time - cache_time < SIDEBAR_CACHE_TIMEOUT:
            return cached_data

    try:
        api_client = get_api_client()
        config_status = run_async(api_client.get_config_status())
        connection_status = run_async(api_client.get_connection_status())
        health = run_async(api_client.health_check())

        combined_status = {
            "config": config_status,
            "connection": connection_status,
            "health": health,
        }

        st.session_state.sidebar_status_cache = (current_time, combined_status)
        return combined_status
    except Exception as e:
        if hasattr(st.session_state, "sidebar_status_cache"):
            return st.session_state.sidebar_status_cache[1]
        return None


def render_sidebar():
    """Render the main sidebar with status and controls."""
    with st.sidebar:
        st.title("⚙️ MCP Client Control")

        render_configuration_status()

        st.divider()

        render_connection_status()

        st.divider()

        render_service_status()

        st.divider()

        render_quick_actions()

        st.divider()

        render_about_section()


def render_configuration_status():
    """Render system configuration status using cached data."""
    st.subheader("🔧 Configuration Status")

    try:
        cached_status = get_cached_sidebar_status()
        if not cached_status:
            st.warning("⚠️ Cannot check status")
            return

        config_status = cached_status.get("config")

        if config_status:
            if config_status.get("is_configured"):
                st.success("✅ System Configured")

                source = config_status.get("config_source", "unknown")
                st.text(f"Source: {source}")

                if config_status.get("has_api_key"):
                    st.success("🔑 API Key Set")
                else:
                    st.error("🔑 API Key Missing")

            else:
                st.error("❌ System Not Configured")
                missing = config_status.get("missing_fields", [])
                if missing:
                    st.write(f"Missing: {', '.join(missing)}")

                if st.button("🔧 Configure System", key="sidebar_config"):
                    st.info("Please go to Configuration tab")

        else:
            st.warning("⚠️ Cannot check config status")

    except Exception as e:
        st.error(f"❌ Config status error: {str(e)}")


def render_connection_status():
    """Render MCP connection status using cached data."""
    st.subheader("🔗 Connection Status")

    try:
        cached_status = get_cached_sidebar_status()
        if not cached_status:
            st.warning("⚠️ Cannot check status")
            return

        status = cached_status.get("connection")

        if status and status.get("connected"):
            st.success("✅ MCP Server Connected")
            st.metric("Tools Available", status.get("tools_count", 0))
            server_url = status.get("server_url", "Unknown")
            st.text(f"Server: {server_url}")
        else:
            st.error("❌ MCP Server Disconnected")
            if status and status.get("error"):
                st.error(f"Error: {status['error']}")

            if st.button("🔄 Reconnect", key="reconnect_btn"):
                reconnect_server()

    except Exception as e:
        st.error(f"❌ Connection check failed: {str(e)}")


def render_service_status():
    """Render overall service status using cached data."""
    st.subheader("🏥 Service Health")

    try:
        cached_status = get_cached_sidebar_status()
        if not cached_status:
            st.warning("⚠️ Cannot check status")
            return

        health = cached_status.get("health")

        if health:
            status = health.get("status", "unknown")
            if status == "healthy":
                st.success("✅ All Services Healthy")
            elif status == "degraded":
                st.warning("⚠️ Services Degraded")
            else:
                st.error(f"❌ Status: {status}")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Version", health.get("version", "Unknown"))
                st.metric("Uptime", health.get("uptime", "Unknown"))

            with col2:
                model = health.get("gemini_model", "Unknown")
                st.write(f"**AI Model:** {model}")
                tools = health.get("tools_available", 0)
                st.write(f"**Tools:** {tools}")

            if hasattr(st.session_state, "sidebar_status_cache"):
                cache_age = int(time.time() - st.session_state.sidebar_status_cache[0])
                st.caption(f"Cache: {cache_age}s (refresh: {SIDEBAR_CACHE_TIMEOUT}s)")

        else:
            st.error("❌ Health check failed")

    except Exception as e:
        st.error(f"❌ Health check error: {str(e)}")


def render_quick_actions():
    """Render quick action buttons with optimized cache management."""
    st.subheader("⚡ Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh Status", key="refresh_status"):
            if hasattr(st.session_state, "sidebar_status_cache"):
                delattr(st.session_state, "sidebar_status_cache")
            st.success("✅ Status refreshed!")
            st.rerun()

        if st.button("🧹 Clear Chat", key="clear_chat_sidebar"):
            clear_chat()

    with col2:
        if st.button("🛠️ Refresh Tools", key="refresh_tools_sidebar"):
            refresh_tools()

        if st.button("🧪 Test Connection", key="test_connection_sidebar"):
            test_connection()


def render_about_section():
    """Render about and help section."""
    st.subheader("ℹ️ About")

    st.markdown(
        """
    **MCP Client v2.0**
    
    🤖 **AI:** Google Gemini  
    🔌 **Protocol:** MCP (SSE)  
    ⚡ **Backend:** FastAPI  
    🎨 **Frontend:** Streamlit  
    
    **Features:**
    - Flexible configuration management
    - Intelligent tool usage
    - Real-time MCP integration  
    - Multi-tool conversations
    - Direct tool testing
    """
    )

    with st.expander("🆘 Help & Support"):
        st.markdown(
            """
        **Getting Started:**
        
        1. **Configure System**: Go to Configuration tab
        2. **Enter API Key**: Add your Gemini API key
        3. **Set Preferences**: Choose model and parameters
        4. **Start Chatting**: Use the chat interface
        
        **Common Issues:**
        
        1. **Not Configured**: Use Configuration tab to set up
        2. **Connection Failed**: Check MCP server is running
        3. **No Tools**: Ensure MCP server has tools configured
        4. **Slow Response**: Check network and server performance
        
        **Quick Fixes:**
        - Use 'Configure System' if not set up
        - Use 'Reconnect' button if connection drops
        - 'Refresh Tools' if tools don't appear
        - 'Clear Chat' to reset conversation
        """
        )


def reconnect_server():
    """Reconnect to MCP server with optimized cache management."""
    with st.spinner("Reconnecting to MCP server..."):
        try:
            api_client = get_api_client()
            result = run_async(api_client.reconnect_server())

            if result.get("success") and result.get("connected"):
                if hasattr(st.session_state, "sidebar_status_cache"):
                    delattr(st.session_state, "sidebar_status_cache")
                if hasattr(st.session_state, "health_cache"):
                    delattr(st.session_state, "health_cache")
                if hasattr(st.session_state, "tools_cache"):
                    delattr(st.session_state, "tools_cache")

                st.success(
                    f"✅ Reconnected! {result.get('tools_count', 0)} tools available"
                )
            else:
                st.error(
                    f"❌ Reconnection failed: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            st.error(f"❌ Reconnection error: {str(e)}")

    st.rerun()


def clear_chat():
    """Clear chat history without affecting other caches."""
    try:
        if "messages" in st.session_state:
            st.session_state.messages = []

        api_client = get_api_client()
        result = run_async(api_client.reset_conversation())

        if result.get("success"):
            st.success("✅ Chat cleared")
        else:
            st.warning("⚠️ Local chat cleared, server reset may have failed")

    except Exception as e:
        st.error(f"❌ Clear chat error: {str(e)}")

    st.rerun()


def refresh_tools():
    """Refresh tools from server with targeted cache clearing."""
    with st.spinner("Refreshing tools..."):
        try:
            if hasattr(st.session_state, "tools_cache"):
                delattr(st.session_state, "tools_cache")

            api_client = get_api_client()
            result = run_async(api_client.refresh_tools())

            if result.get("success"):
                st.success(f"✅ Refreshed {result.get('count', 0)} tools")
            else:
                st.error(f"❌ Refresh failed: {result.get('error')}")

        except Exception as e:
            st.error(f"❌ Refresh error: {str(e)}")

    st.rerun()


def test_connection():
    """Test MCP connection with fresh data."""
    with st.spinner("Testing connection..."):
        try:
            if hasattr(st.session_state, "sidebar_status_cache"):
                delattr(st.session_state, "sidebar_status_cache")

            api_client = get_api_client()
            health = run_async(api_client.health_check())

            if health and health.get("mcp_connected"):
                st.success("✅ Connection test passed")
            else:
                st.error("❌ Connection test failed")

        except Exception as e:
            st.error(f"❌ Connection test error: {str(e)}")


def render_debug_info():
    """Render debug information with caching to reduce API calls."""
    if st.checkbox("🐛 Show Debug Info"):
        st.subheader("🔍 Debug Information")

        try:
            cached_status = get_cached_sidebar_status()

            if cached_status:
                st.write("**Cached Status Response:**")
                st.json(cached_status)

                cache_age = int(time.time() - st.session_state.sidebar_status_cache[0])
                st.write(f"**Cache Age:** {cache_age} seconds")
            else:
                st.error("❌ No cached status available")

            st.write("**Session State (filtered):**")
            filtered_state = {
                key: value
                for key, value in dict(st.session_state).items()
                if not key.endswith("_cache")
                and not "password" in key.lower()
                and not "key" in key.lower()
            }
            st.json(filtered_state)

        except Exception as e:
            st.error(f"Debug info error: {str(e)}")
