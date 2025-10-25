"""
Code Review Workflow Example

This example demonstrates how to create a code review workflow
and optimize it using Taguchi experiments.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
from langgraph.graph import StateGraph

# Note: These imports will work once the package is installed
# from tesseract_flow import BaseWorkflowService
# from tesseract_flow.core.strategies import get_strategy

# For now, we'll use placeholder base class
class BaseWorkflowService:
    """Placeholder - will be imported from tesseract_flow"""
    pass


class CodeReviewInput(BaseModel):
    """Input schema for code review workflow."""
    code: str
    language: str
    context: Optional[str] = None


class Issue(BaseModel):
    """Code issue detected during review."""
    type: str  # "bug", "style", "performance", "security"
    severity: str  # "low", "medium", "high", "critical"
    line_number: Optional[int] = None
    description: str
    suggestion: str


class CodeReviewOutput(BaseModel):
    """Output schema for code review workflow."""
    issues: List[Issue]
    suggestions: List[str]
    quality_score: float  # 0.0 to 1.0


class CodeReviewWorkflow(BaseWorkflowService):
    """
    Code review workflow that analyzes code for issues and suggestions.

    This workflow uses the configured generation strategy (standard, VS, etc.)
    to analyze code and provide feedback.
    """

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph = StateGraph()

        # Define nodes
        graph.add_node("analyze", self._analyze_code)
        graph.add_node("suggest", self._generate_suggestions)
        graph.add_node("score", self._compute_quality_score)

        # Define edges
        graph.add_edge("analyze", "suggest")
        graph.add_edge("suggest", "score")

        # Set entry and exit points
        graph.set_entry_point("analyze")
        graph.set_finish_point("score")

        return graph.compile()

    async def _analyze_code(self, state: dict) -> dict:
        """
        Analyze code for issues using configured generation strategy.

        This node uses the strategy pattern - the specific generation
        technique (standard, CoT, VS) is selected from config.
        """
        strategy = state["strategy"]
        input_data = state["input"]

        # Build analysis prompt
        prompt = self.config.render_prompt("analyze", {
            "code": input_data["code"],
            "language": input_data["language"],
            "context": input_data.get("context", "")
        })

        # Generate using configured strategy
        analysis = await strategy.generate(
            prompt=prompt,
            model=self.model,
            config=self.config.dict()
        )

        state["analysis"] = analysis
        return state

    async def _generate_suggestions(self, state: dict) -> dict:
        """Generate improvement suggestions based on analysis."""
        strategy = state["strategy"]

        prompt = self.config.render_prompt("suggest", {
            "analysis": state["analysis"],
            "code": state["input"]["code"]
        })

        suggestions = await strategy.generate(
            prompt=prompt,
            model=self.model,
            config=self.config.dict()
        )

        state["suggestions"] = suggestions
        return state

    async def _compute_quality_score(self, state: dict) -> dict:
        """
        Compute overall quality score.

        This is a simplified example - real implementation would
        use more sophisticated metrics.
        """
        # Parse issues from analysis
        # (In real implementation, use structured output)
        issues = self._parse_issues(state["analysis"])

        # Simple scoring: penalize for critical/high severity issues
        base_score = 1.0
        for issue in issues:
            if issue.severity == "critical":
                base_score -= 0.15
            elif issue.severity == "high":
                base_score -= 0.10
            elif issue.severity == "medium":
                base_score -= 0.05

        state["quality_score"] = max(0.0, base_score)
        state["issues"] = issues
        return state

    def _parse_issues(self, analysis: str) -> List[Issue]:
        """
        Parse issues from analysis text.

        Real implementation would use structured output or
        parsing library.
        """
        # Placeholder - parse the analysis text
        # In production, use structured output or JSON parsing
        return []

    def _validate_output(self, result: dict) -> CodeReviewOutput:
        """Validate and convert result to output schema."""
        return CodeReviewOutput(
            issues=result.get("issues", []),
            suggestions=result.get("suggestions", "").split("\n"),
            quality_score=result.get("quality_score", 0.0)
        )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Example code to review
        code_input = CodeReviewInput(
            code="""
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item['price']
    return total
            """,
            language="python",
            context="E-commerce shopping cart calculation"
        )

        # Create workflow (config loaded from YAML)
        workflow = CodeReviewWorkflow()

        # Execute workflow
        result = await workflow.execute(code_input)

        print("Code Review Results:")
        print(f"Quality Score: {result.quality_score}")
        print(f"\nIssues Found: {len(result.issues)}")
        for issue in result.issues:
            print(f"  - [{issue.severity}] {issue.description}")
        print(f"\nSuggestions: {len(result.suggestions)}")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")

    asyncio.run(main())
