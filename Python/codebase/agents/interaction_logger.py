"""Agent Interaction Logger for tracking and visualizing agent activities"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import time


class InteractionType(str, Enum):
    """Types of agent interactions"""
    QUERY_RECEIVED = "query_received"
    ROUTING_START = "routing_start"
    ROUTING_DECISION = "routing_decision"
    AGENT_START = "agent_start"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_THINKING = "agent_thinking"
    AGENT_RESPONSE = "agent_response"
    SYNTHESIS_START = "synthesis_start"
    SYNTHESIS_COMPLETE = "synthesis_complete"
    ERROR = "error"


@dataclass
class InteractionLog:
    """Single interaction log entry"""
    timestamp: str
    type: InteractionType
    agent: Optional[str]
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "type": self.type.value,
            "agent": self.agent,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms
        }


class InteractionTracer:
    """Traces and logs agent interactions for visualization"""

    def __init__(self):
        self.logs: List[InteractionLog] = []
        self.start_time: Optional[float] = None
        self._timers: Dict[str, float] = {}

    def reset(self):
        """Reset the tracer for a new query"""
        self.logs = []
        self.start_time = time.time()
        self._timers = {}

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()

    def _elapsed_ms(self) -> float:
        """Get elapsed time since start in milliseconds"""
        if self.start_time:
            return round((time.time() - self.start_time) * 1000, 2)
        return 0

    def start_timer(self, key: str):
        """Start a named timer"""
        self._timers[key] = time.time()

    def stop_timer(self, key: str) -> float:
        """Stop a named timer and return duration in ms"""
        if key in self._timers:
            duration = (time.time() - self._timers[key]) * 1000
            del self._timers[key]
            return round(duration, 2)
        return 0

    def log(
        self,
        interaction_type: InteractionType,
        message: str,
        agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ):
        """Add a log entry"""
        entry = InteractionLog(
            timestamp=self._get_timestamp(),
            type=interaction_type,
            agent=agent,
            message=message,
            details=details,
            duration_ms=duration_ms or self._elapsed_ms()
        )
        self.logs.append(entry)

    def log_query_received(self, query: str):
        """Log incoming query"""
        self.reset()
        self.log(
            InteractionType.QUERY_RECEIVED,
            f"Query received: {query[:100]}{'...' if len(query) > 100 else ''}",
            details={"query": query}
        )

    def log_routing_start(self):
        """Log start of routing analysis"""
        self.start_timer("routing")
        self.log(
            InteractionType.ROUTING_START,
            "Analyzing query to determine best agent(s)..."
        )

    def log_routing_decision(self, decision: Dict):
        """Log routing decision"""
        duration = self.stop_timer("routing")
        agents = decision.get("agents", [])
        reasoning = decision.get("reasoning", "")

        self.log(
            InteractionType.ROUTING_DECISION,
            f"Selected agent(s): {', '.join(agents)}",
            details={
                "intent": decision.get("intent"),
                "agents": agents,
                "reasoning": reasoning,
                "refined_query": decision.get("refined_query")
            },
            duration_ms=duration
        )

    def log_agent_start(self, agent_name: str, query: str):
        """Log agent starting processing"""
        self.start_timer(f"agent_{agent_name}")
        self.log(
            InteractionType.AGENT_START,
            f"Starting analysis...",
            agent=agent_name,
            details={"query": query}
        )

    def log_tool_call(self, agent_name: str, tool_name: str, tool_input: Dict):
        """Log a tool being called"""
        self.start_timer(f"tool_{tool_name}")

        # Summarize input for display
        input_summary = self._summarize_dict(tool_input)

        self.log(
            InteractionType.TOOL_CALL,
            f"Calling tool: {tool_name}",
            agent=agent_name,
            details={
                "tool": tool_name,
                "input": tool_input,
                "input_summary": input_summary
            }
        )

    def log_tool_result(self, agent_name: str, tool_name: str, result: Any):
        """Log tool result"""
        duration = self.stop_timer(f"tool_{tool_name}")

        # Summarize result for display
        result_summary = self._summarize_result(result)

        # Build details with source file info if available
        details = {
            "tool": tool_name,
            "result_summary": result_summary,
            "result_count": len(result) if isinstance(result, list) else None
        }

        # Extract source file and table info from result if it's a dict
        if isinstance(result, dict):
            if result.get("source_file"):
                details["source_file"] = result["source_file"]
            if result.get("table"):
                details["table"] = result["table"]
            if result.get("total_rows"):
                details["total_rows"] = result["total_rows"]
            if result.get("returned_rows"):
                details["returned_rows"] = result["returned_rows"]

        self.log(
            InteractionType.TOOL_RESULT,
            f"Tool {tool_name} returned: {result_summary}",
            agent=agent_name,
            details=details,
            duration_ms=duration
        )

    def log_agent_thinking(self, agent_name: str, thought: str):
        """Log agent thinking/reasoning"""
        self.log(
            InteractionType.AGENT_THINKING,
            thought[:200] + "..." if len(thought) > 200 else thought,
            agent=agent_name
        )

    def log_agent_response(self, agent_name: str, success: bool, message: str):
        """Log agent completing"""
        duration = self.stop_timer(f"agent_{agent_name}")
        self.log(
            InteractionType.AGENT_RESPONSE,
            f"{'Completed' if success else 'Failed'}: {message[:150]}{'...' if len(message) > 150 else ''}",
            agent=agent_name,
            details={"success": success},
            duration_ms=duration
        )

    def log_synthesis_start(self, agent_count: int):
        """Log start of response synthesis"""
        self.start_timer("synthesis")
        self.log(
            InteractionType.SYNTHESIS_START,
            f"Synthesizing responses from {agent_count} agent(s)..."
        )

    def log_synthesis_complete(self, agents_used: List[str]):
        """Log synthesis complete"""
        duration = self.stop_timer("synthesis")
        total_duration = self._elapsed_ms()

        self.log(
            InteractionType.SYNTHESIS_COMPLETE,
            f"Response ready (total: {total_duration}ms)",
            details={
                "agents_used": agents_used,
                "total_duration_ms": total_duration
            },
            duration_ms=duration
        )

    def log_error(self, message: str, agent: Optional[str] = None, error: Optional[str] = None):
        """Log an error"""
        self.log(
            InteractionType.ERROR,
            message,
            agent=agent,
            details={"error": error} if error else None
        )

    def _summarize_dict(self, d: Dict, max_items: int = 3) -> str:
        """Summarize a dictionary for display"""
        if not d:
            return "no parameters"

        items = []
        for i, (k, v) in enumerate(d.items()):
            if i >= max_items:
                items.append(f"...+{len(d) - max_items} more")
                break
            if isinstance(v, str) and len(v) > 30:
                v = v[:30] + "..."
            items.append(f"{k}={v}")

        return ", ".join(items)

    def _summarize_result(self, result: Any) -> str:
        """Summarize a result for display"""
        if isinstance(result, list):
            return f"{len(result)} items"
        elif isinstance(result, dict):
            if "error" in result:
                return f"Error: {result['error']}"
            return f"{len(result)} fields"
        elif result is None:
            return "no data"
        else:
            s = str(result)
            return s[:50] + "..." if len(s) > 50 else s

    def get_logs(self) -> List[Dict]:
        """Get all logs as dictionaries"""
        return [log.to_dict() for log in self.logs]

    def get_summary(self) -> Dict:
        """Get a summary of the interaction"""
        tool_calls = [l for l in self.logs if l.type == InteractionType.TOOL_CALL]
        agents = set(l.agent for l in self.logs if l.agent)
        errors = [l for l in self.logs if l.type == InteractionType.ERROR]

        return {
            "total_steps": len(self.logs),
            "agents_involved": list(agents),
            "tool_calls": len(tool_calls),
            "errors": len(errors),
            "total_duration_ms": self._elapsed_ms()
        }


# Global tracer instance
_tracer: Optional[InteractionTracer] = None


def get_tracer() -> InteractionTracer:
    """Get the global tracer instance"""
    global _tracer
    if _tracer is None:
        _tracer = InteractionTracer()
    return _tracer


def reset_tracer() -> InteractionTracer:
    """Reset and return the global tracer"""
    global _tracer
    _tracer = InteractionTracer()
    return _tracer
