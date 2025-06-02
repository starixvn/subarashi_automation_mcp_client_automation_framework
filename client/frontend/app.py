import sys
import os
from pathlib import Path
import time

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from typing import Dict, Any

from client.frontend.components import (
    render_chat_interface,
    render_chat_controls,
    render_chat_status,
    render_conversation_info,
    render_sidebar,
    render_tools_overview,
    render_tool_testing_section,
    render_configuration_page,
    get_configuration_status,
    export_conversation,
    get_conversation_stats,
)
from client.frontend.utils.api_client import get_api_client, run_async

HEALTH_CACHE_TIMEOUT = 60
TOOLS_CACHE_TIMEOUT = 120

def get_cached_health_status():
    """Get health status with optimized caching to reduce API calls."""
    current_time = time.time()
    
    if hasattr(st.session_state, 'health_cache'):
        cache_time, cached_data = st.session_state.health_cache
        if current_time - cache_time < HEALTH_CACHE_TIMEOUT:
            return cached_data
    
    try:
        api_client = get_api_client()
        health = run_async(api_client.health_check())
        
        st.session_state.health_cache = (current_time, health)
        return health
    except Exception as e:
        if hasattr(st.session_state, 'health_cache'):
            return st.session_state.health_cache[1]
        return None

def get_cached_tools_info():
    """Get tools info with optimized caching to reduce API calls."""
    current_time = time.time()
    
    if hasattr(st.session_state, 'tools_cache'):
        cache_time, cached_data = st.session_state.tools_cache
        if current_time - cache_time < TOOLS_CACHE_TIMEOUT:
            return cached_data
    
    try:
        api_client = get_api_client()
        tools_response = run_async(api_client.list_tools())
        
        st.session_state.tools_cache = (current_time, tools_response)
        return tools_response
    except Exception as e:
        if hasattr(st.session_state, 'tools_cache'):
            return st.session_state.tools_cache[1]
        return None

def smart_cache_clear():
    """Smart cache clearing - only clear when actually needed."""
    if hasattr(st.session_state, 'health_cache'):
        cache_time, _ = st.session_state.health_cache
        if time.time() - cache_time > 300:  # 5 minutes
            delattr(st.session_state, 'health_cache')
    
    if hasattr(st.session_state, 'tools_cache'):
        cache_time, _ = st.session_state.tools_cache
        if time.time() - cache_time > 600:  # 10 minutes
            delattr(st.session_state, 'tools_cache')

def initialize_app(): 
    """Initialize application state and check backend connection."""
    if "app_initialized" not in st.session_state:
        st.session_state.app_initialized = False
        st.session_state.backend_connected = False
        st.session_state.system_configured = False
        st.session_state.last_status_check = None

    try:
        api_client = get_api_client()
        health = run_async(api_client.health_check())

        if health and health.get("status") in ["healthy", "degraded"]:
            st.session_state.backend_connected = True
            st.session_state.app_initialized = True

            config_status = get_configuration_status()
            if config_status:
                st.session_state.system_configured = config_status.get(
                    "is_configured", False
                )

        else:
            st.session_state.backend_connected = False

    except Exception as e:
        st.session_state.backend_connected = False
        st.error(f"🚨 **Backend Connection Failed**: {str(e)}")
        st.error("**Debug Info:**")
        
        try:
            api_client = get_api_client()
            backend_url = api_client.base_url
            st.error(f"- Trying to connect to: {backend_url}")
            st.error(f"- Backend should be running on: {backend_url.replace('http://', '')}")
        except:
            st.error(f"- Trying to connect to: Backend API")
            st.error(f"- Backend should be running on: Check configuration")
            
        st.error(f"- Current error: {type(e).__name__}")

        if st.button("🔄 Retry Connection"):
            st.rerun()
        st.stop()


def show_connection_banner():
    """Show connection status banner."""
    if not st.session_state.get("backend_connected", False):
        st.error(
            "🚨 **Not Connected**: FastAPI backend is not accessible. "
            "Please start the backend server."
        )
        if st.button("🔄 Retry Connection"):
            st.rerun()
        st.stop()


def show_configuration_banner():
    """Show configuration status banner."""
    if not st.session_state.get("system_configured", False):
        st.warning(
            "⚙️ **System Configuration Required**: Please configure the system before using chat and tools."
        )
        st.info(
            "Go to the 'Configuration' tab to set up your API keys and preferences."
        )


def setup_page():
    """Setup page configuration and styling."""
    st.set_page_config(
        page_title="MCP Client",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://github.com/your-repo/mcp-client",
            "Report a bug": "https://github.com/your-repo/mcp-client/issues",
            "About": "MCP Client v2.0 - AI Assistant with Tool Integration",
        },
    )

    st.markdown(
        """
        <style>
        .main > div {
            padding-top: 1rem;
        }
        .stApp > header {
            background-color: transparent;
        }
        .stDeployButton {
            display: none;
        }
        footer {
            visibility: hidden;
        }
        .stAlert > div {
            margin-bottom: 1rem;
        }
        div[data-testid="stToolbar"] {
            visibility: hidden;
        }
        
        /* Custom chat styling */
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            display: flex;
            flex-direction: column;
        }
        
        .user-message {
            background-color: #f0f2f6;
            margin-left: 20%;
        }
        
        .assistant-message {
            background-color: #e8f4f8;
            margin-right: 20%;
        }
        
        /* Status indicators */
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-connected {
            background-color: #00ff00;
        }
        
        .status-disconnected {
            background-color: #ff0000;
        }
        
        .status-warning {
            background-color: #ffaa00;
        }
        
        /* Configuration warning */
        .config-warning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    setup_page()
    initialize_app()
    show_connection_banner()

    render_sidebar()

    if st.session_state.get("system_configured", False):
        config_tab, main_tab, tools_tab, testing_tab = st.tabs(
            [
                "⚙️ Configuration",
                "💬 Chat Assistant",
                "🛠️ Tools Overview",
                "🧪 Tool Testing",
            ]
        )
    else:
        config_tab, main_tab, tools_tab, testing_tab = st.tabs(
            [
                "⚙️ Configuration",
                "💬 Chat Assistant",
                "🛠️ Tools Overview",
                "🧪 Tool Testing",
            ]
        )

    with config_tab:
        render_configuration_tab()

    with main_tab:
        if st.session_state.get("system_configured", False):
            render_main_chat_tab()
        else:
            show_configuration_required_message("chat")

    with tools_tab:
        if st.session_state.get("system_configured", False):
            render_tools_tab()
        else:
            show_configuration_required_message("tools")

    with testing_tab:
        if st.session_state.get("system_configured", False):
            render_testing_tab()
        else:
            show_configuration_required_message("testing")

    render_footer()


def render_configuration_tab():
    """Render the configuration tab."""
    render_configuration_page()


def show_configuration_required_message(feature: str):
    """Show message that configuration is required."""
    st.warning(f"⚙️ **Configuration Required for {feature.title()}**")
    st.info(
        "Please configure the system in the Configuration tab before using this feature."
    )

    feature_descriptions = {
        "chat": "Enable AI-powered conversations with tool integration",
        "tools": "Manage and explore available MCP tools",
        "testing": "Test individual tools directly",
    }

    st.markdown(
        f"**This feature will allow you to:** {feature_descriptions.get(feature, 'Use this functionality')}"
    )

    if st.button(f"🔧 Go to Configuration", key=f"goto_config_{feature}"):
        st.info("👆 Please click on the Configuration tab above to configure the system")


def render_main_chat_tab():
    """Render the main chat interface tab."""
    show_configuration_banner()

    render_chat_interface()

    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])

    with col1:
        render_chat_controls()

    with col2:
        st.subheader("💬 Chat Status")
        render_chat_status()
        
        st.divider()
        
        if st.button("📥 Export Chat", help="Export conversation to text", key="export_chat_main"):
            export_text = export_conversation()
            stats = get_conversation_stats()
            
            if stats.get("total_messages", 0) > 0:
                st.download_button(
                    label="💾 Download",
                    data=export_text,
                    file_name=f"mcp_chat_{time.strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    key="download_chat_main"
                )
                
                st.metric("Messages", stats["total_messages"])
                st.metric("Tools Used", stats["tools_used"])
            else:
                st.info("No conversation to export")

        st.divider()

        render_conversation_info()


def render_tools_tab():
    """Render the tools overview tab."""
    show_configuration_banner()

    st.header("🛠️ MCP Tools Overview")

    col1, col2 = st.columns([3, 1])

    with col1:
        render_tools_overview()

    with col2:
        st.subheader("ℹ️ Tools Info")
        show_tools_statistics()


def render_testing_tab():
    """Render the tool testing tab."""
    show_configuration_banner()

    st.header("🧪 Direct Tool Testing")
    st.markdown(
        "Use this section to test individual tools directly without going through the AI assistant."
    )

    render_tool_testing_section()


def show_quick_status():
    """Show quick status information with caching."""
    st.subheader("📊 Status")

    health = get_cached_health_status()
    
    if health:
        if health.get("status") == "healthy":
            st.success("✅ Backend Healthy")
        else:
            st.warning(f"⚠️ Backend: {health.get('status', 'Unknown')}")

        if health.get("mcp_connected"):
            st.success("✅ MCP Connected")
            st.metric("Tools", health.get("tools_available", 0))
        else:
            st.error("❌ MCP Disconnected")

        model = health.get("gemini_model", "Unknown")
        st.text(f"🤖 AI: {model}")
        
        if hasattr(st.session_state, 'health_cache'):
            cache_age = int(time.time() - st.session_state.health_cache[0])
            st.caption(f"Data age: {cache_age}s")
    else:
        st.error("❌ Health check failed")


def show_quick_actions():
    """Show quick action buttons with optimized cache management."""
    st.subheader("⚡ Quick Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh Data", help="Refresh status data", key="refresh_data_main"):
            smart_cache_clear()
            st.success("✅ Cache refreshed!")
            st.rerun()

        if st.button("🧹 Clear Chat", help="Clear chat history", key="clear_chat_main"):
            if "messages" in st.session_state:
                st.session_state.messages = []
            st.success("✅ Chat cleared!")
            st.rerun()

    with col2:
        if st.button("🔗 Reconnect MCP", help="Force reconnect to MCP server", key="reconnect_mcp_main"):
            try:
                api_client = get_api_client()
                with st.spinner("Reconnecting..."):
                    result = run_async(api_client.reconnect_server())
                
                if hasattr(st.session_state, 'health_cache'):
                    delattr(st.session_state, 'health_cache')
                if hasattr(st.session_state, 'tools_cache'):
                    delattr(st.session_state, 'tools_cache')
                    
                if result.get("success"):
                    st.success("✅ Reconnected!")
                else:
                    st.error(f"❌ Reconnect failed: {result.get('error')}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            st.rerun()

        if st.button("🧪 Test Health", help="Test backend connection", key="test_health_main"):
            try:
                if hasattr(st.session_state, 'health_cache'):
                    delattr(st.session_state, 'health_cache')
                    
                api_client = get_api_client()
                with st.spinner("Testing..."):
                    result = run_async(api_client.health_check())
                if result and result.get("status") == "healthy":
                    st.success("✅ Test passed!")
                else:
                    st.error("❌ Test failed!")
            except Exception as e:
                st.error(f"❌ Test error: {str(e)}")


def show_tools_statistics():
    """Show tools statistics with optimized caching."""
    tools_response = get_cached_tools_info()
    
    if tools_response and tools_response.get("success"):
        tools = tools_response.get("tools", [])

        st.metric("Total Tools", len(tools))

        categories = {}
        for tool in tools:
            name = tool["name"].lower()
            if "browser" in name or "web" in name:
                cat = "Web"
            elif "file" in name or "directory" in name:
                cat = "File"
            elif "search" in name:
                cat = "Search"
            elif "api" in name:
                cat = "API"
            else:
                cat = "Other"

            categories[cat] = categories.get(cat, 0) + 1

        st.subheader("📈 Categories")
        for category, count in categories.items():
            st.text(f"{category}: {count}")
            
        if hasattr(st.session_state, 'tools_cache'):
            cache_age = int(time.time() - st.session_state.tools_cache[0])
            st.caption(f"Cache age: {cache_age}s (auto-refresh: {TOOLS_CACHE_TIMEOUT}s)")

    else:
        st.error("❌ Cannot load tools")


def render_footer():
    """Render application footer."""
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**MCP Client v2.0**")
        st.markdown("Powered by Google Gemini")

    with col2:
        st.markdown("**Tech Stack:**")
        st.markdown("FastAPI • Streamlit • MCP")

    with col3:
        st.markdown("**Status:**")
        if st.session_state.get("backend_connected"):
            if st.session_state.get("system_configured"):
                st.markdown("🟢 Ready")
            else:
                st.markdown("🟡 Needs Config")
        else:
            st.markdown("🔴 Disconnected")


if __name__ == "__main__":
    main()
