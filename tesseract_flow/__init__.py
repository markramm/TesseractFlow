"""
TesseractFlow - Multi-dimensional LLM Workflow Optimization

A framework for systematic LLM workflow optimization using Taguchi Design of Experiments.
"""

__version__ = "0.1.1"

from tesseract_flow.core.base_workflow import BaseWorkflowService
from tesseract_flow.core.config import WorkflowConfig
from tesseract_flow.core.strategies import (
    GENERATION_STRATEGIES,
    GenerationStrategy,
    get_strategy,
    register_strategy,
)
from tesseract_flow.workflows import CodeIssue, CodeReviewInput, CodeReviewOutput, CodeReviewWorkflow

__all__ = [
    "BaseWorkflowService",
    "WorkflowConfig",
    "GENERATION_STRATEGIES",
    "get_strategy",
    "register_strategy",
    "GenerationStrategy",
    "CodeReviewWorkflow",
    "CodeReviewInput",
    "CodeReviewOutput",
    "CodeIssue",
]
