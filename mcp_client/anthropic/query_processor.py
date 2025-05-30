from typing import List, Dict, Any


class QueryProcessor:
    
    def __init__(self, session_manager, anthropic_service):
        self.session_manager = session_manager
        self.anthropic_service = anthropic_service
        
    async def process_query(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]
        tools = await self.session_manager.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ]
        
        response = self.anthropic_service.generate_response(
            messages=messages,
            tools=available_tools,
        )
        
        tool_results = []
        final_text = []
        
        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input
                
                result = await self.session_manager.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                
                if hasattr(content, "text") and content.text:
                    messages.append({"role": "assistant", "content": content.text})
                messages.append({"role": "user", "content": result.content})
                
                response = self.anthropic_service.generate_response(
                    messages=messages,
                )
                
                final_text.append(response.content[0].text)
                
        return "\n".join(final_text) 