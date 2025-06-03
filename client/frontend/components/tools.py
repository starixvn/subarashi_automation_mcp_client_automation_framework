import streamlit as st
import json
import time
from typing import Dict, Any, List
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from client.frontend.utils.api_client import get_api_client, run_async

TOOLS_CACHE_TIMEOUT = 120

def get_cached_tools_data():
    """Get tools data with caching to reduce API calls."""
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


def render_tools_overview():
    """Render tools overview section with optimized caching."""
    st.subheader("🛠️ Available Tools")

    try:
        tools_response = get_cached_tools_data()

        if not tools_response or not tools_response.get("success"):
            error_msg = tools_response.get('error', 'Unknown error') if tools_response else 'Failed to load tools'
            st.error(f"❌ Failed to load tools: {error_msg}")
            return

        tools = tools_response.get("tools", [])

        if not tools:
            st.warning("⚠️ No tools available")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tools", len(tools))
        with col2:
            if st.button("🔄 Refresh Tools", key="refresh_tools_overview"):
                refresh_tools()
        with col3:
            if st.button("🔧 Test Connection", key="test_connection_overview"):
                test_connection()
                
        if hasattr(st.session_state, 'tools_cache'):
            cache_age = int(time.time() - st.session_state.tools_cache[0])
            st.caption(f"Tools cache: {cache_age}s (auto-refresh: {TOOLS_CACHE_TIMEOUT}s)")

        categorized_tools = _categorize_tools(tools)

        for category, category_tools in categorized_tools.items():
            with st.expander(
                f"📂 {category} ({len(category_tools)} tools)", expanded=True
            ):
                for tool in category_tools:
                    render_tool_card(tool)

    except Exception as e:
        st.error(f"❌ Error loading tools: {str(e)}")


def render_tool_card(tool: Dict[str, Any]):
    """Render individual tool card."""
    with st.container():
        st.markdown(f"### 🔧 {tool['name']}")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**Description:** {tool.get('description', 'No description')}")

            params = tool.get("parameters", {})
            if params and isinstance(params, dict) and params.get("properties"):
                st.write("**Parameters:**")
                for param_name, param_info in params["properties"].items():
                    param_type = param_info.get("type", "unknown")
                    param_desc = param_info.get("description", "No description")
                    required = param_name in params.get("required", [])
                    req_indicator = " **(required)**" if required else ""
                    st.write(
                        f"  • `{param_name}` ({param_type}){req_indicator}: {param_desc}"
                    )
            else:
                st.write("**Parameters:** None")

        with col2:
            if st.button(f"🚀 Test {tool['name']}", key=f"test_{tool['name']}"):
                test_tool_dialog(tool)

        st.divider()


def test_tool_dialog(tool: Dict[str, Any]):
    """Show tool testing dialog."""
    st.subheader(f"🧪 Test Tool: {tool['name']}")

    params = tool.get("parameters", {})
    tool_args = {}

    if params and isinstance(params, dict) and params.get("properties"):
        st.write("**Enter tool parameters:**")

        for param_name, param_info in params["properties"].items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            required = param_name in params.get("required", [])

            if param_type == "string":
                value = st.text_input(
                    f"{param_name} {'*' if required else ''}",
                    help=param_desc,
                    key=f"param_{tool['name']}_{param_name}",
                )
                if value:
                    tool_args[param_name] = value

            elif param_type in ["integer", "number"]:
                value = st.number_input(
                    f"{param_name} {'*' if required else ''}",
                    help=param_desc,
                    key=f"param_{tool['name']}_{param_name}",
                )
                tool_args[param_name] = value

            elif param_type == "boolean":
                value = st.checkbox(
                    f"{param_name} {'*' if required else ''}",
                    help=param_desc,
                    key=f"param_{tool['name']}_{param_name}",
                )
                tool_args[param_name] = value

            else:
                value = st.text_area(
                    f"{param_name} {'*' if required else ''} (JSON)",
                    help=f"{param_desc} (Enter as JSON)",
                    key=f"param_{tool['name']}_{param_name}",
                )
                if value:
                    try:
                        tool_args[param_name] = json.loads(value)
                    except json.JSONDecodeError:
                        st.error(f"Invalid JSON for {param_name}")
                        return

    if st.button(f"🚀 Execute {tool['name']}", key=f"execute_{tool['name']}"):
        execute_tool(tool["name"], tool_args)


def execute_tool(tool_name: str, tool_args: Dict[str, Any]):
    """Execute a tool and display results."""
    with st.spinner(f"Executing {tool_name}..."):
        try:
            api_client = get_api_client()
            result = run_async(api_client.call_tool(tool_name, tool_args))

            if result.get("success"):
                st.success(f"✅ Tool {tool_name} executed successfully!")

                if result.get("result"):
                    st.subheader("📋 Tool Output")
                    st.text_area(
                        "Result", value=result["result"], height=200, disabled=True
                    )

                if result.get("is_error"):
                    st.warning("⚠️ Tool reported an error condition")

            else:
                st.error(f"❌ Tool execution failed: {result.get('error')}")

        except Exception as e:
            st.error(f"❌ Execution error: {str(e)}")


def refresh_tools():
    """Refresh tools from server with cache clearing."""
    with st.spinner("Refreshing tools..."):
        try:
            if hasattr(st.session_state, 'tools_cache'):
                delattr(st.session_state, 'tools_cache')
                
            api_client = get_api_client()
            result = run_async(api_client.refresh_tools())

            if result.get("success"):
                st.success(f"✅ Refreshed {result.get('count', 0)} tools")
            else:
                st.error(f"❌ Failed to refresh: {result.get('error')}")

        except Exception as e:
            st.error(f"❌ Refresh error: {str(e)}")

    st.rerun()


def test_connection():
    """Test MCP connection."""
    with st.spinner("Testing connection..."):
        try:
            api_client = get_api_client()
            result = run_async(api_client.get_connection_status())

            if result.get("connected"):
                st.success(
                    f"✅ Connected to MCP server ({result.get('tools_count', 0)} tools)"
                )
            else:
                st.error(f"❌ Not connected: {result.get('error', 'Unknown error')}")

        except Exception as e:
            st.error(f"❌ Connection test failed: {str(e)}")


def _categorize_tools(tools: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize tools by name patterns."""
    categories = {}

    for tool in tools:
        name = tool["name"].lower()

        if any(
            keyword in name
            for keyword in ["browser", "web", "navigate", "click", "page"]
        ):
            category = "🌐 Web & Browser"
        elif any(keyword in name for keyword in ["file", "read", "write", "directory"]):
            category = "📁 File System"
        elif any(keyword in name for keyword in ["search", "find", "query"]):
            category = "🔍 Search"
        elif any(keyword in name for keyword in ["api", "http", "request"]):
            category = "🔌 API & Network"
        elif any(keyword in name for keyword in ["data", "process", "analyze"]):
            category = "📊 Data Processing"
        else:
            category = "🔧 General Tools"

        if category not in categories:
            categories[category] = []
        categories[category].append(tool)

    return dict(sorted(categories.items()))


def render_tool_testing_section():
    """Render tool testing section with optimized caching."""
    st.subheader("🧪 Tool Testing")

    try:
        tools_response = get_cached_tools_data()

        if not tools_response or not tools_response.get("success"):
            st.error("❌ Cannot load tools for testing")
            return

        tools = tools_response.get("tools", [])
        if not tools:
            st.warning("⚠️ No tools available for testing")
            return

        tool_names = [tool["name"] for tool in tools]
        selected_tool_name = st.selectbox("Select tool to test:", tool_names, key="tool_testing_select")

        if selected_tool_name:
            selected_tool = next(
                tool for tool in tools if tool["name"] == selected_tool_name
            )
            test_tool_dialog(selected_tool)

    except Exception as e:
        st.error(f"❌ Error in tool testing: {str(e)}")
