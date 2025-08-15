from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..mcp_bootstrap import get_gmail_agent
from ..utils.gmail_helpers import parse_gmail_search_results


router = APIRouter()


class ExecuteRequest(BaseModel):
    toolName: str
    args: Dict[str, Any] = {}


@router.get("/mcp/tools")
async def list_tools():
    agent = get_gmail_agent()
    try:
        result = await agent.list_tools()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    tools = []
    for tool in getattr(result, 'tools', []) or []:
        input_schema = {}
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            input_schema = {
                k: v for k, v in tool.inputSchema.items() if k not in ["additionalProperties", "$schema"]
            }
        tools.append({
            "name": getattr(tool, 'name', ''),
            "description": getattr(tool, 'description', ''),
            "inputSchema": input_schema,
        })
    return {"tools": tools}


@router.get("/mcp/inbox")
async def inbox(maxResults: int = 50):
    agent = get_gmail_agent()
    try:
        search_result = await agent.call_tool(
            "gmail_search_emails", arguments={"query": "in:inbox", "maxResults": maxResults}
        )
        emails = parse_gmail_search_results(search_result)
        return {"emails": emails}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/execute")
async def execute(req: ExecuteRequest):
    agent = get_gmail_agent()
    try:
        result = await agent.call_tool(req.toolName, arguments=req.args or {})

        # Normalize response text similar to main.py behavior
        response_content = {}
        if hasattr(result, 'content') and result.content:
            text_parts = []
            for content_item in result.content:
                if hasattr(content_item, 'text'):
                    text_parts.append(content_item.text)
            response_content["result"] = "\n".join(text_parts) if text_parts else ""
        else:
            response_content["result"] = "Tool executed successfully"

        return {"ok": True, **response_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


