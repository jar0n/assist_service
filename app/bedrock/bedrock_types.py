# ruff: noqa: A005
from enum import Enum, auto
from typing import Optional

import httpx
from openai import OpenAI, AsyncOpenAI

from app.config import OPENAI_API_KEY, OPENAI_API_BASE

OPENAI_API_READ_TIMEOUT_SECS = 115
OPENAI_API_CONNECT_TIMEOUT_SECS = 3


class BedrockErrorType(str, Enum):
    INPUT_TOO_LONG = auto()
    BEDROCK_AGENT_EXCEPTION = auto()


class BedrockError(Exception):
    """Base class for all OpenAI/LLM exceptions."""

    def __init__(self, msg: str, error_type: Optional[BedrockErrorType] = None):
        super().__init__(msg)
        self.error_type = error_type


class AnthropicBedrockProvider:
    """
    Provides a single instance of OpenAI sync client.
    It creates a new instance on first call and returns existing client on subsequent calls.
    Note: Name kept for backwards compatibility.
    """

    __client = None

    @classmethod
    def get(cls, _aws_region: str = None) -> OpenAI:
        """Get or create OpenAI sync client. Region parameter ignored for OpenAI."""
        if cls.__client is None:
            cls.__client = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_API_BASE,
                max_retries=0,
                timeout=httpx.Timeout(timeout=OPENAI_API_READ_TIMEOUT_SECS, connect=OPENAI_API_CONNECT_TIMEOUT_SECS),
            )
        return cls.__client


class AsyncAnthropicBedrockProvider:
    """
    Provides a single instance of OpenAI async client.
    It creates a new instance on first call and returns existing client on subsequent calls.
    Note: Name kept for backwards compatibility.
    """

    __client = None

    @classmethod
    def get(cls, _aws_region: str = None) -> AsyncOpenAI:
        """Get or create OpenAI async client. Region parameter ignored for OpenAI."""
        if cls.__client is None:
            cls.__client = AsyncOpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_API_BASE,
                max_retries=0,
                timeout=httpx.Timeout(timeout=OPENAI_API_READ_TIMEOUT_SECS, connect=OPENAI_API_CONNECT_TIMEOUT_SECS),
            )
        return cls.__client
