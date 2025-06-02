import asyncio
from typing import List, Dict, Any, Optional

from google import genai
from google.genai.types import (
    Tool as GeminiTool,
    FunctionDeclaration,
    Content,
    Part,
    GenerateContentConfig,
    Schema,
    Type,
)

from ..core.config import settings
from ..core.exceptions import GeminiServiceError
from ..shared.logger import get_logger

logger = get_logger(__name__)


class GeminiService:
    """Gemini AI service with MCP tool integration and lazy initialization."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """Initialize Gemini service with optional lazy initialization."""
        self.client = None
        self.model_name = model_name or settings.gemini_model
        self._api_key = api_key
        self._is_initialized = False

        if api_key or settings.gemini_api_key:
            try:
                self._initialize_client(api_key or settings.gemini_api_key)
            except Exception as e:
                logger.warning(
                    f"Initial Gemini initialization failed (will retry later): {str(e)}"
                )

    def _initialize_client(self, api_key: str):
        """Initialize the Gemini client with API key."""
        if not api_key:
            raise GeminiServiceError("GEMINI_API_KEY is required")

        try:
            self.client = genai.Client(api_key=api_key)
            self._api_key = api_key
            self._is_initialized = True
            logger.info(
                f"Gemini service initialized successfully with model: {self.model_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise GeminiServiceError(f"Client initialization failed: {str(e)}")

    def configure(self, api_key: str, model_name: Optional[str] = None) -> bool:
        """Configure or reconfigure the Gemini service."""
        try:
            if model_name:
                self.model_name = model_name

            self._initialize_client(api_key)
            logger.info("Gemini service configured successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to configure Gemini service: {str(e)}")
            return False

    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return self._is_initialized and self.client is not None

    def _ensure_initialized(self):
        """Ensure service is initialized before use."""
        if not self.is_configured():
            if settings.gemini_api_key:
                try:
                    self._initialize_client(settings.gemini_api_key)
                except Exception:
                    pass

            if not self.is_configured():
                raise GeminiServiceError(
                    "Gemini service not configured. Please set API key via configuration."
                )

    async def generate_response(
        self, contents: List[Content], tools: Optional[List[GeminiTool]] = None
    ) -> Any:
        """Generate response using Gemini with async execution."""
        self._ensure_initialized()

        try:
            logger.debug(
                f"Generating response with {len(contents)} messages and {len(tools) if tools else 0} tools"
            )

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=GenerateContentConfig(
                        temperature=settings.temperature,
                        max_output_tokens=settings.max_tokens,
                        tools=tools,
                    ),
                ),
            )

            logger.debug("Gemini response generated successfully")
            return response

        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise GeminiServiceError(f"Generation failed: {str(e)}")

    def convert_mcp_tools_to_gemini(self, mcp_tools: List) -> List[GeminiTool]:
        """Convert MCP tools to Gemini format."""
        self._ensure_initialized()

        gemini_tools = []

        for tool in mcp_tools:
            try:
                parameters = self._clean_schema(tool.inputSchema)

                function_declaration = FunctionDeclaration(
                    name=tool.name,
                    description=tool.description or f"Tool: {tool.name}",
                    parameters=parameters,
                )

                gemini_tool = GeminiTool(function_declarations=[function_declaration])
                gemini_tools.append(gemini_tool)

                logger.debug(f"Converted tool: {tool.name}")

            except Exception as e:
                logger.warning(f"Failed to convert tool {tool.name}: {str(e)}")
                continue

        logger.info(f"Converted {len(gemini_tools)} tools for Gemini")
        return gemini_tools

    def _clean_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Clean MCP schema to be compatible with Gemini API - theo cách của mcp_client."""
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
            "string",
            "number",
            "integer",
            "boolean",
            "object",
            "array",
            "null",
        ]:
            clean_schema["type"] = "object"

        if "properties" in clean_schema and isinstance(
            clean_schema["properties"], dict
        ):
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
                    if any(
                        special_key in value
                        for special_key in ["anyOf", "oneOf", "allOf"]
                    ):
                        properties[key] = {
                            "type": "string",
                            "description": f"Property {key} (simplified from complex schema)",
                        }
                    else:
                        clean_value = self._clean_schema(value)
                        properties[key] = clean_value

            clean_schema["properties"] = properties

        return clean_schema

    def _convert_schema_to_gemini(self, schema: Dict[str, Any]) -> Schema:
        """Convert JSON Schema to Gemini Schema format."""
        try:
            if not isinstance(schema, dict):
                return self._create_default_schema()

            if any(key in schema for key in ["anyOf", "oneOf", "allOf"]):
                return self._simplify_complex_schema()

            clean_schema = self._clean_schema(schema.copy())
            return self._build_gemini_schema(clean_schema)

        except Exception as e:
            logger.warning(f"Schema conversion failed, using default: {str(e)}")
            return self._create_default_schema()

    def _build_gemini_schema(self, schema: Dict[str, Any]) -> Schema:
        """Build Gemini Schema from clean JSON schema."""
        schema_type = self._get_gemini_type(schema.get("type", "object"))

        if schema_type == Type.OBJECT and "properties" in schema:
            properties = {}
            for key, prop_schema in schema["properties"].items():
                properties[key] = self._build_gemini_schema(prop_schema)

            return Schema(
                type=schema_type,
                properties=properties,
                required=schema.get("required", []),
            )
        else:
            return Schema(type=schema_type, description=schema.get("description", ""))

    def _get_gemini_type(self, json_type: str) -> Type:
        """Map JSON Schema type to Gemini Type."""
        type_mapping = {
            "string": Type.STRING,
            "number": Type.NUMBER,
            "integer": Type.INTEGER,
            "boolean": Type.BOOLEAN,
            "object": Type.OBJECT,
            "array": Type.ARRAY,
            "null": Type.STRING,
        }
        return type_mapping.get(json_type, Type.STRING)

    def _create_default_schema(self) -> Schema:
        """Create a default schema for problematic tools."""
        return Schema(
            type=Type.OBJECT,
            properties={},
            description="Default schema for complex tool",
        )

    def _simplify_complex_schema(self) -> Schema:
        """Simplify complex schemas with anyOf/oneOf/allOf."""
        return Schema(
            type=Type.STRING, description="Simplified from complex JSON Schema"
        )
