"""
Agent runtime package for loop-oriented orchestration.

This package is intentionally lightweight and designed for progressive migration.
Business tools remain implemented in backend.app and are injected into the loop
controller via callbacks.
"""

from .contracts import (
    AgentStartInput,
    FinalBundle,
    LoopState,
    Observation,
    PlanFrame,
    RetryPolicy,
    RunContext,
    ToolCall,
    ToolSpec,
)
from .planner import AgentPlanner
from .context_manager import AgentContextManager
from .tool_registry import ToolRegistry, build_default_registry
from .executor import AgentExecutor
from .reporter import AgentReporter
from .loop_controller import AgentLoopController, LoopCallbacks

__all__ = [
    "AgentStartInput",
    "FinalBundle",
    "LoopState",
    "Observation",
    "PlanFrame",
    "RetryPolicy",
    "RunContext",
    "ToolCall",
    "ToolSpec",
    "AgentPlanner",
    "AgentContextManager",
    "ToolRegistry",
    "build_default_registry",
    "AgentExecutor",
    "AgentReporter",
    "AgentLoopController",
    "LoopCallbacks",
]

