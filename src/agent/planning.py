"""
Planning engine for the autonomous agent.

This module contains the logic for breaking down high-level goals into actionable steps,
and dynamically adjusting the plan based on step outcomes.
"""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Step(BaseModel):
    """Represents a single step in the agent's plan."""
    id: str = Field(..., description="Unique identifier for this step")
    description: str = Field(..., description="Human-readable description of the step")
    status: str = Field("pending", description="Current status of the step: pending, in_progress, completed, failed")
    action_type: str = Field(..., description="Type of action: terminal_command, browser_action, etc.")
    action_params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")
    result: Optional[Dict[str, Any]] = Field(None, description="Result of executing this step")
    created_at: str = Field(..., description="ISO timestamp when this step was created")
    started_at: Optional[str] = Field(None, description="ISO timestamp when execution of this step started")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when execution of this step completed")


class Plan(BaseModel):
    """Represents the full plan for accomplishing a goal."""
    id: str = Field(..., description="Unique identifier for this plan")
    goal: str = Field(..., description="The original user goal to accomplish")
    status: str = Field("planning", description="Current status of the plan: planning, in_progress, completed, failed")
    steps: List[Step] = Field(default_factory=list, description="Ordered list of steps to execute")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contextual information gathered during execution")
    created_at: str = Field(..., description="ISO timestamp when this plan was created")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when this plan was completed")


class PlanningEngine:
    """
    The planning engine is responsible for breaking down high-level goals into actionable steps,
    and dynamically adjusting the plan based on step outcomes.
    """

    def __init__(self, model_client):
        """
        Initialize the planning engine.

        Args:
            model_client: A client for the LLM to use for planning.
        """
        self.model_client = model_client

    async def create_initial_plan(self, goal: str) -> Plan:
        """
        Create an initial plan for accomplishing the given goal.

        Args:
            goal: The user's goal in natural language.

        Returns:
            A Plan object containing the steps to accomplish the goal.
        """
        # In a real implementation, this would involve:
        # 1. Sending the goal to the LLM with a prompt for planning
        # 2. Parsing the LLM's response into a structured plan
        # 3. Validating the plan steps are executable

        # For MVP, we'll implement a simplified version that calls the model
        # and structures the response into a Plan

        prompt = self._build_planning_prompt(goal)
        response = await self.model_client.generate(prompt)
        plan = self._parse_plan_from_response(response, goal)

        return plan

    async def update_plan(self, plan: Plan, latest_step: Step) -> Plan:
        """
        Update a plan based on the outcome of the latest step.

        Args:
            plan: The current plan.
            latest_step: The most recently executed step.

        Returns:
            An updated Plan object with potentially modified steps.
        """
        # In a real implementation, this would:
        # 1. Analyze the latest step's outcome
        # 2. Decide if the plan needs to change
        # 3. Generate new or modified steps if needed

        # For MVP, we might implement a simpler version:
        if latest_step.status == "failed":
            # If a step failed, ask the LLM for an alternative approach
            prompt = self._build_replanning_prompt(plan, latest_step)
            response = await self.model_client.generate(prompt)
            updated_plan = self._parse_updated_plan(response, plan)
            return updated_plan

        # If the step succeeded, we might just return the original plan
        # In a more advanced implementation, we'd adapt based on new information too
        return plan

    def _build_planning_prompt(self, goal: str) -> str:
        """Build a prompt for the initial planning."""
        return f"""
        You are an autonomous agent that helps users accomplish their goals.
        Given the following goal, create a detailed step-by-step plan to accomplish it.

        User's Goal: {goal}

        For each step, specify:
        1. A clear description of what to do
        2. What type of action it is (terminal_command or browser_action)
        3. The specific parameters needed for that action

        Respond in JSON format like this:
        {{
            "steps": [
                {{
                    "description": "Step description",
                    "action_type": "terminal_command",
                    "action_params": {{
                        "command": "actual command to run"
                    }}
                }},
                {{
                    "description": "Another step description",
                    "action_type": "browser_action",
                    "action_params": {{
                        "url": "https://example.com",
                        "action": "navigate"
                    }}
                }}
            ]
        }}
        """

    def _build_replanning_prompt(self, plan: Plan, failed_step: Step) -> str:
        """Build a prompt for replanning after a failed step."""
        plan_json = json.dumps(plan.dict(), indent=2)
        failed_step_json = json.dumps(failed_step.dict(), indent=2)

        return f"""
        You are an autonomous agent that helps users accomplish their goals.
        A step in your plan has failed. Please analyze what went wrong and suggest a new approach.

        Original Plan:
        {plan_json}

        Failed Step:
        {failed_step_json}

        Please provide an updated plan that addresses this failure. You can:
        1. Modify the failed step to try a different approach
        2. Replace the failed step with alternative steps
        3. Adjust subsequent steps as needed

        Respond in JSON format with the complete updated plan.
        """

    def _parse_plan_from_response(self, response: str, goal: str) -> Plan:
        """Parse the LLM's response into a Plan object."""
        # In a real implementation, this would include error handling,
        # validation, and more sophisticated parsing

        # This is a simplified example:
        try:
            response_json = json.loads(response)

            import datetime
            import uuid

            now = datetime.datetime.utcnow().isoformat()
            plan_id = str(uuid.uuid4())

            steps = []
            for i, step_data in enumerate(response_json.get("steps", [])):
                step = Step(
                    id=f"{plan_id}-step-{i}",
                    description=step_data["description"],
                    action_type=step_data["action_type"],
                    action_params=step_data["action_params"],
                    created_at=now
                )
                steps.append(step)

            plan = Plan(
                id=plan_id,
                goal=goal,
                steps=steps,
                created_at=now
            )

            return plan

        except Exception as e:
            # In a real implementation, we'd have better error handling
            # For now, create a simple error plan
            return Plan(
                id=str(uuid.uuid4()),
                goal=goal,
                status="failed",
                steps=[],
                context={"error": f"Failed to parse plan: {str(e)}"},
                created_at=datetime.datetime.utcnow().isoformat()
            )

    def _parse_updated_plan(self, response: str, original_plan: Plan) -> Plan:
        """Parse the LLM's response into an updated Plan object."""
        # This would be similar to _parse_plan_from_response but would
        # preserve the original plan's ID and other metadata

        # For MVP, we might just implement a simple version
        try:
            response_json = json.loads(response)

            # Create a copy of the original plan and update its steps
            updated_plan = original_plan.copy(deep=True)

            # Update steps based on the response
            # This is simplified - a real implementation would be more sophisticated
            if "steps" in response_json:
                import datetime
                now = datetime.datetime.utcnow().isoformat()

                new_steps = []
                for i, step_data in enumerate(response_json["steps"]):
                    # Preserve completed steps
                    if i < len(updated_plan.steps) and updated_plan.steps[i].status == "completed":
                        new_steps.append(updated_plan.steps[i])
                        continue

                    # Replace or add new steps
                    step = Step(
                        id=f"{updated_plan.id}-step-{i}",
                        description=step_data["description"],
                        action_type=step_data["action_type"],
                        action_params=step_data["action_params"],
                        created_at=now
                    )
                    new_steps.append(step)

                updated_plan.steps = new_steps
                updated_plan.status = "in_progress"

            return updated_plan

        except Exception as e:
            # If parsing fails, return the original plan with an error in context
            original_plan.context["replanning_error"] = str(e)
            return original_plan