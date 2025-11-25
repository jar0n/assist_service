import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel

from app.bedrock.bedrock_stream import BedrockStreamInput, bedrock_stream
from app.bedrock.bedrock_types import AnthropicBedrockProvider, AsyncAnthropicBedrockProvider
from app.bedrock.retry import handle_region_failover_with_retries, with_region_failover_for_streaming
from app.bedrock.schemas import LLMResponse, LLMTransaction
from app.bedrock.service import llm_transaction
from app.config import LLM_DEFAULT_MODEL
from app.database.models import LLM, Message
from app.database.table import LLMTable

logger = logging.getLogger(__name__)


def llm_get_default_model() -> LLM:
    """
    Get the LLM model object from the database where model name is specified by LLM_DEFAULT_MODEL config parameter.
    """
    return LLMTable().get_by_model(LLM_DEFAULT_MODEL)


class RunMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


class Content(BaseModel):
    text: str


class ContentToolUse(BaseModel):
    input: Dict[str, Any]
    type: str


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class Result(BaseModel):
    content: List[Content | ContentToolUse]
    completion_cost: float
    usage: Usage


class ToolResult(BaseModel):
    content: List[Content | ContentToolUse]
    completion_cost: float
    input_tokens: int
    output_tokens: int


class BedrockHandler:
    """Handler for OpenAI API calls. Name kept for backwards compatibility."""

    def __init__(
        self,
        max_tokens=None,
        llm: Optional[LLM] = None,
        mode: RunMode = RunMode.SYNC,
        system=None,
    ):
        """
        Initializes the BedrockHandler instance with the following parameters:

        Args:
            max_tokens (int, optional): Maximum number of tokens for the model's response.
            Defaults to the model's internal `max_tokens` if not provided.
            llm (LLM, optional): An instance of the `LLM` model. If not provided, a default model is assigned.
            mode (RunMode, optional): Indicates the operation mode of the handler, defaults to `RunMode.SYNC`.
            system (str, optional): Optional system configuration for the model.
        """
        # Assign default llm model if no LLM model is provided
        self.llm = llm if llm else llm_get_default_model()

        if not max_tokens:
            max_tokens = self.llm.max_tokens

        if mode == RunMode.SYNC:
            self.client = AnthropicBedrockProvider.get()
        elif mode == RunMode.ASYNC:
            self.async_client = AsyncAnthropicBedrockProvider.get()
        else:
            raise ValueError(f"Invalid client mode: {mode}")

        self.model = self.llm.model
        self.config = {
            "model": self.model,
            "max_tokens": max_tokens,
        }
        self.system = system

    def _convert_messages_to_openai_format(self, messages: List[dict], system: Optional[str] = None) -> List[dict]:
        """
        Convert Anthropic message format to OpenAI format.

        Anthropic format:
        - System prompt is a separate parameter
        - Messages have 'role' and 'content'

        OpenAI format:
        - System prompt is a message with role='system'
        - Messages have 'role' and 'content'
        """
        openai_messages = []

        # Add system message if provided
        if system or self.system:
            openai_messages.append({"role": "system", "content": system or self.system})

        # Convert messages
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            # Handle different content formats
            if isinstance(content, str):
                openai_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle complex content with text blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif "text" in block:
                            text_parts.append(block["text"])
                    elif isinstance(block, str):
                        text_parts.append(block)

                openai_messages.append({"role": role, "content": " ".join(text_parts)})
            else:
                openai_messages.append({"role": role, "content": str(content)})

        return openai_messages

    def _convert_openai_response_to_result(self, response) -> Result:
        """
        Convert OpenAI response to Result format for backwards compatibility.
        """
        # Extract content
        content_list = []
        message = response.choices[0].message

        if message.content:
            content_list.append(Content(text=message.content))

        # Handle tool calls if present
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                import json

                content_list.append(
                    ContentToolUse(
                        input=json.loads(tool_call.function.arguments), type=tool_call.function.name
                    )
                )

        # Extract usage
        usage = Usage(
            input_tokens=response.usage.prompt_tokens, output_tokens=response.usage.completion_tokens
        )

        # Calculate cost (this will be done later in format_response)
        return Result(content=content_list, completion_cost=0.0, usage=usage)

    def format_content_for_chat_title(self, content: str) -> List[dict]:
        """
        Formats the provided content into a list of messages required by OpenAI API.

        Args:
            content (str): The content to be formatted into a chat message.

        Returns:
            List[dict]: A list with a single dictionary with keys 'role' and 'content'.
        """
        messages = []
        title_message = {"role": "user", "content": content}
        messages.append(title_message)
        return messages

    def format_response(self, response: [Result | ToolResult | Message]) -> LLMTransaction:
        if isinstance(response, ToolResult):
            payload = LLMResponse(
                content=response.content,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        elif isinstance(response, Result):
            payload = LLMResponse(
                content=response.content,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        else:
            payload = LLMResponse(
                content=response.content,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

        return llm_transaction(self.llm, payload)

    def _format_chat_title_response(self, response) -> LLMTransaction:
        """Format OpenAI response for chat title."""
        result = LLMResponse(
            content=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
        return llm_transaction(self.llm, result)

    def _convert_tool_choice_to_openai_format(self, tool_choice):
        """
        Convert Anthropic tool_choice format to OpenAI format.

        Anthropic: {"type": "tool", "name": "tool_name"}
        OpenAI: {"type": "function", "function": {"name": "tool_name"}}
        """
        if isinstance(tool_choice, dict):
            if tool_choice.get("type") == "tool" and "name" in tool_choice:
                return {"type": "function", "function": {"name": tool_choice["name"]}}
        return tool_choice

    async def _invoke_async(self, messages, **data) -> Result:
        logger.debug("LLM _invoke_async started")

        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages, data.pop("system", None))

        # Build API call parameters
        call_params = {"model": self.config["model"], "max_tokens": self.config["max_tokens"], "messages": openai_messages}

        # Add any additional parameters from data
        if "tools" in data:
            call_params["tools"] = data["tools"]
        if "tool_choice" in data:
            call_params["tool_choice"] = self._convert_tool_choice_to_openai_format(data["tool_choice"])
        if "temperature" in data:
            call_params["temperature"] = data["temperature"]

        logger.debug(f"Messages sent to LLM: {openai_messages}")

        response = await self.async_client.chat.completions.create(**call_params)
        logger.debug("LLM _invoke_async completed")

        return self._convert_openai_response_to_result(response)

    @handle_region_failover_with_retries
    async def invoke_async(self, messages, **data) -> Result:
        return await self._invoke_async(messages, **data)

    async def _invoke_async_with_call_cost_details(self, messages, **data) -> LLMTransaction:
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages, data.pop("system", None))

        # Build API call parameters
        call_params = {"model": self.config["model"], "max_tokens": self.config["max_tokens"], "messages": openai_messages}

        # Add any additional parameters from data
        if "tools" in data:
            call_params["tools"] = data["tools"]
        if "tool_choice" in data:
            call_params["tool_choice"] = self._convert_tool_choice_to_openai_format(data["tool_choice"])
        if "temperature" in data:
            call_params["temperature"] = data["temperature"]

        response = await self.async_client.chat.completions.create(**call_params)

        result = self._convert_openai_response_to_result(response)
        return self.format_response(result)

    @handle_region_failover_with_retries
    async def invoke_async_with_call_cost_details(self, messages, **data) -> LLMTransaction:
        return await self._invoke_async_with_call_cost_details(messages, **data)

    async def _create_chat_title(self, messages: List[dict]):
        """
        Create a chat title using the LLM model configured in the init.
        Returns a LLMTransaction object encapsulating the title and the cost of generating it.
        """
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages)

        response = await self.async_client.chat.completions.create(
            model=self.config["model"], max_tokens=self.config["max_tokens"], messages=openai_messages
        )
        logger.debug(f"Messages sent to LLM {openai_messages}")
        return self._format_chat_title_response(response)

    @handle_region_failover_with_retries
    async def create_chat_title(self, messages: List[dict]) -> LLMTransaction:
        return await self._create_chat_title(messages)

    def _stream(
        self,
        messages,
        user_message: Message = None,
        system: str = None,
        parse_data=None,
        **data,
    ):
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages, system)

        # Convert tool_choice if present
        tool_choice = data.get("tool_choice")
        if tool_choice:
            tool_choice = self._convert_tool_choice_to_openai_format(tool_choice)

        bedrock_stream_input = BedrockStreamInput(
            async_client=self.async_client,
            messages=openai_messages,
            max_tokens=self.config["max_tokens"],
            model=self.config["model"],
            user_message=user_message,
            system=system,
            parse_data=parse_data,
            tools=data.get("tools"),
            tool_choice=tool_choice,
        )
        return bedrock_stream(bedrock_stream_input)

    def stream(
        self,
        messages,
        on_error: Callable[[Exception], str],
        user_message: Message = None,
        system: str = None,
        parse_data=None,
        **data,
    ):
        return with_region_failover_for_streaming(
            self, self._stream, on_error, messages, user_message, system, parse_data, **data
        )
