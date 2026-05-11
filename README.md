# pokeapi-mcp

A MCP server exposing the pokeapi.   
And a chatbot client using the pokeapi MCP server.

## Installation

### Requirements

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Install

```bash
git clone --single-branch --depth 1 https://github.com/fburleson/pokeapi-mcp.git
cd pokeapi-mcp
uv sync --no-dev --frozen
```

## Usage

### Client

```bash
fastapi dev ./src/api/main.py
```

### Server

```bash
uv run mcp dev ./src/server/main.py
```

#### Docker

```bash
docker build -f ./src/server/Dockerfile -t pokeapi-mcp .    # Build image
docker run -p 8050:8050 --name pokeapi-mcp pokeapi-mcp      # Run image
npx @modelcontextprotocol/inspector                         # Run MCPInspector
```