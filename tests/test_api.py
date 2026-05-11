from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from mcp.types import TextContent

from api.main import _convert_tool, app


class TestConvertTool:
    def test_full_tool(self):
        tool = MagicMock()
        tool.name = "get_character_info"
        tool.description = "Fetch Pokémon info"
        tool.inputSchema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }

        result = _convert_tool(tool)
        assert result == {
            "type": "function",
            "function": {
                "name": "get_character_info",
                "description": "Fetch Pokémon info",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
            },
        }

    def test_empty_description(self):
        tool = MagicMock()
        tool.name = "test"
        tool.description = ""
        tool.inputSchema = {}

        result = _convert_tool(tool)
        assert result["function"]["description"] == ""

    def test_none_description(self):
        tool = MagicMock()
        tool.name = "test"
        tool.description = None
        tool.inputSchema = {}

        result = _convert_tool(tool)
        assert result["function"]["description"] == ""


class TestConversationEndpoint:
    @pytest.fixture(autouse=True)
    def _mocks(self):
        with (
            patch("api.main.stdio_client") as mock_stdio,
            patch("api.main.ClientSession") as mock_session_cls,
            patch("api.main.chat") as mock_chat,
        ):
            mock_stdio_cm = AsyncMock()
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio_cm.__aenter__.return_value = (mock_read, mock_write)
            mock_stdio.return_value = mock_stdio_cm

            session = AsyncMock()
            session.initialize = AsyncMock()
            session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
            session.call_tool = AsyncMock()

            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__.return_value = session
            mock_session_cls.return_value = mock_session_cm

            self.session = session
            self.chat = mock_chat
            self.client = TestClient(app, raise_server_exceptions=False)
            yield

    def _given_tools(self, *names):
        tools = []
        for name in names:
            t = MagicMock()
            t.name = name
            t.description = f"Tool: {name}"
            t.inputSchema = {"type": "object", "properties": {}}
            tools.append(t)
        self.session.list_tools.return_value = MagicMock(tools=tools)

    def _given_chat_returns_direct(self, content="Hello!"):
        msg = MagicMock(tool_calls=None, content=content)
        self.chat.return_value = MagicMock(message=msg)

    def _given_chat_uses_tool(
        self,
        tool_name="get_it",
        tool_args=None,
        tool_result_text='{"ok": true}',
        final_content="Done.",
    ):
        if tool_args is None:
            tool_args = {"name": "pikachu"}

        tc = MagicMock()
        tc.function.name = tool_name
        tc.function.arguments = tool_args

        msg1 = MagicMock(tool_calls=[tc], content=None)
        resp1 = MagicMock(message=msg1)

        msg2 = MagicMock(tool_calls=None, content=final_content)
        resp2 = MagicMock(message=msg2)

        self.chat.side_effect = [resp1, resp2]

        tc_content = MagicMock(spec=TextContent, text=tool_result_text)
        self.session.call_tool.return_value = MagicMock(content=[tc_content])

    # --- happy path ---

    def test_direct_response(self):
        self._given_tools("get_info")
        self._given_chat_returns_direct("Hi there!")
        resp = self.client.post("/conversation", json={"message": "hello"})
        assert resp.status_code == 200
        assert resp.json() == {"response": "Hi there!"}

    def test_with_tool_call(self):
        self._given_tools("get_character_info")
        self._given_chat_uses_tool(
            tool_name="get_character_info",
            tool_args={"name": "pikachu"},
            tool_result_text='{"name":"Pikachu","type":"electric"}',
            final_content="Pikachu is an Electric-type Pokémon.",
        )
        resp = self.client.post(
            "/conversation", json={"message": "tell me about pikachu"}
        )
        assert resp.status_code == 200
        assert resp.json()["response"] == "Pikachu is an Electric-type Pokémon."
        self.session.call_tool.assert_called_once_with(
            "get_character_info", {"name": "pikachu"}
        )

    def test_multiple_tools_available(self):
        self._given_tools("get_character_info", "get_location")
        self._given_chat_uses_tool(
            tool_name="get_character_info",
            final_content="Found Pikachu!",
        )
        resp = self.client.post("/conversation", json={"message": "find pikachu"})
        assert resp.status_code == 200

    def test_no_tools_defined(self):
        self._given_tools()
        self._given_chat_returns_direct("No tools available.")
        resp = self.client.post("/conversation", json={"message": "hi"})
        assert resp.status_code == 200
        assert resp.json()["response"] == "No tools available."

    def test_empty_message(self):
        self._given_tools("get_info")
        self._given_chat_returns_direct("")
        resp = self.client.post("/conversation", json={"message": ""})
        assert resp.status_code == 200

    def test_none_content_in_response(self):
        self._given_tools("get_info")
        msg = MagicMock(tool_calls=None, content=None)
        self.chat.return_value = MagicMock(message=msg)
        resp = self.client.post("/conversation", json={"message": "hi"})
        assert resp.status_code == 200
        assert resp.json()["response"] == ""

    # --- tool call edge cases ---

    def test_tool_result_with_mixed_content_types(self):
        self._given_tools("get_it")
        tc = MagicMock()
        tc.function.name = "get_it"
        tc.function.arguments = {"x": 1}

        msg1 = MagicMock(tool_calls=[tc], content=None)
        msg2 = MagicMock(tool_calls=None, content="Result")
        self.chat.side_effect = [MagicMock(message=msg1), MagicMock(message=msg2)]

        text_c = MagicMock(spec=TextContent, text="from text")
        non_text = MagicMock(spec=object)
        self.session.call_tool.return_value = MagicMock(content=[text_c, non_text])

        resp = self.client.post("/conversation", json={"message": "go"})
        assert resp.status_code == 200

    def test_tool_result_empty_content_list(self):
        self._given_tools("get_it")
        tc = MagicMock()
        tc.function.name = "get_it"
        tc.function.arguments = {}

        msg1 = MagicMock(tool_calls=[tc], content=None)
        msg2 = MagicMock(tool_calls=None, content="Fallback")
        self.chat.side_effect = [MagicMock(message=msg1), MagicMock(message=msg2)]

        self.session.call_tool.return_value = MagicMock(content=[])

        resp = self.client.post("/conversation", json={"message": "go"})
        assert resp.status_code == 200
        assert resp.json()["response"] == "Fallback"

    def test_multiple_tool_calls_in_one_response(self):
        self._given_tools("tool_a", "tool_b")

        tc1 = MagicMock()
        tc1.function.name = "tool_a"
        tc1.function.arguments = {"x": 1}
        tc2 = MagicMock()
        tc2.function.name = "tool_b"
        tc2.function.arguments = {"y": 2}

        msg1 = MagicMock(tool_calls=[tc1, tc2], content=None)
        msg2 = MagicMock(tool_calls=None, content="Both done")
        self.chat.side_effect = [MagicMock(message=msg1), MagicMock(message=msg2)]

        tc_content = MagicMock(spec=TextContent, text="result")
        self.session.call_tool.return_value = MagicMock(content=[tc_content])

        resp = self.client.post("/conversation", json={"message": "run both"})
        assert resp.status_code == 200
        assert self.session.call_tool.call_count == 2

    # --- error paths ---

    def test_mcp_session_initialize_fails(self):
        self.session.initialize.side_effect = RuntimeError("MCP init failed")
        resp = self.client.post("/conversation", json={"message": "hi"})
        assert resp.status_code == 500

    def test_ollama_chat_fails(self):
        self._given_tools("get_info")
        self.chat.side_effect = Exception("Ollama error")
        resp = self.client.post("/conversation", json={"message": "hi"})
        assert resp.status_code == 500

    def test_tool_call_fails(self):
        self._given_tools("get_it")
        tc = MagicMock()
        tc.function.name = "get_it"
        tc.function.arguments = {}

        msg1 = MagicMock(tool_calls=[tc], content=None)
        self.chat.return_value = MagicMock(message=msg1)

        self.session.call_tool.side_effect = RuntimeError("Tool crashed")

        resp = self.client.post("/conversation", json={"message": "go"})
        assert resp.status_code == 500

    def test_chat_fails_on_second_call(self):
        self._given_tools("get_it")
        tc = MagicMock()
        tc.function.name = "get_it"
        tc.function.arguments = {}

        msg1 = MagicMock(tool_calls=[tc], content=None)
        resp1 = MagicMock(message=msg1)

        self.chat.side_effect = [resp1, Exception("Ollama crashed on final call")]

        tc_content = MagicMock(spec=TextContent, text="result")
        self.session.call_tool.return_value = MagicMock(content=[tc_content])

        resp = self.client.post("/conversation", json={"message": "go"})
        assert resp.status_code == 500
