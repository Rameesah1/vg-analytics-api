import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv

from src.mcp.server import (
    search_games,
    get_verdict,
    get_controversy,
    get_hidden_gems,
    get_leaderboard,
)

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

router = APIRouter(prefix="/api/ask", tags=["Ask AI"])


def get_anthropic_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is missing")
    return Anthropic(api_key=api_key)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


TOOLS = [
    {
        "name": "search_games",
        "description": "Search for game releases by title or platform. Returns sales and review scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "platform": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
            },
            "required": [],
        },
    },
    {
        "name": "get_verdict",
        "description": "Get the Verdict Machine classification for a specific game release ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "game_release_id": {"type": "string"},
            },
            "required": ["game_release_id"],
        },
    },
    {
        "name": "get_controversy",
        "description": "Get games where critics and players most disagreed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
            },
            "required": [],
        },
    },
    {
        "name": "get_hidden_gems",
        "description": "Get games with high user scores that were overlooked commercially.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
            },
            "required": [],
        },
    },
    {
        "name": "get_leaderboard",
        "description": "Get top games ranked by a metric such as total_sales, meta_score, or user_review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": ["meta_score", "user_review", "total_sales"],
                    "default": "total_sales",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                "platform": {"type": "string"},
                "year_from": {"type": "integer"},
                "year_to": {"type": "integer"},
            },
            "required": [],
        },
    },
]


def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "search_games":
        return search_games(
            title=tool_input.get("title"),
            platform=tool_input.get("platform"),
            limit=tool_input.get("limit", 10),
        )

    if tool_name == "get_verdict":
        return get_verdict(game_release_id=tool_input["game_release_id"])

    if tool_name == "get_controversy":
        return get_controversy(limit=tool_input.get("limit", 10))

    if tool_name == "get_hidden_gems":
        return get_hidden_gems(limit=tool_input.get("limit", 10))

    if tool_name == "get_leaderboard":
        return get_leaderboard(
            metric=tool_input.get("metric", "total_sales"),
            limit=tool_input.get("limit", 10),
            platform=tool_input.get("platform"),
            year_from=tool_input.get("year_from"),
            year_to=tool_input.get("year_to"),
        )

    raise ValueError(f"Unknown tool: {tool_name}")


def normalise_assistant_blocks(blocks) -> list[dict]:
    """
    Convert Anthropic SDK content blocks into plain dictionaries.
    This avoids serialization issues when sending them back in messages.
    """
    normalised = []

    for block in blocks:
        if block.type == "text":
            normalised.append({
                "type": "text",
                "text": block.text,
            })
        elif block.type == "tool_use":
            normalised.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })

    return normalised


@router.post("", response_model=AskResponse)
def ask(request: AskRequest):
    client = get_anthropic_client()

    system_prompt = """
You are an assistant for the Video Game Industry Analytics API.

Rules:
- Use the provided tools whenever the question is about games, rankings, verdicts, controversy, hidden gems, sales, ratings, platforms, or years.
- Never invent database facts.
- If a question is ambiguous, use the best matching tool and explain any assumption.
- Keep answers concise but insightful.
- When useful, summarise patterns instead of just dumping raw records.
- If the available tools cannot answer something, say so clearly.
"""

    try:
        messages = [
            {
                "role": "user",
                "content": request.question,
            }
        ]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        while response.stop_reason == "tool_use":
            assistant_blocks = normalise_assistant_blocks(response.content)
            tool_result_blocks = []

            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)

                    # Keep tool result content as plain text / JSON string
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({
                "role": "assistant",
                "content": assistant_blocks,
            })

            messages.append({
                "role": "user",
                "content": tool_result_blocks,
            })

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=700,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )

        final_text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

        if not final_text:
            final_text = "I couldn't generate an answer."

        return AskResponse(answer=final_text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))