"""OpenAI-compatible LLM provider implementation."""

from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.errors import EmbeddingError, LLMError
from app.core.logging import get_logger
from app.llm.provider import LLMProvider

settings = get_settings()
logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider implementation."""

    def __init__(self) -> None:
        """Initialize OpenAI provider."""
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
        )
        self.embedding_model = settings.openai_embedding_model
        self.chat_model = settings.openai_chat_model

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            logger.info("Generating embedding", text_length=len(text))
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            embedding = response.data[0].embedding
            logger.info("Embedding generated successfully", dimension=len(embedding))
            return embedding

        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate chat completion.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Expected response format

        Returns:
            Completion response

        Raises:
            LLMError: If completion generation fails
        """
        try:
            logger.info(
                "Generating chat completion",
                message_count=len(messages),
                temperature=temperature,
            )

            kwargs: dict[str, Any] = {
                "model": self.chat_model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            if response_format is not None:
                kwargs["response_format"] = response_format

            response = await self.client.chat.completions.create(**kwargs)

            result = {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            logger.info(
                "Chat completion generated successfully",
                tokens_used=result["usage"]["total_tokens"],
            )

            return result

        except Exception as e:
            logger.error("Failed to generate chat completion", error=str(e))
            raise LLMError(f"Failed to generate chat completion: {str(e)}")


def get_llm_provider() -> LLMProvider:
    """Get LLM provider instance."""
    return OpenAIProvider()
