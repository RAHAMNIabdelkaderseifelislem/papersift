"""LLMProvider base interface."""

from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """
    Abstract base class for all AI language model providers.

    Every provider (Ollama, Gemini, OpenAI-compatible)
    must implement the generate method.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response using the selected AI model.

        Args:
            prompt: User prompt.
            system_prompt: Optional system instructions.
            temperature: Controls response randomness.
            max_tokens: Maximum number of generated tokens.

        Returns:
            Generated text response.
        """
        pass