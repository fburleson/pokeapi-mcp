import json
import os
from typing import Any

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
SERVER_PORT: str | None = os.getenv("SERVER_PORT")
SERVER_HOST: str | None = os.getenv("SERVER_HOST")


mcp = FastMCP(
    name="pokeapi",
    host=SERVER_HOST if SERVER_HOST is not None else "0.0.0.0",
    port=int(SERVER_PORT) if SERVER_PORT is not None else 8050,
)

POKEAPI_BASE_URL: str = "https://pokeapi.co/api/v2"


@mcp.tool()
def get_character_info(name: str) -> str:
    """Fetch detailed information about a Pokémon by name.

    Retrieves data from the PokéAPI and returns a JSON string with the
    Pokémon's name, height, weight, base experience, stats, abilities,
    and types.

    Args:
        name (str): The name of the Pokémon to look up (case-insensitive).

    Returns:
        str: A JSON-formatted string containing the Pokémon's details,
        or an error message if the Pokémon is not found or the request
        fails.

    Example:
        >>> get_character_info("pikachu")
        '{\n  "name": "Pikachu",\n  "height": 4,\n  ...}'
    """
    url: str = f"{POKEAPI_BASE_URL}/pokemon/{name.lower().strip()}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return json.dumps({"error": f"Pokémon '{name}' not found."}, indent=2)
        response.raise_for_status()
        data = response.json()
        payload: dict[str, Any] = {
            "name": data.get("name").capitalize(),
            "height": data.get("height"),
            "weight": data.get("weight"),
            "base xp": data.get("base_experience"),
            "base_stats": {
                s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])
            },
            "abilities": [a["ability"]["name"] for a in data.get("abilities", [])],
            "types": [t["type"]["name"] for t in data.get("types", [])],
        }
        return json.dumps(payload, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps(
            {"error": f"Failed to retrieve data from PokeAPI: {str(e)}"}, indent=2
        )


if __name__ == "__main__":
    transport: str | None = os.getenv("SERVER_TRANSPORT")
    if transport is None:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=transport)  # type: ignore
