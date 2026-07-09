"""Filter Planner Agent for External Data Queries

This agent analyzes natural language queries and returns filter operations
that the frontend can execute locally on external data. Instead of processing
data on the backend, it acts as a query planner.

The frontend sends:
- Model metadata (categories, properties)
- External data metadata (column names, distinct values)

The agent returns:
- Filter operations (model filters + external data filters)
- Viewer actions to apply after filtering
"""
from typing import List, Dict, Any, Optional
import logging
import json

from .base_agent import BaseAgent, AgentResponse
from llm_providers.base import BaseLLMProvider
from data_layer.query_engine import QueryEngine

logger = logging.getLogger(__name__)


class FilterPlannerAgent(BaseAgent):
    """Agent that plans filter operations for external data queries"""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        query_engine: QueryEngine
    ):
        super().__init__(llm_provider, query_engine)

    @property
    def name(self) -> str:
        return "filter_planner"

    @property
    def description(self) -> str:
        return """Plans filter operations for queries involving external data connected
        to 3D model elements. Returns filter conditions that the frontend executes locally."""

    @property
    def capabilities(self) -> List[str]:
        return [
            "external_data_filtering",
            "model_property_filtering",
            "combined_filtering",
            "status_queries",
            "progress_queries",
            "timeline_queries"
        ]

    def _build_system_prompt(self, context: Optional[Dict] = None) -> str:
        """Build the system prompt with available metadata"""

        # Extract model metadata
        model_info = ""
        if context and context.get('model_context'):
            mc = context['model_context']
            metadata = mc.get('metadata', {})
            if metadata:
                categories = metadata.get('categories', [])
                searchable_props = metadata.get('searchable_properties', [])
                model_info = f"""
MODEL METADATA:
- Categories: {', '.join(categories) if categories else 'Unknown'}
- Searchable properties: {', '.join(searchable_props) if searchable_props else 'Category, Type, Name'}
"""

        # Extract external data metadata
        external_info = ""
        if context and context.get('external_data_context'):
            edc = context['external_data_context']
            columns = edc.get('columns', [])
            distinct_values = edc.get('distinct_values', {})
            identity_col = edc.get('identity_column')
            status_col = edc.get('status_column')
            progress_col = edc.get('progress_column')

            external_info = f"""
EXTERNAL DATA METADATA:
- Available columns: {', '.join(columns) if columns else 'None'}
- Identity column (links to model): {identity_col or 'Not specified'}
- Status column: {status_col or 'Not specified'}
- Progress column: {progress_col or 'Not specified'}
- Column distinct values:
"""
            for col, values in distinct_values.items():
                role = ""
                if col == identity_col:
                    role = " [IDENTITY - links to model]"
                elif col == status_col:
                    role = " [STATUS]"
                elif col == progress_col:
                    role = " [PROGRESS]"

                if len(values) <= 10:
                    external_info += f"  - {col}{role}: {values}\n"
                else:
                    external_info += f"  - {col}{role}: {values[:10]} (and {len(values) - 10} more)\n"

        return f"""You are a Filter Planner Agent in a construction project analytics system.

Your role: Analyze user queries about elements and external data, then return filter operations
that the frontend can execute locally. You do NOT have access to the actual data - only metadata.

{model_info}
{external_info}

IMPORTANT: You must return filter operations that the frontend will execute. The frontend has:
1. Model data (3D elements with properties like Category, Type, Name, Level)
2. External data (Excel/CSV data linked to model elements via identity column)

RESPONSE FORMAT - Return a JSON object:
{{
    "filter_operations": [
        {{
            "source": "model" | "external",
            "property": "<property name>",
            "operator": "equals" | "contains" | "startsWith" | "endsWith" | "gt" | "lt" | "gte" | "lte" | "between" | "in" | "notEquals" | "isEmpty" | "isNotEmpty",
            "value": "<value to match>",
            "caseSensitive": false
        }}
    ],
    "combine_mode": "AND" | "OR",
    "viewer_actions": [
        {{
            "operation": "isolate" | "select" | "hide" | "show" | "fitToView" | "setColor",
            "params": {{
                "useFilteredResults": true,
                "color": "#FF0000"
            }}
        }}
    ],
    "interpretation": "<explanation of what the filters will do>",
    "requires_external_data": true | false
}}

FILTER OPERATORS:
- equals: Exact match (case-insensitive by default)
- contains: Property value contains the string
- startsWith/endsWith: String prefix/suffix matching
- gt/lt/gte/lte: Numeric comparisons (greater than, less than, etc.)
- between: Value is between two numbers (value should be [min, max])
- in: Value is one of multiple options (value should be an array)
- notEquals: Not equal to value
- isEmpty/isNotEmpty: Check if value is null/empty or not

EXAMPLES:

Query: "Show all delayed doors"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Doors"}},
        {{"source": "external", "property": "Status", "operator": "equals", "value": "Delayed"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for door elements with 'Delayed' status from external data",
    "requires_external_data": true
}}

Query: "Color code elements by progress"
Response:
{{
    "filter_operations": [],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "colorByProperty", "params": {{"property": "Progress", "source": "external", "colorScale": "percentage"}}}}
    ],
    "interpretation": "Will color code all elements based on their Progress percentage from external data",
    "requires_external_data": true
}}

Query: "Show walls on Level 1"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Walls"}},
        {{"source": "model", "property": "Level", "operator": "equals", "value": "Level 1"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for wall elements on Level 1",
    "requires_external_data": false
}}

Query: "Find elements with progress less than 50%"
Response:
{{
    "filter_operations": [
        {{"source": "external", "property": "Progress", "operator": "lt", "value": 50}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "setColor", "params": {{"useFilteredResults": true, "color": "#FF6B6B"}}}}
    ],
    "interpretation": "Filtering for elements with less than 50% progress, will highlight in red",
    "requires_external_data": true
}}

Query: "Show all doors that has status inspected"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Doors"}},
        {{"source": "external", "property": "Status", "operator": "equals", "value": "Inspected"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "select", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "First filtering by model Category 'Doors', then filtering by external Status 'Inspected'. Will isolate, select and zoom to matching elements.",
    "requires_external_data": true
}}

Query: "Isolate completed walls"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Walls"}},
        {{"source": "external", "property": "Status", "operator": "equals", "value": "Completed"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for wall elements with 'Completed' status from external data",
    "requires_external_data": true
}}

Query: "Show all doors that has glass"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Doors"}},
        {{"source": "model", "property": "Material", "operator": "contains", "value": "Glass"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for door elements where Material contains 'Glass'. This is a model-only query using two model property filters.",
    "requires_external_data": false
}}

Query: "Glass doors"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Doors"}},
        {{"source": "model", "property": "Material", "operator": "contains", "value": "Glass"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for doors with glass material",
    "requires_external_data": false
}}

Query: "Show concrete walls on Level 2"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Walls"}},
        {{"source": "model", "property": "Material", "operator": "contains", "value": "Concrete"}},
        {{"source": "model", "property": "Level", "operator": "equals", "value": "Level 2"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for wall elements made of concrete on Level 2. Three model property filters combined.",
    "requires_external_data": false
}}

Query: "Exterior doors"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "equals", "value": "Doors"}},
        {{"source": "model", "property": "Type Name", "operator": "contains", "value": "Exterior"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for exterior doors by checking if Type Name contains 'Exterior'",
    "requires_external_data": false
}}

Query: "Steel beams"
Response:
{{
    "filter_operations": [
        {{"source": "model", "property": "Category", "operator": "contains", "value": "Structural Framing"}},
        {{"source": "model", "property": "Material", "operator": "contains", "value": "Steel"}}
    ],
    "combine_mode": "AND",
    "viewer_actions": [
        {{"operation": "isolate", "params": {{"useFilteredResults": true}}}},
        {{"operation": "fitToView", "params": {{"useFilteredResults": true}}}}
    ],
    "interpretation": "Filtering for structural framing elements (beams) made of steel",
    "requires_external_data": false
}}

IMPORTANT RULES:
1. When a query mentions BOTH a model element type (doors, walls, windows, etc.) AND an external property value (status, progress values), create filter operations for BOTH model and external sources.
2. When a query mentions a model element type AND a material/characteristic (glass, concrete, steel, exterior, etc.), create MULTIPLE MODEL filter operations.
3. The model filter for element type should use "Category" property.
4. The model filter for materials should use "Material" property with "contains" operator.
5. The model filter for type characteristics (exterior, interior, etc.) should use "Type Name" property with "contains" operator.
6. Always use combine_mode "AND" when filtering by multiple properties.
7. Use the exact column names and values from the metadata provided.
8. If no external data context is provided, only use model filters.
9. Common model properties: Category, Type Name, Material, Level, Family, Mark, Comments.
10. If a query cannot be answered with the available metadata, explain what's missing.
"""

    def _register_tools(self) -> List[Dict]:
        """No tools needed - this agent just analyzes and returns filter plans"""
        return []

    async def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """No tools to execute"""
        return {"error": f"Unknown tool: {tool_name}"}

    async def process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Process query and return filter operations"""
        from .interaction_logger import get_tracer

        tracer = get_tracer()
        system_prompt = self._build_system_prompt(context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        try:
            response = await self.llm.chat(messages)
            return self._parse_filter_response(response.content)

        except Exception as e:
            logger.error(f"Error in filter planner: {e}")
            return AgentResponse(
                success=False,
                data=None,
                message=f"Error planning filters: {str(e)}",
                error=str(e)
            )

    def _parse_filter_response(self, content: str) -> AgentResponse:
        """Parse the LLM response containing filter operations"""
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

            data = json.loads(content)

            return AgentResponse(
                success=True,
                data=data.get("filter_operations", []),
                message=data.get("interpretation", "Filter plan created."),
                charts=[],
                metadata={
                    "filter_operations": data.get("filter_operations", []),
                    "combine_mode": data.get("combine_mode", "AND"),
                    "viewer_actions": data.get("viewer_actions", []),
                    "requires_external_data": data.get("requires_external_data", False)
                }
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse filter response: {e}")
            return AgentResponse(
                success=False,
                data=[],
                message=content,
                error="Failed to parse filter operations"
            )
