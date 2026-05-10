from unittest.mock import MagicMock, patch

import json

import pytest
import requests

from server.main import get_character_info


@pytest.fixture
def mock_pokeapi_response():
    return {
        "name": "pikachu",
        "height": 4,
        "weight": 60,
        "base_experience": 112,
        "stats": [
            {"base_stat": 35, "effort": 0, "stat": {"name": "hp", "url": "..."}},
            {"base_stat": 55, "effort": 0, "stat": {"name": "attack", "url": "..."}},
            {"base_stat": 40, "effort": 0, "stat": {"name": "defense", "url": "..."}},
            {
                "base_stat": 50,
                "effort": 0,
                "stat": {"name": "special-attack", "url": "..."},
            },
            {
                "base_stat": 50,
                "effort": 0,
                "stat": {"name": "special-defense", "url": "..."},
            },
            {"base_stat": 90, "effort": 2, "stat": {"name": "speed", "url": "..."}},
        ],
        "abilities": [
            {
                "ability": {"name": "static", "url": "..."},
                "is_hidden": False,
                "slot": 1,
            },
            {
                "ability": {"name": "lightning-rod", "url": "..."},
                "is_hidden": True,
                "slot": 3,
            },
        ],
        "types": [
            {"slot": 1, "type": {"name": "electric", "url": "..."}},
        ],
    }


@pytest.fixture
def mock_get():
    with patch("server.main.requests.get") as mock:
        yield mock


class TestGetCharacterInfo:
    def test_success(self, mock_get, mock_pokeapi_response):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_pokeapi_response,
        )
        result = json.loads(get_character_info("pikachu"))
        assert result["name"] == "Pikachu"
        assert result["height"] == 4
        assert result["weight"] == 60
        assert result["base xp"] == 112
        assert result["base_stats"]["hp"] == 35
        assert result["base_stats"]["speed"] == 90
        assert result["abilities"] == ["static", "lightning-rod"]
        assert result["types"] == ["electric"]

    @pytest.mark.parametrize(
        "name",
        ["Pikachu", "PIKACHU", "pIkAcHu"],
        ids=["capitalized", "uppercase", "mixed"],
    )
    def test_case_insensitive(self, mock_get, mock_pokeapi_response, name):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_pokeapi_response,
        )
        result = json.loads(get_character_info(name))
        assert result["name"] == "Pikachu"

    def test_whitespace_handling(self, mock_get, mock_pokeapi_response):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_pokeapi_response,
        )
        result = json.loads(get_character_info("  pikachu  "))
        assert result["name"] == "Pikachu"

    def test_verify_url_uses_lowered_name(self, mock_get, mock_pokeapi_response):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_pokeapi_response,
        )
        get_character_info("CHARIZARD")
        mock_get.assert_called_once_with(
            "https://pokeapi.co/api/v2/pokemon/charizard", timeout=10
        )

    def test_not_found(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)
        result = json.loads(get_character_info("nonexistent"))
        assert result["error"] == "Pokémon 'nonexistent' not found."

    def test_network_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("connection failed")
        result = json.loads(get_character_info("pikachu"))
        assert "Failed to retrieve data from PokeAPI" in result["error"]

    def test_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("timed out")
        result = json.loads(get_character_info("pikachu"))
        assert "Failed to retrieve data from PokeAPI" in result["error"]

    def test_http_500(self, mock_get):
        resp = MagicMock(status_code=500)
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_get.return_value = resp
        result = json.loads(get_character_info("pikachu"))
        assert "Failed to retrieve data from PokeAPI" in result["error"]

    def test_empty_name(self, mock_get):
        mock_get.return_value = MagicMock(status_code=404)
        result = json.loads(get_character_info(""))
        assert "error" in result

    def test_idempotent(self, mock_get, mock_pokeapi_response):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_pokeapi_response,
        )
        r1 = get_character_info("pikachu")
        r2 = get_character_info("pikachu")
        assert r1 == r2
        assert mock_get.call_count == 2

    def test_return_type(self, mock_get, mock_pokeapi_response):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_pokeapi_response,
        )
        result = get_character_info("pikachu")
        assert isinstance(result, str)
        json.loads(result)
