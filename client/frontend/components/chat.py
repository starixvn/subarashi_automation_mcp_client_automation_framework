import streamlit as st
import time
from typing import Dict, Any, List
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from client.frontend.utils.api_client import get_api_client, run_async


def display_chat_message(message: Dict[str, Any], key: str = None):
    """Display a single chat message with enhanced formatting."""
    with st.chat_message(message["role"], avatar=_get_avatar(message["role"])):
        st.markdown(message["content"])
        
        if message.get("tool_calls"):
            display_tool_calls_inline(message["tool_calls"])
        
        if message.get("iterations") and message["iterations"] > 1:
            st.caption(f"🔄 Completed in {message['iterations']} iterations")
        
        if message.get("timestamp"):
            st.caption(f"⏰ {message['timestamp']}")


def display_tool_calls_inline(tool_calls: List[Dict[str, Any]]):
    """Display tool calls inline with the message."""
    if not tool_calls:
        return

    st.markdown("**🛠️ Tools Used:**")
    
    for i, tool_call in enumerate(tool_calls, 1):
        status_icon = "✅" if tool_call["success"] else "❌"
        tool_name = tool_call.get("tool_name", "Unknown")
        
        with st.expander(f"{status_icon} {tool_name}", expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write("**Status:**")
                if tool_call["success"]:
                    st.success("Success")
                else:
                    st.error("Failed")
                
                if tool_call.get("args"):
                    st.write("**Arguments:**")
                    st.json(tool_call["args"])
            
            with col2:
                if tool_call["success"] and tool_call.get("result"):
                    st.write("**Result:**")
                    result = str(tool_call["result"])
                    if len(result) > 300:
                        result = result[:300] + "..."
                    st.code(result, language="text")
                elif tool_call.get("error"):
                    st.write("**Error:**")
                    st.error(tool_call["error"])


def add_message_to_history(role: str, content: str, tool_calls: List[Dict] = None, iterations: int = 1):
    """Add a message to the chat history with metadata."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    message = {
        "role": role,
        "content": content,
        "timestamp": time.strftime("%H:%M:%S"),
        "iterations": iterations
    }
    
    if tool_calls:
        message["tool_calls"] = tool_calls
    
    st.session_state.messages.append(message)


def render_chat_interface():
    """Render the main chat interface with improved layout."""
    st.title("💬 MCP Chat Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "processing" not in st.session_state:
        st.session_state.processing = False

    messages_container = st.container()
    
    with messages_container:
        if st.session_state.messages:
            for i, message in enumerate(st.session_state.messages):
                display_chat_message(message, key=f"msg_{i}")
        else:
            st.info("👋 Hello! How can I help you today?")
    
    st.markdown("---")
    
    if prompt := st.chat_input(
        "Ask me anything...", 
        disabled=st.session_state.processing,
        key="chat_input"
    ):
        add_message_to_history("user", prompt)
        
        st.session_state.processing = True
        
        st.rerun()

    if st.session_state.processing and st.session_state.messages:
        last_message = st.session_state.messages[-1]
        if last_message["role"] == "user":
            process_ai_response(last_message["content"])


def process_ai_response(user_prompt: str):
    """Process AI response with simulated streaming updates."""
    with st.chat_message("assistant", avatar="🤖"):
        status_placeholder = st.empty()
        response_placeholder = st.empty()
        tools_placeholder = st.empty()
        
        try:
            status_placeholder.info("🧠 Analyzing your request...")
            time.sleep(0.5)
            
            status_placeholder.info("🔄 Processing with AI...")
            
            api_client = get_api_client()
            response = run_async(api_client.send_chat_message(user_prompt))
            
            if response.get("success"):
                ai_content = response["response"]
                tool_calls = response.get("tool_calls", [])
                iterations = response.get("iterations", 1)
                
                if tool_calls:
                    tool_names = [tc.get("tool_name", "Unknown") for tc in tool_calls]
                    status_placeholder.success(f"🛠️ Used {len(tool_calls)} tools: {', '.join(tool_names)}")
                    
                    with tools_placeholder.container():
                        st.markdown("**🔧 Tools Active:**")
                        for tc in tool_calls:
                            tool_name = tc.get("tool_name", "Unknown")
                            status_icon = "✅" if tc["success"] else "❌"
                            st.caption(f"{status_icon} {tool_name}")
                    
                    time.sleep(0.3)
                else:
                    status_placeholder.info("💭 Generating response...")
                
                words = ai_content.split()
                displayed_text = ""
                
                tools_placeholder.empty()
                
                chunk_size = max(1, len(words) // 5)
                for i in range(0, len(words), chunk_size):
                    chunk = words[i:i + chunk_size]
                    displayed_text += " " + " ".join(chunk)
                    response_placeholder.markdown(displayed_text + " ▋")
                    time.sleep(0.2)
                
                status_placeholder.success("✅ Response complete")
                response_placeholder.markdown(ai_content)
                
                add_message_to_history("assistant", ai_content, tool_calls, iterations)
                
                if iterations > 1:
                    st.info(f"🔄 Completed in {iterations} iterations")
                
                time.sleep(0.5)
                
            else:
                error_msg = f"❌ Error: {response.get('error', 'Unknown error')}"
                status_placeholder.error("❌ Failed to get response")
                response_placeholder.error(error_msg)
                add_message_to_history("assistant", error_msg)
                
        except Exception as e:
            error_msg = f"❌ Connection error: {str(e)}"
            status_placeholder.error("❌ Connection failed")
            response_placeholder.error(error_msg)
            add_message_to_history("assistant", error_msg)
        
        finally:
            time.sleep(1)
            status_placeholder.empty()
            
            st.session_state.processing = False
            
            st.rerun()


def render_chat_controls():
    """Render chat control buttons."""
    st.subheader("Chat Controls")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🗑️ Clear Chat", help="Clear conversation history", key="clear_chat_controls"):
            st.session_state.messages = []
            st.session_state.processing = False
            
            try:
                api_client = get_api_client()
                run_async(api_client.reset_conversation())
                st.success("✅ Chat cleared")
            except Exception as e:
                st.error(f"❌ Failed to reset: {str(e)}")
            
            st.rerun()

    with col2:
        if st.button("🔄 Refresh", help="Refresh interface", key="refresh_chat_controls"):
            st.rerun()

    with col3:
        msg_count = len(st.session_state.messages) if "messages" in st.session_state else 0
        st.metric("Messages", msg_count)


def _get_avatar(role: str) -> str:
    """Get avatar for message role."""
    avatars = {"user": "👤", "assistant": "🤖", "system": "⚙️"}
    return avatars.get(role, "💬")


def render_conversation_info():
    """Render conversation information."""
    st.subheader("📊 Conversation Info")
    
    try:
        api_client = get_api_client()
        chat_status = run_async(api_client.get_chat_status())

        if chat_status:
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Server Messages", 
                    chat_status.get("conversation_length", 0)
                )
                st.metric(
                    "Local Messages", 
                    len(st.session_state.messages) if "messages" in st.session_state else 0
                )

            with col2:
                st.metric("Tools Available", chat_status.get("tools_available", 0))
                model = chat_status.get("gemini_model", "unknown")
                st.write(f"**Model:** {model}")
                
                if st.session_state.get("processing"):
                    st.warning("🔄 Processing...")
                else:
                    st.success("✅ Ready")

    except Exception as e:
        st.error(f"Failed to get conversation info: {str(e)}")


def render_chat_status():
    """Render current chat status."""
    if st.session_state.get("processing"):
        st.warning("🔄 AI is thinking...")
    else:
        st.success("💬 Ready for your message")
    
    if "messages" in st.session_state and st.session_state.messages:
        last_msg = st.session_state.messages[-1]
        if last_msg.get("timestamp"):
            st.caption(f"Last activity: {last_msg['timestamp']}")


def export_conversation():
    """Export conversation to text format."""
    if "messages" not in st.session_state or not st.session_state.messages:
        return "No conversation to export."
    
    export_text = "# MCP Chat Conversation\n\n"
    for msg in st.session_state.messages:
        role = msg["role"].title()
        content = msg["content"]
        timestamp = msg.get("timestamp", "")
        
        export_text += f"## {role} ({timestamp})\n{content}\n\n"
        
        if msg.get("tool_calls"):
            export_text += "**Tools Used:**\n"
            for tc in msg["tool_calls"]:
                tool_name = tc.get("tool_name", "Unknown")
                status = "✅" if tc["success"] else "❌"
                export_text += f"- {status} {tool_name}\n"
            export_text += "\n"
    
    return export_text


def get_conversation_stats():
    """Get conversation statistics."""
    if "messages" not in st.session_state:
        return {}
    
    messages = st.session_state.messages
    user_msgs = [m for m in messages if m["role"] == "user"]
    ai_msgs = [m for m in messages if m["role"] == "assistant"]
    
    total_tools = 0
    for msg in ai_msgs:
        if msg.get("tool_calls"):
            total_tools += len(msg["tool_calls"])
    
    return {
        "total_messages": len(messages),
        "user_messages": len(user_msgs),
        "ai_messages": len(ai_msgs),
        "tools_used": total_tools
    }
