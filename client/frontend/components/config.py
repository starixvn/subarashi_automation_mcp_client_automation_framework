import streamlit as st
import time
from typing import Dict, Any
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from client.frontend.utils.api_client import get_api_client, run_async

CONFIG_CACHE_TIMEOUT = 60

def get_cached_config_status():
    """Get config status with optimized caching."""
    current_time = time.time()
    
    if hasattr(st.session_state, 'config_status_cache'):
        cache_time, cached_data = st.session_state.config_status_cache
        if current_time - cache_time < CONFIG_CACHE_TIMEOUT:
            return cached_data
    
    try:
        api_client = get_api_client()
        status = run_async(api_client.get_config_status())
        st.session_state.config_status_cache = (current_time, status)
        return status
    except Exception as e:
        if hasattr(st.session_state, 'config_status_cache'):
            return st.session_state.config_status_cache[1]
        return None

def get_cached_current_config():
    """Get current config with optimized caching."""
    current_time = time.time()
    
    if hasattr(st.session_state, 'current_config_cache'):
        cache_time, cached_data = st.session_state.current_config_cache
        if current_time - cache_time < CONFIG_CACHE_TIMEOUT:
            return cached_data
    
    try:
        api_client = get_api_client()
        config = run_async(api_client.get_current_config())
        st.session_state.current_config_cache = (current_time, config)
        return config
    except Exception as e:
        if hasattr(st.session_state, 'current_config_cache'):
            return st.session_state.current_config_cache[1]
        return None

def clear_config_caches():
    """Clear config-related caches only when needed."""
    current_time = time.time()
    
    if hasattr(st.session_state, 'config_status_cache'):
        cache_time, _ = st.session_state.config_status_cache
        if current_time - cache_time > 300:  # 5 minutes
            delattr(st.session_state, 'config_status_cache')
    
    if hasattr(st.session_state, 'current_config_cache'):
        cache_time, _ = st.session_state.current_config_cache
        if current_time - cache_time > 300:  # 5 minutes
            delattr(st.session_state, 'current_config_cache')
    
    if hasattr(st.session_state, 'health_cache'):
        cache_time, _ = st.session_state.health_cache
        if current_time - cache_time > 300:  # 5 minutes
            delattr(st.session_state, 'health_cache')

def render_configuration_page():
    """Render the main configuration page."""
    st.title("⚙️ MCP Client Configuration")

    config_status = get_cached_config_status()

    if config_status and config_status.get("is_configured"):
        st.success("✅ System is configured and ready!")

        render_service_status()

        st.divider()

        render_current_configuration()

        st.divider()

        with st.expander("🔧 Advanced Configuration", expanded=False):
            render_configuration_form()
    else:
        st.warning("⚠️ System needs configuration to function properly")
        render_configuration_form()

def render_service_status():
    """Render current service status."""
    st.subheader("🏥 Service Status")

    try:
        api_client = get_api_client()
        health = run_async(api_client.health_check())

        if health:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write("**Backend API**")
                if health.get("status") == "healthy":
                    st.success("✅ Healthy")
                else:
                    st.warning(f"⚠️ {health.get('status', 'Unknown')}")

            with col2:
                st.write("**MCP Server**")
                if health.get("mcp_connected"):
                    st.success("✅ Connected")
                    st.metric("Tools", health.get("tools_available", 0))
                else:
                    st.error("❌ Disconnected")

            with col3:
                st.write("**AI Service**")
                chat_status = run_async(api_client.get_chat_status())
                if chat_status and chat_status.get("ai_configured", False):
                    st.success("✅ Configured")
                    st.write(f"Model: {health.get('gemini_model', 'Unknown')}")
                else:
                    st.error("❌ Not Configured")

            if health.get("capabilities"):
                with st.expander("📋 Server Capabilities", expanded=False):
                    caps = health["capabilities"]
                    
                    if "tools" in caps:
                        tools_info = caps["tools"]
                        if isinstance(tools_info, dict):
                            list_changed = tools_info.get("listChanged", False)
                            st.write(f"🛠️ **Tools**: ✅ Available (Live updates: {'✅' if list_changed else '❌'})")
                        else:
                            st.write("🛠️ **Tools**: ✅ Available")
                    
                    if "prompts" in caps:
                        prompts_info = caps["prompts"]
                        if isinstance(prompts_info, dict):
                            list_changed = prompts_info.get("listChanged", False)
                            st.write(f"📝 **Prompts**: ✅ Available (Live updates: {'✅' if list_changed else '❌'})")
                        else:
                            st.write("📝 **Prompts**: ✅ Available")
                    
                    if "resources" in caps:
                        resources_info = caps["resources"]
                        if isinstance(resources_info, dict):
                            subscribe = resources_info.get("subscribe", False)
                            list_changed = resources_info.get("listChanged", False)
                            subscribe_text = "✅" if subscribe else "❌"
                            updates_text = "✅" if list_changed else "❌"
                            st.write(f"📁 **Resources**: ✅ Available (Subscribe: {subscribe_text}, Live updates: {updates_text})")
                        else:
                            st.write("📁 **Resources**: ✅ Available")
                    
                    if "logging" in caps:
                        st.write("📊 **Logging**: ✅ Available")
                    
                    if "experimental" in caps:
                        st.write("🧪 **Experimental**: ✅ Available")
                    
                    known_caps = {"tools", "prompts", "resources", "logging", "experimental"}
                    other_caps = set(caps.keys()) - known_caps
                    if other_caps:
                        for cap in other_caps:
                            st.write(f"⚡ **{cap.title()}**: ✅ Available")

            col1, col2, col3 = st.columns(3)
            with col2:
                if st.button(
                    "🔄 Reconfigure Services", 
                    help="Manually reconfigure all services",
                    key="reconfigure_services_config"
                ):
                    reconfigure_services()
            
            if not health.get("mcp_connected"):
                with col1:
                    if st.button(
                        "🔗 Reconnect MCP", 
                        help="Force reconnect to MCP server",
                        type="primary",
                        key="reconnect_mcp_config_disconnected"
                    ):
                        reconnect_mcp_server()
            else:
                with col3:
                    if st.button(
                        "🔗 Reconnect MCP", 
                        help="Force reconnect to MCP server",
                        key="reconnect_mcp_config_connected"
                    ):
                        reconnect_mcp_server()

        else:
            st.error("❌ Cannot connect to backend")

    except Exception as e:
        st.error(f"❌ Service status error: {str(e)}")


def reconfigure_services():
    """Manually reconfigure services."""
    with st.spinner("Reconfiguring services..."):
        try:
            api_client = get_api_client()
            result = run_async(api_client.reconfigure_services())

            if result and result.get("success"):
                if hasattr(st.session_state, 'health_cache'):
                    delattr(st.session_state, 'health_cache')
                if hasattr(st.session_state, 'tools_cache'):
                    delattr(st.session_state, 'tools_cache')
                    
                st.success("✅ Services reconfigured successfully!")
                st.rerun()
            else:
                error_msg = (
                    result.get("error", "Unknown error")
                    if result
                    else "Reconfiguration failed"
                )
                st.error(f"❌ Reconfiguration failed: {error_msg}")

        except Exception as e:
            st.error(f"❌ Reconfiguration error: {str(e)}")


def reconnect_mcp_server():
    """Force reconnect to MCP server."""
    with st.spinner("Reconnecting to MCP server..."):
        try:
            api_client = get_api_client()
            result = run_async(api_client.reconnect_mcp())

            if result and result.get("success"):
                if hasattr(st.session_state, 'health_cache'):
                    delattr(st.session_state, 'health_cache')
                if hasattr(st.session_state, 'tools_cache'):
                    delattr(st.session_state, 'tools_cache')
                
                st.success("✅ MCP server reconnected successfully!")
                
                if result.get("tools_count", 0) > 0:
                    st.info(f"🛠️ Found {result['tools_count']} tools available")
                
                if result.get("capabilities"):
                    st.info(f"📋 Server capabilities: {', '.join(result['capabilities'].keys())}")
                
                st.rerun()
            else:
                error_msg = (
                    result.get("error", "Unknown error")
                    if result
                    else "Reconnection failed"
                )
                st.error(f"❌ MCP reconnection failed: {error_msg}")
                
                st.markdown("""
                **💡 Troubleshooting Tips:**
                - Check if the MCP server URL is correct
                - Verify the server is running and accessible
                - Try different transport type (SSE/WebSocket/Stdio)
                - Check server logs for connection errors
                """)

        except Exception as e:
            st.error(f"❌ MCP reconnection error: {str(e)}")


def render_configuration_form():
    """Render the configuration form."""
    st.subheader("🔧 Configure System")

    current_config = get_cached_current_config()
    config_data = current_config.get("config", {}) if current_config else {}

    with st.form("config_form"):
        st.markdown("### 🤖 AI Configuration")

        api_key = st.text_input(
            "Gemini API Key *",
            type="password",
            help="Your Google Gemini API key (required)",
            placeholder="Enter your Gemini API key...",
        )

        model_options = [
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
        gemini_model = st.selectbox(
            "Gemini Model",
            options=model_options,
            index=model_options.index(
                config_data.get("gemini_model", model_options[0])
            ),
            help="Choose the Gemini model to use",
        )

        st.markdown("### 🔗 MCP Server Configuration")

        col1, col2 = st.columns([3, 1])
        
        with col1:
            mcp_url = st.text_input(
                "MCP Server URL",
                value=config_data.get("mcp_server_url", "http://localhost:5000/sse"),
                help="URL of your MCP server",
            )
        
        with col2:
            transport_options = ["sse", "websocket", "stdio"]
            transport_type = st.selectbox(
                "Transport Type",
                options=transport_options,
                index=transport_options.index(config_data.get("transport_type", "sse")),
                help="Communication protocol to use"
            )

        st.markdown("### 🎛️ AI Parameters")

        col1, col2 = st.columns(2)

        with col1:
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=float(config_data.get("temperature", 0.2)),
                step=0.1,
                help="Controls randomness in AI responses",
            )

            max_tokens = st.number_input(
                "Max Tokens",
                min_value=100,
                max_value=10000,
                value=int(config_data.get("max_tokens", 2000)),
                step=100,
                help="Maximum tokens for AI responses",
            )

        with col2:
            max_tool_calls = st.number_input(
                "Max Tool Calls",
                min_value=1,
                max_value=20,
                value=int(config_data.get("max_tool_calls", 5)),
                help="Maximum tool call iterations",
            )

            save_to_file = st.checkbox(
                "Save to Configuration File",
                value=True,
                help="Save configuration for future use",
            )

        submitted = st.form_submit_button("💾 Save Configuration", type="primary")

        if submitted:
            if not api_key:
                st.error("❌ Gemini API Key is required!")
                return

            config_updates = {
                "gemini_api_key": api_key,
                "gemini_model": gemini_model,
                "mcp_server_url": mcp_url,
                "transport_type": transport_type,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "max_tool_calls": max_tool_calls,
                "save_to_file": save_to_file,
            }

            save_configuration(config_updates)


def render_current_configuration():
    """Render current configuration display."""
    st.subheader("📋 Current Configuration")

    config = get_cached_current_config()

    if config and config.get("success"):
        config_data = config["config"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Environment", config_data.get("environment", "Unknown"))
            st.metric("Config Source", config.get("config_source", "Unknown"))

        with col2:
            st.metric("AI Model", config_data.get("gemini_model", "Unknown"))
            st.metric("Temperature", f"{config_data.get('temperature', 0):.1f}")

        with col3:
            st.metric("Max Tokens", config_data.get("max_tokens", 0))
            st.metric("Max Tool Calls", config_data.get("max_tool_calls", 0))

        st.text(f"🔗 MCP Server: {config_data.get('mcp_server_url', 'Not set')}")
        st.text(f"🚀 Transport: {config_data.get('transport_type', 'sse')}")
        st.text(
            f"🔑 API Key: {'✅ Configured' if config_data.get('has_api_key') else '❌ Not set'}"
        )
    else:
        st.error("❌ Failed to load current configuration")


def get_configuration_status():
    """Legacy function - use get_cached_config_status instead."""
    return get_cached_config_status()


def get_current_configuration():
    """Legacy function - use get_cached_current_config instead."""
    return get_cached_current_config()


def save_configuration(config_data: Dict[str, Any]):
    """Save configuration via API."""
    with st.spinner("Saving configuration..."):
        try:
            api_client = get_api_client()
            result = run_async(api_client.update_config(config_data))

            if result and result.get("success"):
                if hasattr(st.session_state, 'config_status_cache'):
                    delattr(st.session_state, 'config_status_cache')
                if hasattr(st.session_state, 'current_config_cache'):
                    delattr(st.session_state, 'current_config_cache')
                
                st.success("✅ Configuration saved successfully!")

                if result.get("services_reconfigured"):
                    st.success("✅ Services automatically reconfigured!")
                    if hasattr(st.session_state, 'health_cache'):
                        delattr(st.session_state, 'health_cache')
                else:
                    st.warning("⚠️ Services may need manual reconfiguration")
                    if st.button("🔄 Reconfigure Services Now", key="reconfigure_services_now_save"):
                        reconfigure_services()

                st.balloons()
                st.rerun()
            else:
                error_msg = (
                    result.get("error", "Unknown error")
                    if result
                    else "API call failed"
                )
                st.error(f"❌ Failed to save configuration: {error_msg}")

        except Exception as e:
            st.error(f"❌ Configuration save error: {str(e)}")


def reset_configuration():
    """Reset configuration to defaults."""
    with st.spinner("Resetting configuration..."):
        try:
            api_client = get_api_client()
            result = run_async(api_client.reset_config())

            if result and result.get("success"):
                clear_config_caches()
                
                st.success("✅ Configuration reset successfully!")
                st.rerun()
            else:
                error_msg = (
                    result.get("error", "Unknown error") if result else "Reset failed"
                )
                st.error(f"❌ Failed to reset configuration: {error_msg}")

        except Exception as e:
            st.error(f"❌ Configuration reset error: {str(e)}")


def render_config_status_badge():
    """Render a configuration status badge for sidebar."""
    status = get_cached_config_status()

    if status:
        if status.get("is_configured"):
            st.success("✅ Configured")
        else:
            st.error("❌ Needs Config")
            missing = status.get("missing_fields", [])
            if missing:
                st.write(f"Missing: {', '.join(missing)}")
    else:
        st.warning("⚠️ Status Unknown")
