# pokeapi-mcp

A MCP server exposing the pokeapi.   
And a chatbot client using the pokeapi MCP server.

## Installation

### Requirements

- Python 3.13+

### Install

```bash
git clone https://github.com/fburleson/pokeapi-mcp.git
pip install uv
uv sync --no-dev --frozen
```

## Usage

### Server

#### Native

```bash
uv run mcp dev ./src/server/main.py
```

#### Docker

```bash
docker build -f .\src\server\Dockerfile -t pokeapi-mcp .    # Build image
docker run -p 8050:8050 --name pokeapi-mcp pokeapi-mcp      # Run image
npx @modelcontextprotocol/inspector                         # Run MCPInspector
```