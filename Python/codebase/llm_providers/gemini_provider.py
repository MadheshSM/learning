"""Google Gemini LLM provider implementation"""
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import List, Dict, Any, Optional
import json
import logging
import asyncio

from .base import BaseLLMProvider, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider implementation"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self._model_instance = None

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def default_model(self) -> str:
        return "gemini-1.5-pro"

    def _get_model(self, tools: Optional[List] = None):
        """Get or create the generative model instance"""
        model_config = {
            "model_name": self.model,
        }

        if tools:
            model_config["tools"] = tools

        return genai.GenerativeModel(**model_config)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """Send a chat completion request to Gemini"""
        try:
            # Convert tools if provided
            gemini_tools = self._convert_tools(tools) if tools else None

            # Get model instance
            model = self._get_model(gemini_tools)

            # Extract system instruction if present
            system_instruction = None
            chat_messages = []

            for msg in messages:
                if msg.get("role") == "system":
                    system_instruction = msg.get("content", "")
                else:
                    chat_messages.append(msg)

            # Convert messages to Gemini format
            converted_messages = self._convert_messages(chat_messages)

            # Configure generation
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Safety settings
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }

            # Start chat and send message
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=self.model,
                    system_instruction=system_instruction,
                    tools=gemini_tools
                )

            chat = model.start_chat(history=converted_messages[:-1] if len(converted_messages) > 1 else [])

            # Get the last message to send
            last_message = converted_messages[-1] if converted_messages else {"parts": [{"text": "Hello"}]}

            # Run synchronous call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: chat.send_message(
                    last_message.get("parts", [{"text": ""}]),
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            )

            # Extract content and function calls
            content = ""
            tool_calls = []

            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    content += part.text
                elif hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    tool_calls.append(ToolCall(
                        tool_id=f"call_{fc.name}_{len(tool_calls)}",
                        tool_name=fc.name,
                        tool_input=dict(fc.args) if fc.args else {}
                    ))

            # Get usage metadata if available
            usage = None
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "input_tokens": response.usage_metadata.prompt_token_count,
                    "output_tokens": response.usage_metadata.candidates_token_count
                }

            return LLMResponse(
                content=content,
                tool_calls=tool_calls if tool_calls else None,
                usage=usage,
                model=self.model,
                finish_reason="stop",
                raw_response=response
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def _convert_tools(self, tools: List[Dict]) -> List:
        """Convert tools to Gemini's function declaration format"""
        if not tools:
            return None

        function_declarations = []
        for tool in tools:
            # Convert parameters to Gemini schema format
            parameters = tool.get("parameters", {"type": "object", "properties": {}})

            func_decl = genai.protos.FunctionDeclaration(
                name=tool.get("name"),
                description=tool.get("description", ""),
                parameters=self._convert_schema(parameters)
            )
            function_declarations.append(func_decl)

        return [genai.protos.Tool(function_declarations=function_declarations)]

    def _convert_schema(self, schema: Dict) -> Dict:
        """Convert JSON schema to Gemini schema format"""
        gemini_type_map = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT,
        }

        schema_type = schema.get("type", "object")

        result = {
            "type": gemini_type_map.get(schema_type, genai.protos.Type.OBJECT),
        }

        if "properties" in schema:
            result["properties"] = {}
            for prop_name, prop_schema in schema["properties"].items():
                result["properties"][prop_name] = self._convert_schema(prop_schema)

        if "required" in schema:
            result["required"] = schema["required"]

        if "description" in schema:
            result["description"] = schema["description"]

        if "enum" in schema:
            result["enum"] = schema["enum"]

        return genai.protos.Schema(**result)

    def _convert_messages(self, messages: List[Dict]) -> List[Dict]:
        """Convert messages to Gemini's expected format"""
        converted = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "user":
                converted.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                parts = []
                if content:
                    parts.append({"text": content})

                # Handle tool calls
                if msg.get("tool_calls"):
                    for tc in msg.get("tool_calls", []):
                        if isinstance(tc, dict):
                            parts.append({
                                "function_call": {
                                    "name": tc.get("tool_name", tc.get("name")),
                                    "args": tc.get("tool_input", tc.get("input", {}))
                                }
                            })
                        elif hasattr(tc, 'tool_name'):
                            parts.append({
                                "function_call": {
                                    "name": tc.tool_name,
                                    "args": tc.tool_input
                                }
                            })

                converted.append({
                    "role": "model",
                    "parts": parts
                })
            elif role == "tool":
                # Tool response
                tool_call_id = msg.get("tool_call_id", "")
                tool_name = tool_call_id.split("_")[1] if "_" in tool_call_id else "function"

                try:
                    response_data = json.loads(content)
                except json.JSONDecodeError:
                    response_data = {"result": content}

                converted.append({
                    "role": "user",
                    "parts": [{
                        "function_response": {
                            "name": tool_name,
                            "response": response_data
                        }
                    }]
                })

        return converted
