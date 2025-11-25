import json
import logging
from typing import Any, List, Optional

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.bedrock.american_word_swap import PARTIAL_WORD_PATTERN, replace_american_words
from app.database.models import Message

logger = logging.getLogger(__name__)


class BedrockStreamInput(BaseModel):
    async_client: AsyncOpenAI
    messages: List[dict]
    max_tokens: int
    model: str
    parse_data: Optional[Any] = None
    user_message: Optional[Message] = None
    system: Optional[str] = None
    on_complete: Any = None
    tools: Optional[List[dict]] = None
    tool_choice: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True


async def bedrock_stream(bedrock_stream_input: BedrockStreamInput):
    full_message = ""
    logger.info("Calling OpenAI stream")

    # Build the API call parameters
    call_params = {
        "model": bedrock_stream_input.model,
        "messages": bedrock_stream_input.messages,
        "max_tokens": bedrock_stream_input.max_tokens,
        "stream": True,
    }

    # Add tools if provided
    if bedrock_stream_input.tools:
        call_params["tools"] = bedrock_stream_input.tools
    if bedrock_stream_input.tool_choice:
        call_params["tool_choice"] = bedrock_stream_input.tool_choice

    stream = await bedrock_stream_input.async_client.chat.completions.create(**call_params)

    remaining_word = ""
    final_response = None

    async for chunk in stream:
        # Get the delta content from the chunk
        if chunk.choices and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta
            text = delta.content if delta.content else ""

            if text:
                text = remaining_word + text

                # Handle partial word splits across chunks
                has_partial_word = PARTIAL_WORD_PATTERN.search(text)
                if has_partial_word:
                    split_index = has_partial_word.start()
                    remaining_word = text[split_index:]  # Save the incomplete word
                    text = text[:split_index]  # Process only complete words
                else:
                    remaining_word = ""

                text = replace_american_words(text)
                full_message += text

                if bedrock_stream_input.parse_data:
                    citations = getattr(bedrock_stream_input.user_message, "citation", None)
                    parsed_data = json.dumps(
                        bedrock_stream_input.parse_data(full_message, citations),
                        indent=4,
                    )
                    yield f"{parsed_data}"
                else:
                    yield text

    # Handle remaining word at end of stream
    if remaining_word:
        text = replace_american_words(remaining_word)
        full_message += text

        if bedrock_stream_input.parse_data:
            citations = getattr(bedrock_stream_input.user_message, "citation", None)
            parsed_data = json.dumps(
                bedrock_stream_input.parse_data(full_message, citations),
                indent=4,
            )
            yield f"{parsed_data}"
        else:
            yield text

    # Create a mock final response object for compatibility with existing code
    # OpenAI streaming doesn't provide usage stats in stream, so we estimate
    class MockUsage:
        def __init__(self):
            # Rough estimation: 1 token ≈ 4 characters
            self.input_tokens = sum(len(str(msg.get("content", ""))) for msg in bedrock_stream_input.messages) // 4
            self.output_tokens = len(full_message) // 4

    class MockContent:
        def __init__(self, text):
            self.text = text

    class MockResponse:
        def __init__(self, text):
            self.content = [MockContent(text)]
            self.usage = MockUsage()

    final_response = MockResponse(full_message)
    logger.debug("Final response is: %s", final_response)
    logger.info("Completed OpenAI stream")

    if bedrock_stream_input.on_complete:
        bedrock_stream_input.on_complete(final_response)
