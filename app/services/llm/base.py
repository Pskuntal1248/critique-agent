"""LLM factory — returns a LangChain chat model based on LLM_PROVIDER setting."""

from langchain_core.language_models import BaseChatModel

from app.core.config import settings
from app.core.constants import ANTHROPIC_MODEL, OPENAI_MODEL


def get_llm(temperature: float = 0.3) -> BaseChatModel:
    """Return the configured LangChain chat model."""
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # noqa: PLC0415

        return ChatAnthropic(
            model=ANTHROPIC_MODEL,
            temperature=temperature,
            anthropic_api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
            max_tokens=4096,
        )

    from langchain_openai import ChatOpenAI  # noqa: PLC0415

    return ChatOpenAI(
        model=OPENAI_MODEL,
        temperature=temperature,
        api_key=settings.openai_api_key,  # type: ignore[arg-type]
        max_tokens=4096,
    )
