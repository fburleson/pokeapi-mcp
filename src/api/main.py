import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.types import TextContent
from ollama import chat
from pydantic import BaseModel

load_dotenv()

MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

app = FastAPI(title="PokeAPI MCP Conversation API")


class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    response: str


def _convert_tool(tool):
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


@asynccontextmanager
async def _mcp_session() -> AsyncIterator[ClientSession]:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(PROJECT_ROOT / "src" / "server" / "main.py")],
        cwd=PROJECT_ROOT,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@app.post("/conversation")
async def conversation(body: MessageRequest) -> MessageResponse:
    async with _mcp_session() as session:
        tools = (await session.list_tools()).tools
        ollama_tools = [_convert_tool(t) for t in tools]

        messages = [{"role": "user", "content": body.message}]

        response = await asyncio.to_thread(
            chat,
            model=MODEL_NAME,
            messages=messages,
            tools=ollama_tools or None,
        )

        msg = response.message

        if msg.tool_calls:
            for tc in msg.tool_calls:
                result = await session.call_tool(
                    tc.function.name, dict(tc.function.arguments)
                )
                content_parts = [
                    c.text for c in result.content if isinstance(c, TextContent)
                ]
                messages.append({"role": "tool", "content": "\n".join(content_parts)})
            final = await asyncio.to_thread(chat, model=MODEL_NAME, messages=messages)
            return MessageResponse(response=final.message.content or "")

        return MessageResponse(response=msg.content or "")
