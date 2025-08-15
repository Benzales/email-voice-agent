from pydantic import BaseModel, Field
from typing import Optional


class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: dict


class InboxEmail(BaseModel):
    id: str
    subject: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias="from")
    date: Optional[str] = None


