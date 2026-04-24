"""Base agent class — all pipeline agents extend this."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import litellm
from pydantic_ai import Agent, AgentRunResult
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.litellm import LiteLLMProvider

# Allow LiteLLM to restructure messages for provider compatibility
# (e.g. Bedrock requires conversations to start with a user message).
litellm.modify_params = True

TOutput = TypeVar("TOutput")


class BaseAgent(ABC, Generic[TOutput]):
    _DEFAULT_MODEL = "gemini/gemini-2.5-flash"

    @property
    @abstractmethod
    def instructions(self) -> str: ...

    @property
    def constraints(self) -> list[str]:
        return []

    @property
    def system_prompt(self) -> str:
        prompt = self.instructions
        if self.constraints:
            items = "\n".join(f"- {c}" for c in self.constraints)
            prompt += f"\n\nConstraints:\n{items}"
        return prompt

    @staticmethod
    def build_model(model_name: str | None = None) -> OpenAIModel:
        resolved = model_name or os.environ.get("ADK_MODEL", BaseAgent._DEFAULT_MODEL)
        provider = LiteLLMProvider(
            api_base=os.environ.get("LITELLM_BASE_URL"),
            api_key=os.environ.get("LITELLM_API_KEY"),
        )
        return OpenAIModel(resolved, provider=provider)

    def __init__(
        self,
        output_type: type[TOutput],
        model_name: str | None = None,
        agent_name: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        # Subclasses may pass system_prompt explicitly to avoid relying on
        # property resolution order during construction (e.g. ScoutAgent).
        resolved_prompt = system_prompt if system_prompt is not None else self.system_prompt
        self.agent: Agent[None, TOutput] = Agent(
            model=self.build_model(model_name),
            name=agent_name or self.__class__.__name__,
            output_type=output_type,
            system_prompt=resolved_prompt,
        )

    def run_sync(self, prompt: str, **kwargs) -> AgentRunResult[TOutput]:
        return self.agent.run_sync(prompt, **kwargs)

    async def run(self, prompt: str, **kwargs) -> AgentRunResult[TOutput]:
        return await self.agent.run(prompt, **kwargs)
