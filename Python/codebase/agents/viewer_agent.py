"""Viewer Agent for controlling Autodesk Viewer through chat

This agent handles natural language commands for viewer operations like:
- Element selection, isolation, visibility
- Camera control and preset views
- Sectioning and explode views
- Measurements and annotations
- Walkthroughs and animations
"""
from typing import List, Dict, Any, Optional
import logging

from .base_agent import BaseAgent, AgentResponse
from .tools.viewer_tools import ViewerTools
from llm_providers.base import BaseLLMProvider
from data_layer.query_engine import QueryEngine

logger = logging.getLogger(__name__)


class ViewerAgent(BaseAgent):
    """Agent for controlling the 3D model viewer through natural language"""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        query_engine: QueryEngine,
        model_metadata: Optional[Dict] = None
    ):
        """
        Initialize the ViewerAgent

        Args:
            llm_provider: LLM provider for natural language processing
            query_engine: Query engine for data access (may not be used much)
            model_metadata: Optional pre-loaded model metadata for element lookups
        """
        self.viewer_tools = ViewerTools(model_metadata)
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "viewer"

    @property
    def description(self) -> str:
        return """Controls the 3D model viewer. Can select, isolate, hide/show elements,
        control camera views, create sections, explode models, take measurements,
        add annotations/markups, and create camera walkthroughs."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "element_selection",
            "visibility_control",
            "camera_control",
            "view_presets",
            "sectioning",
            "explode_view",
            "measurement",
            "markup_annotation",
            "walkthrough",
            "property_queries"
        ]

    def _build_system_prompt(self, context: Optional[Dict] = None) -> str:
        """Build the system prompt for the viewer agent with model context"""

        # Extract model metadata if available
        model_info = ""
        if context and context.get('model_context'):
            mc = context['model_context']
            metadata = mc.get('metadata', {})

            if metadata:
                categories = metadata.get('categories', [])
                searchable_props = metadata.get('searchable_properties', [])
                property_details = metadata.get('property_details', [])
                element_count = metadata.get('element_count', 0)

                model_info = f"""
MODEL INFORMATION:
- Total elements: {element_count}
- Available categories: {', '.join(categories) if categories else 'Unknown'}
- Searchable properties: {', '.join(searchable_props) if searchable_props else 'Category, Type, Name'}
"""
                if property_details:
                    model_info += "\nPROPERTY DETAILS (actual property names with sample values):\n"
                    for prop in property_details[:40]:  # Limit to avoid huge prompts
                        name = prop.get('name', '')
                        group = prop.get('category', '')
                        samples = prop.get('sampleValues', [])
                        if samples:
                            model_info += f"  - [{group}] {name}: {', '.join(str(s) for s in samples[:3])}\n"

        return f"""You are the Viewer Agent in a construction project analytics system.

Your role: Control the 3D model viewer based on user requests. You can select, isolate,
hide/show elements, control the camera, create sections, explode the model, take
measurements, add annotations, and create walkthroughs.
{model_info}
Instructions:
1. Analyze the user's request to understand what viewer operation they want
2. Check the PROPERTY DETAILS section above for actual property names and sample values
3. Use the EXACT property names from the model when building search filters
4. Use your tools to generate the appropriate viewer operations
5. Provide a clear message explaining what you did
6. Multiple operations can be chained together

CRITICAL SEARCH RULES:

HOW TO BUILD FILTERS:
- For EVERY search criterion, set property to null. The frontend searches across
  element names and ALL property values automatically.
- Do NOT specify property names in filters. Different element types use different
  property names (e.g., walls use "Base Constraint" but stairs use "Base Level" for the same floor).
  Setting property to null ensures the search works across all element types.
- Use the PROPERTY DETAILS above only to understand what values exist in the model
  (e.g., available floor names, material names), NOT to pick property names.
- Multiple criteria → use filters array with one entry per criterion. Results are ANDed.
- After search, use fitToView to zoom to results.

When responding, return a JSON object:
{{
    "data": [<list of viewer operations>],
    "insights": "Description of what was done",
    "charts": []
}}

Each viewer operation has:
- operation: The operation type (select, isolate, hide, show, fitToView, setCameraPreset, etc.)
- params: Parameters for the operation
- description: Human-readable description

Examples:
- "Stairs on Floor 30" -> filters: [{{"property": null, "value": "Stairs"}}, {{"property": null, "value": "Floor 30"}}]
- "Chrome furniture" -> filters: [{{"property": null, "value": "Furniture"}}, {{"property": null, "value": "Chrome"}}]
- "Show walls" -> filters: [{{"property": null, "value": "Walls"}}]
- "Give me a top view" -> use set_camera_view with preset "top"
- "Create a section through the middle" -> use create_section_plane
- "Explode the model" -> use explode_model with scale 1.0
- "Zoom to selection" -> use zoom_to_fit

Available camera presets: front, back, top, bottom, left, right, iso, iso_front, iso_back
Available measurement types: distance, angle, area
Available markup types: text, arrow, circle, rectangle, freehand, cloud, polyline
Section planes: X, Y, Z (with optional offset)
"""

    def _register_tools(self) -> List[Dict]:
        """Register viewer control tools"""
        return [
            {
                "name": "select_elements",
                "description": "Select elements in the 3D viewer by IDs, property, or name pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of element database IDs to select"
                        },
                        "by_name": {
                            "type": "string",
                            "description": "Select elements by name pattern"
                        },
                        "by_property": {
                            "type": "object",
                            "properties": {
                                "property": {"type": "string"},
                                "value": {"type": "string"}
                            },
                            "description": "Select by property value"
                        }
                    }
                }
            },
            {
                "name": "clear_selection",
                "description": "Clear the current selection in the viewer",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "isolate_elements",
                "description": "Isolate specific elements (hide everything else)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Element IDs to isolate"
                        }
                    },
                    "required": ["db_ids"]
                }
            },
            {
                "name": "hide_elements",
                "description": "Hide specific elements from view",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Element IDs to hide"
                        }
                    },
                    "required": ["db_ids"]
                }
            },
            {
                "name": "show_elements",
                "description": "Show hidden elements or show all",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Specific element IDs to show, or omit to show all"
                        }
                    }
                }
            },
            {
                "name": "show_all",
                "description": "Show all elements and clear any isolation",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "zoom_to_fit",
                "description": "Zoom camera to fit elements in view",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Elements to fit, or omit for entire model"
                        }
                    }
                }
            },
            {
                "name": "set_camera_view",
                "description": "Set camera to a standard view preset",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "preset": {
                            "type": "string",
                            "enum": ["front", "back", "top", "bottom", "left", "right", "iso", "iso_front", "iso_back"],
                            "description": "View preset"
                        }
                    },
                    "required": ["preset"]
                }
            },
            {
                "name": "set_camera_position",
                "description": "Set exact camera position and target",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "position": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Camera position [x, y, z]"
                        },
                        "target": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Look-at target [x, y, z]"
                        },
                        "up": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Up vector [x, y, z], defaults to [0, 0, 1]"
                        }
                    },
                    "required": ["position", "target"]
                }
            },
            {
                "name": "create_section_plane",
                "description": "Create a section cutting plane",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plane": {
                            "type": "string",
                            "enum": ["X", "Y", "Z"],
                            "description": "Section plane axis"
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset from model center"
                        }
                    },
                    "required": ["plane"]
                }
            },
            {
                "name": "clear_sections",
                "description": "Remove all section planes",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "explode_model",
                "description": "Explode the model to see internal components",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scale": {
                            "type": "number",
                            "description": "Explode scale (0=assembled, 1-3=exploded)"
                        }
                    }
                }
            },
            {
                "name": "reset_explode",
                "description": "Reset explode to assembled view",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "start_measurement",
                "description": "Start a measurement tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "measure_type": {
                            "type": "string",
                            "enum": ["distance", "angle", "area"],
                            "description": "Type of measurement"
                        }
                    }
                }
            },
            {
                "name": "clear_measurements",
                "description": "Clear all measurements",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "add_markup",
                "description": "Add annotation/markup to the view",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "markup_type": {
                            "type": "string",
                            "enum": ["text", "arrow", "circle", "rectangle", "freehand", "cloud", "polyline"],
                            "description": "Type of markup"
                        },
                        "text": {
                            "type": "string",
                            "description": "Text content for text markup"
                        },
                        "position": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"}
                            },
                            "description": "Screen position"
                        }
                    },
                    "required": ["markup_type"]
                }
            },
            {
                "name": "clear_markups",
                "description": "Clear all markups",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "start_walkthrough",
                "description": "Start animated camera walkthrough",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "waypoints": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "position": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "target": {
                                        "type": "array",
                                        "items": {"type": "number"}
                                    },
                                    "duration": {"type": "number"}
                                }
                            },
                            "description": "List of camera waypoints"
                        }
                    },
                    "required": ["waypoints"]
                }
            },
            {
                "name": "stop_walkthrough",
                "description": "Stop walkthrough animation",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_element_properties",
                "description": "Get properties of an element",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "db_id": {
                            "type": "integer",
                            "description": "Database ID of the element"
                        }
                    },
                    "required": ["db_id"]
                }
            },
            {
                "name": "search_elements",
                "description": "Search for elements by one or more property filters. Use the filters array for multi-criteria searches (e.g., category + level). Each filter has a property name and value. Results are intersected (AND logic).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Element category (e.g., 'Walls', 'Doors', 'Windows'). Shorthand for a Category filter."
                        },
                        "property_name": {
                            "type": "string",
                            "description": "Property name to search (single filter mode)"
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to match (single filter mode)"
                        },
                        "filters": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "property": {"type": "string", "description": "Property name (e.g., Category, Level, Material)"},
                                    "value": {"type": "string", "description": "Value to match"}
                                },
                                "required": ["property", "value"]
                            },
                            "description": "Array of property filters for multi-criteria search. Each filter is ANDed together."
                        }
                    }
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute viewer tool - returns operation spec for frontend"""
        tool_method = getattr(self.viewer_tools, tool_name, None)

        if tool_method:
            try:
                result = tool_method(**tool_input)
                logger.info(f"ViewerAgent executed {tool_name}: {result}")
                return result
            except Exception as e:
                logger.error(f"ViewerAgent tool error: {e}")
                return {"error": str(e)}

        return {"error": f"Unknown tool: {tool_name}"}

    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process a query using the agentic loop - overridden to pass context to system prompt"""
        from .interaction_logger import get_tracer
        import json as json_module

        tracer = get_tracer()
        # Pass context to _build_system_prompt to include model metadata
        system_prompt = self._build_system_prompt(context)

        # Store context for auto-injection into tool calls
        self._current_context = context

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        # Agentic loop
        for iteration in range(self.max_iterations):
            try:
                if iteration > 0:
                    tracer.log_agent_thinking(
                        self.name,
                        f"Processing iteration {iteration + 1}/{self.max_iterations}..."
                    )

                response = await self.llm.chat(messages, tools=self.tools)

                # If no tool calls, we have the final response
                if not response.tool_calls:
                    return self._parse_final_response(response.content)

                # Execute each tool call
                for tool_call in response.tool_calls:
                    logger.info(f"Executing tool: {tool_call.tool_name}")

                    tool_input = tool_call.tool_input.copy() if tool_call.tool_input else {}

                    tracer.log_tool_call(self.name, tool_call.tool_name, tool_input)

                    try:
                        result = await self._execute_tool(tool_call.tool_name, tool_input)
                        tracer.log_tool_result(self.name, tool_call.tool_name, result)
                        result_str = json_module.dumps(result, default=str)
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        result_str = json_module.dumps({"error": str(e)})
                        tracer.log_tool_result(self.name, tool_call.tool_name, {"error": str(e)})

                    messages.append({
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.tool_id,
                        "content": result_str
                    })

            except Exception as e:
                logger.error(f"Error in agent loop: {e}")
                return AgentResponse(
                    success=False,
                    data=None,
                    message=f"Error processing query: {str(e)}",
                    error=str(e)
                )

        return AgentResponse(
            success=False,
            data=None,
            message="Maximum iterations reached without completing the query",
            error="max_iterations_reached"
        )

    def _parse_final_response(self, content: str) -> AgentResponse:
        """Parse the final response from the LLM"""
        import json

        try:
            # Handle markdown code blocks
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            # Try to parse as JSON
            data = json.loads(content)

            # Extract viewer operations
            viewer_actions = []
            if "data" in data:
                if isinstance(data["data"], list):
                    viewer_actions = data["data"]
                elif isinstance(data["data"], dict) and "operation" in data["data"]:
                    viewer_actions = [data["data"]]

            metadata = {"viewer_actions": viewer_actions}
            follow_ups = data.get("follow_up_questions", [])
            if follow_ups:
                metadata["follow_up_questions"] = follow_ups

            return AgentResponse(
                success=True,
                data=viewer_actions,
                message=data.get("insights", "Viewer operations executed."),
                charts=data.get("charts", []),
                metadata=metadata
            )

        except json.JSONDecodeError:
            # If not JSON, return as plain text message
            return AgentResponse(
                success=True,
                data=[],
                message=content,
                charts=[],
                metadata={}
            )
