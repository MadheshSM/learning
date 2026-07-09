"""Orchestrator Agent for routing queries to specialist agents"""
from typing import List, Dict, Any, Optional
import json
import logging
import re

from llm_providers.base import BaseLLMProvider
from cache import get_cache
from .base_agent import BaseAgent, AgentResponse
from .interaction_logger import get_tracer, reset_tracer

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Central orchestrator that routes queries to specialist agents"""

    def __init__(self, llm_provider: BaseLLMProvider, agents: List[BaseAgent]):
        self.llm = llm_provider
        self.agents = {agent.name: agent for agent in agents}
        self.agent_descriptions = self._build_agent_descriptions()

    def _build_agent_descriptions(self) -> str:
        """Build description of available agents for routing"""
        descriptions = []
        for name, agent in self.agents.items():
            descriptions.append(f"""
Agent: {name}
Description: {agent.description}
Capabilities: {', '.join(agent.capabilities)}
""")
        return "\n".join(descriptions)

    async def process_query(self, query: str, context: Optional[Dict] = None) -> Dict:
        """Main entry point - analyze query and route to appropriate agents"""
        # Initialize tracer for this query
        tracer = reset_tracer()
        tracer.log_query_received(query)

        # Extract context values
        project_id = context.get("project_id") if context else None
        skip_cache = context.get("skip_cache", False) if context else False
        data_source = context.get("data_source", "acc") if context else "acc"

        # Check cache first (skip for krion6d/viewer data sources)
        cache = get_cache()
        if cache and not skip_cache:
            cached_result = await cache.get_query_result(query, project_id)
            if cached_result:
                logger.info(f"Cache HIT for query: {query[:50]}...")
                cached_result["from_cache"] = True
                return cached_result

        try:
            # Step 1: Analyze query and determine routing
            tracer.log_routing_start()

            # Short-circuit routing based on data_source
            if data_source == "viewer":
                # Viewer data source always routes to viewer agent
                routing_decision = {
                    "intent": query,
                    "agents": ["viewer"],
                    "refined_query": query,
                    "reasoning": "Request from viewer data source"
                }
            elif data_source == "erp":
                # ERP data source always routes to erp agent
                routing_decision = {
                    "intent": query,
                    "agents": ["erp"],
                    "refined_query": query,
                    "reasoning": "Request from ERP data source — routing to ERP agent for project plan, BOM, and costing analysis"
                }
            else:
                routing_decision = await self._analyze_and_route(query)
                # Prevent viewer/erp agent from being used for non-viewer/erp data sources
                routing_decision["agents"] = [
                    a for a in routing_decision.get("agents", []) if a not in ("viewer", "erp")
                ] or ["data_analyst"]
                if data_source == "krion6d":
                    routing_decision = self._apply_krion6d_review_schedule_routing(
                        query, routing_decision
                    )

            tracer.log_routing_decision(routing_decision)
            logger.info(f"Routing decision: {routing_decision}")

            # Step 2: Execute with selected agents
            agent_results = []
            for agent_name in routing_decision.get('agents', ['data_analyst']):
                if agent_name in self.agents:
                    agent = self.agents[agent_name]
                    logger.info(f"Executing agent: {agent_name}")

                    # Log agent start
                    refined_query = routing_decision.get('refined_query', query)
                    tracer.log_agent_start(agent_name, refined_query)

                    try:
                        result = await agent.process(
                            query=refined_query,
                            context={
                                **(context or {}),
                                'original_query': query,
                                'routing': routing_decision
                            }
                        )

                        # Log agent completion
                        tracer.log_agent_response(
                            agent_name,
                            result.success,
                            result.message or "Completed"
                        )

                        agent_results.append({
                            'agent': agent_name,
                            'result': result
                        })
                    except Exception as e:
                        logger.error(f"Agent {agent_name} failed: {e}")
                        tracer.log_error(f"Agent failed: {str(e)}", agent_name, str(e))

                        agent_results.append({
                            'agent': agent_name,
                            'result': AgentResponse(
                                success=False,
                                data=None,
                                message=f"Agent error: {str(e)}",
                                error=str(e)
                            )
                        })
                else:
                    logger.warning(f"Agent not found: {agent_name}")
                    tracer.log_error(f"Agent not found: {agent_name}")

            # Step 3: Synthesize responses
            tracer.log_synthesis_start(len(agent_results))
            final_response = await self._synthesize_responses(query, agent_results, routing_decision)
            tracer.log_synthesis_complete(final_response.get('agents_used', []))

            # Add interaction logs to response
            final_response['interaction_logs'] = tracer.get_logs()
            final_response['interaction_summary'] = tracer.get_summary()

            # Cache successful results (skip for krion6d/viewer data sources)
            if cache and not skip_cache and final_response.get('success'):
                await cache.set_query_result(query, final_response, project_id)
                logger.info(f"Cached result for query: {query[:50]}...")

            return final_response

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            tracer.log_error(f"Orchestrator error: {str(e)}", error=str(e))

            return {
                'success': False,
                'interpretation': query,
                'data': None,
                'message': f"Error processing query: {str(e)}",
                'charts': [],
                'agents_used': [],
                'error': str(e),
                'interaction_logs': tracer.get_logs(),
                'interaction_summary': tracer.get_summary()
            }

    @staticmethod
    def _apply_krion6d_review_schedule_routing(query: str, routing_decision: Dict) -> Dict:
        """Krion6d loads review workflow rows via list_tasks → schedule; route review/reviews queries there."""
        q = query.lower()
        if not re.search(r"\breviews?\b", q):
            return routing_decision
        # Breakdowns by outcome (pending / completed / rejected) need review_status on workflow
        # entities (issues, RFIs, …), not schedule tasks alone — keep LLM routing (usually data_analyst).
        if OrchestratorAgent._krion6d_review_outcome_breakdown_query(q):
            return routing_decision
        if any(
            phrase in q
            for phrase in (
                "pour card",
                "pourcard",
                "form template",
                "form section",
                "section time",
                "reviewer performance",
                "document file",
                "pdf file",
                ".pdf",
                ".rvt",
                ".dwg",
            )
        ):
            return routing_decision
        if re.search(r"\btat\b", q) or "turnaround" in q:
            return routing_decision
        out = dict(routing_decision)
        out["agents"] = ["schedule"]
        out["krion6d_review_route"] = "schedule"
        prev = out.get("reasoning") or ""
        out["reasoning"] = prev + " [Krion6d: review/reviews use schedule task data]"
        return out

    @staticmethod
    def _krion6d_review_outcome_breakdown_query(q: str) -> bool:
        """True if the user wants counts/categories by review outcome — not listing schedule review tasks."""
        if "categor" in q:
            if any(x in q for x in ("rejected", "completed", "pending", "approved", "answered")):
                return True
        if any(x in q for x in ("breakdown", "break down", "distribution", "bucket")):
            if any(x in q for x in ("rejected", "completed", "pending", "approved", "answered")):
                return True
        if ("rejected" in q and "pending" in q) or ("completed" in q and "pending" in q):
            return True
        if "by rejected" in q or "by pending" in q or "by completed" in q:
            return True
        return False

    async def _analyze_and_route(self, query: str) -> Dict:
        """Analyze query intent and determine which agents to use"""

        system_prompt = f"""You are an orchestrator for a construction data analysis system.

Analyze the user query and determine:
1. The intent/goal of the query
2. Which specialist agent(s) should handle it
3. Any query refinements needed

Available Agents:
{self.agent_descriptions}

Respond ONLY with a valid JSON object (no markdown, no code blocks):
{{
    "intent": "description of what user wants",
    "agents": ["agent_name1"],
    "refined_query": "refined version of query if needed",
    "reasoning": "why these agents were selected"
}}

Rules:
- Choose the most relevant agent(s) for the query
- For safety-related queries (incidents, injuries, hazards), use "safety"
- For schedule-related queries (delays, milestones, timeline, tasks, and schedule Reviews/review items), use "schedule"
- For counts or categories of reviews by outcome (pending vs completed vs rejected / review_status) across project workflow items, use "data_analyst" — not "schedule" alone
- For ERP queries (project plan, BOM, bill of materials, ERP costing, WBS, material costs, upcoming week cost), use "erp"
- For budget/cost queries, use "cost"
- For form templates, pour cards, TAT, turnaround, and reviewer-centric form workflows, use "forms"
- For photos, markups, annotations, and sheets (field photos / markups — not project file repository), use "photos"
- For project document files, PDFs, RVT/Revit/DWG listings, "all files" in the document repository, use "data_analyst" (not photos)
- For meeting minutes and action items, use "meetings"
- For issues, RFIs, RFAs (Request for Approval - different from RFIs), submittals, transmittals, tickets, BOM/BOQ (bill of materials, bill of quantities), or general DATA queries (counts, lists, reports, status), use "data_analyst"
- For transmittals and document distribution, use "data_analyst"
- You can select multiple agents if the query spans multiple domains
- Do NOT route to "viewer" agent - viewer routing is handled separately by the system
"""

        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.3,
                max_tokens=500
            )

            # Parse JSON response
            content = response.content.strip()

            # Handle potential markdown code blocks
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            result = json.loads(content)

            # Validate agents exist
            valid_agents = [a for a in result.get('agents', []) if a in self.agents]
            if not valid_agents:
                valid_agents = ['data_analyst']
            result['agents'] = valid_agents

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse routing response: {e}")
            return self._default_routing(query)
        except Exception as e:
            logger.error(f"Routing error: {e}")
            return self._default_routing(query)

    def _default_routing(self, query: str) -> Dict:
        """Default routing when LLM routing fails"""
        query_lower = query.lower()

        # Simple keyword-based routing
        if any(word in query_lower for word in ['safety', 'incident', 'injury', 'hazard', 'near miss']):
            agent = 'safety'
        elif (
            any(word in query_lower for word in ['schedule', 'delay', 'milestone', 'timeline', 'task', 'progress'])
            or re.search(r'(?<!pre)\breviews?\b', query_lower)
        ):
            agent = 'schedule'
        elif any(word in query_lower for word in ['erp', 'project plan', 'bom', 'bill of material', 'erp costing', 'wbs']):
            agent = 'erp'
        elif any(word in query_lower for word in ['budget', 'cost', 'spend', 'variance', 'forecast', 'financial']):
            agent = 'cost'
        elif any(word in query_lower for word in ['form', 'pour card', 'tat', 'turnaround', 'reviewer']):
            agent = 'forms'
        elif (
            any(
                phrase in query_lower
                for phrase in (
                    'document file',
                    'document files',
                    'pdf file',
                    'pdf files',
                    'rvt',
                    'revit',
                    '.rvt',
                    '.pdf',
                    'dwg',
                    'list all files',
                    'show all files',
                    'all document files',
                    'file extension',
                    'bim file',
                )
            )
            or re.search(r"\b(pdfs?|dwgs?)\b", query_lower)
        ):
            agent = 'data_analyst'
        elif any(word in query_lower for word in ['photo', 'markup', 'annotation', 'sheet']):
            agent = 'photos'
        elif any(word in query_lower for word in ['meeting', 'minutes', 'action item', 'attendee', 'participant']):
            agent = 'meetings'
        elif any(word in query_lower for word in ['transmittal', 'distribution', 'recipient', 'rfa', 'request for approval', 'ticket', 'submittal']):
            agent = 'data_analyst'
        elif any(word in query_lower for word in ['boms','boqs','bill of materials','bill of quantities','bill of quantity']):
            agent = 'data_analyst'
        else:
            agent = 'data_analyst'

        return {
            "intent": query,
            "agents": [agent],
            "refined_query": query,
            "reasoning": "Keyword-based routing (fallback)"
        }

    async def _synthesize_responses(
        self,
        original_query: str,
        agent_results: List[Dict],
        routing_decision: Dict
    ) -> Dict:
        """Combine results from multiple agents into coherent response"""

        if not agent_results:
            return {
                'success': False,
                'interpretation': original_query,
                'data': None,
                'message': 'No agents were able to process the query',
                'charts': [],
                'agents_used': [],
                'routing': routing_decision
            }

        # Single agent - return directly
        if len(agent_results) == 1:
            result = agent_results[0]['result']
            response = {
                'success': result.success,
                'interpretation': routing_decision.get('intent', original_query),
                'data': result.data,
                'message': result.message,
                'charts': result.charts or [],
                'agents_used': [agent_results[0]['agent']],
                'routing': routing_decision,
                'follow_up_questions': (result.metadata or {}).get('follow_up_questions', [])
            }
            # Extract viewer_actions if agent is viewer
            if agent_results[0]['agent'] == 'viewer':
                viewer_actions = []
                if result.metadata and result.metadata.get('viewer_actions'):
                    viewer_actions = result.metadata['viewer_actions']
                elif isinstance(result.data, list) and result.data:
                    if isinstance(result.data[0], dict) and 'operation' in result.data[0]:
                        viewer_actions = result.data
                response['viewer_actions'] = viewer_actions
            return response

        # Multiple agents - combine results
        all_charts = []
        all_data = {}
        messages = []
        overall_success = True

        for ar in agent_results:
            agent_name = ar['agent']
            result = ar['result']

            if not result.success:
                overall_success = False

            if result.charts:
                all_charts.extend(result.charts)

            all_data[agent_name] = result.data
            if result.message:
                messages.append(f"**{agent_name.replace('_', ' ').title()}**: {result.message}")

        # Combine messages
        combined_message = "\n\n".join(messages)

        response = {
            'success': overall_success,
            'interpretation': routing_decision.get('intent', original_query),
            'data': all_data,
            'message': combined_message,
            'charts': all_charts,
            'agents_used': [ar['agent'] for ar in agent_results],
            'routing': routing_decision
        }

        # Extract viewer_actions from viewer agent if present
        all_viewer_actions = []
        for ar in agent_results:
            if ar['agent'] == 'viewer':
                result = ar['result']
                if result.metadata and result.metadata.get('viewer_actions'):
                    all_viewer_actions.extend(result.metadata['viewer_actions'])
                elif isinstance(result.data, list) and result.data:
                    if isinstance(result.data[0], dict) and 'operation' in result.data[0]:
                        all_viewer_actions.extend(result.data)
        if all_viewer_actions:
            response['viewer_actions'] = all_viewer_actions

        # Collect follow-up questions from all agents
        all_follow_ups = []
        for ar in agent_results:
            result = ar['result']
            if result.metadata and result.metadata.get('follow_up_questions'):
                all_follow_ups.extend(result.metadata['follow_up_questions'])
        if all_follow_ups:
            response['follow_up_questions'] = all_follow_ups[:3]

        return response

    def get_available_agents(self) -> List[Dict]:
        """Get information about available agents"""
        return [
            {
                'name': name,
                'description': agent.description,
                'capabilities': agent.capabilities
            }
            for name, agent in self.agents.items()
        ]
