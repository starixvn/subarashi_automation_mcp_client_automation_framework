import os
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai.types import Tool as GeminiTool
from google.genai.types import FunctionDeclaration, Content, Part
from google.genai.types import GenerateContentConfig

load_dotenv()


class GeminiService:
    def __init__(self):
        """Initialize the Gemini service."""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        self.client = genai.Client(api_key=gemini_api_key)
        self.model = "gemini-2.0-flash-001"
        self.max_tokens = 1000
        
    def generate_response(self, contents: List[Content], tools: Optional[List[GeminiTool]] = None):
        """Generate a response using Gemini models.
        
        Args:
            contents: List of Content objects representing the conversation
            tools: Optional list of tools to provide to the model
            
        Returns:
            The Gemini response
        """
        return self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=self.max_tokens,
                tools=tools,
            ),
        )
    
    def convert_mcp_tools_to_gemini_tools(self, mcp_tools) -> List[GeminiTool]:
        """Convert MCP tools to Gemini tools format.
        
        Args:
            mcp_tools: List of MCP Tool objects
            
        Returns:
            List of Gemini Tool objects
        """
        gemini_tools = []
        skip_tools = set()

        for tool in mcp_tools:
            try:
                if tool.name.startswith("API-") and tool.name in [
                    "API-OAuth2", "API-Init", "API-GET", "API-POST",
                    "API-PUT", "API-DELETE", "API-BasicAuth", "API-BearerToken"
                ]:
                    skip_tools.add(tool.name)
                    continue

                parameters = self._clean_schema(tool.inputSchema)

                function_declaration = FunctionDeclaration(
                    name=tool.name,
                    description=tool.description or f"Tool: {tool.name}",
                    parameters=parameters,
                )

                gemini_tool = GeminiTool(function_declarations=[function_declaration])
                gemini_tools.append(gemini_tool)

            except Exception as e:
                print(f"Error converting tool {tool.name}: {str(e)}")
                skip_tools.add(tool.name)

        if skip_tools:
            print(f"Skipped problematic tools: {skip_tools}")
            
        return gemini_tools

    def _clean_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Clean MCP schema to be compatible with Gemini API."""
        if not isinstance(schema, dict):
            return {"type": "object"}

        clean_schema = schema.copy()

        if any(key in clean_schema for key in ["anyOf", "oneOf", "allOf"]):
            if "anyOf" in clean_schema:
                cleaned_items = []
                for item in clean_schema["anyOf"]:
                    cleaned_items.append(self._clean_schema(item))
                return {"anyOf": cleaned_items}
            elif "oneOf" in clean_schema:
                cleaned_items = []
                for item in clean_schema["oneOf"]:
                    cleaned_items.append(self._clean_schema(item))
                return {"oneOf": cleaned_items}
            elif "allOf" in clean_schema:
                cleaned_items = []
                for item in clean_schema["allOf"]:
                    cleaned_items.append(self._clean_schema(item))
                return {"allOf": cleaned_items}

        clean_schema.pop("title", None)
        clean_schema.pop("additionalProperties", None)

        if "type" not in clean_schema:
            clean_schema["type"] = "object"
        elif clean_schema["type"] not in [
            "string", "number", "integer", "boolean", "object", "array", "null"
        ]:
            clean_schema["type"] = "object"

        if "properties" in clean_schema and isinstance(clean_schema["properties"], dict):
            properties = {}
            for key, value in list(clean_schema["properties"].items()):
                if value is True or value is False:
                    properties[key] = {
                        "type": "string",
                        "description": f"Property {key}",
                    }
                elif not isinstance(value, dict):
                    properties[key] = {
                        "type": "string",
                        "description": f"Property {key}",
                    }
                else:
                    if any(special_key in value for special_key in ["anyOf", "oneOf", "allOf"]):
                        properties[key] = {
                            "type": "string",
                            "description": f"Property {key} (simplified from complex schema)",
                        }
                    else:
                        clean_value = self._clean_schema(value)
                        properties[key] = clean_value

            clean_schema["properties"] = properties

        return clean_schema 