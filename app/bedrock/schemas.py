from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class TextBlock(BaseModel):
    """Generic text block for LLM responses"""

    type: str = "text"
    text: str


class ToolUseBlock(BaseModel):
    """Generic tool use block for LLM responses"""

    type: str = "tool_use"
    id: Optional[str] = None
    name: str
    input: Dict[str, Any]


class LLMResponse(BaseModel):
    content: Union[str, List[Optional[Union[str, TextBlock, ToolUseBlock]]]]
    input_tokens: int
    output_tokens: int


class LLMTransaction(LLMResponse):
    input_cost: float
    output_cost: float
    completion_cost: float
