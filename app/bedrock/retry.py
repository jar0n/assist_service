import logging
from asyncio import iscoroutinefunction
from functools import wraps
from typing import TYPE_CHECKING, Callable

from app.bedrock.bedrock_types import BedrockError, BedrockErrorType

if TYPE_CHECKING:
    from app.bedrock.bedrock import BedrockHandler

OPENAI_MAX_RETRIES: int = 3

logger = logging.getLogger()


def handle_region_failover_with_retries(func):
    """
    Decorator that handles retries when making OpenAI API calls.
    Note: Name kept for backwards compatibility with existing code.

    Args:
        func: The function to retry on failure

    Returns:
        A decorated function that retries the operation

    Raises:
        BedrockError: If the operation fails after the specified number of retries
    """

    @wraps(func)
    def wrapper(bedrock_handler: "BedrockHandler", *args, **kwargs):
        """Wrapper function for retrying the decorated function."""
        retries = 0
        ex = None

        while retries < OPENAI_MAX_RETRIES:
            try:
                return func(bedrock_handler, *args, **kwargs)
            except Exception as e:
                logger.warning(f"OpenAI API call failed (attempt {retries + 1}/{OPENAI_MAX_RETRIES}): {e}")
                retries += 1
                ex = e

        logger.error("OpenAI API call failed after all retries, last exception: %s", ex)
        raise BedrockError(f"OpenAI API call failed, last exception: {str(ex)}") from ex

    @wraps(func)
    async def async_wrapper(bedrock_handler: "BedrockHandler", *args, **kwargs):
        """Asynchronous wrapper function for retrying the decorated function."""
        retries = 0
        ex = None

        while retries < OPENAI_MAX_RETRIES:
            try:
                return await func(bedrock_handler, *args, **kwargs)
            except Exception as e:
                logger.warning(f"OpenAI API call failed (attempt {retries + 1}/{OPENAI_MAX_RETRIES}): {e}")
                retries += 1
                ex = e

        logger.exception("OpenAI API call failed after all retries, last exception: %s", ex)
        raise BedrockError(f"OpenAI API call failed, last exception: {str(ex)}") from ex

    # check which wrapper to use
    return async_wrapper if iscoroutinefunction(func) else wrapper


async def with_region_failover_for_streaming(
    bedrock_handler: "BedrockHandler",
    func,
    on_error: Callable[[Exception], str],
    *args,
    **kwargs,
):
    """
    Handles retries for streaming OpenAI API calls.
    Note: Name kept for backwards compatibility with existing code.

    If streaming encounters an error after it has started, on_error function is used
    to generate a custom error json msg.

    Args:
        bedrock_handler: The handler for OpenAI API calls
        func: The streaming Generator function that generates json strings
        on_error: The function taking an exception and generating a json string,
                  used when an error encountered after the streaming has started
        *args: Positional arguments passed to the decorated function
        **kwargs: Keyword arguments passed to the decorated function

    Raises:
        BedrockError: If the operation fails after the specified number of retries

    Returns:
        The result of the streaming function if no errors
    """
    retries = 0
    ex = None

    while retries < OPENAI_MAX_RETRIES:
        streaming_started = False
        try:
            async for item in func(*args, **kwargs):
                yield item
                streaming_started = True
            # Exit while loop when streaming is completed
            return
        except Exception as e:
            ex = e
            ex_msg = f"{e}"

            # Check if error is due to large input (context length exceeded)
            if "context_length_exceeded" in ex_msg or "maximum context length" in ex_msg.lower():
                error_msg = "Input is too long"
                logger.error(f"{error_msg}: {type(ex)}: {ex}")
                yield on_error(BedrockError(error_msg, BedrockErrorType.INPUT_TOO_LONG))
                return

            # If error happened at the beginning of streaming, retry
            if not streaming_started:
                logger.warning(f"OpenAI streaming failed (attempt {retries + 1}/{OPENAI_MAX_RETRIES}): {ex}")
                retries += 1
            else:
                # Stream a custom error message payload if exception happened midway through streaming
                yield on_error(e)
                logger.error("OpenAI error through streaming, exception: %s", ex)
                return

    # All attempts failed
    logger.error("OpenAI streaming call failed after all retries, last exception: %s:%s", type(ex), ex)
    yield on_error(ex)
