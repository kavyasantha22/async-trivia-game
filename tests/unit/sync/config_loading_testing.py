from pathlib import Path
import sys
import unittest
import json

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from client import Client
from server import load_config


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config_files"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class TestConfigLoading(unittest.TestCase):
    def test_client_config_loading_human(self):
        config = _load_json(CONFIG_DIR / "client_human.json")
        config["mode"] = config["client_mode"]
        config.pop("client_mode")
        client = Client(**config)
        self.assertEqual(client.username, "human-player")
        self.assertEqual(client.mode, "you")

    def test_client_config_loading_auto(self):
        config = _load_json(CONFIG_DIR / "client_bot.json")
        config["mode"] = config["client_mode"]
        config.pop("client_mode")
        client = Client(**config)
        self.assertEqual(client.username, "bot-player")
        self.assertEqual(client.mode, "auto")

    def test_client_config_loading_ai(self):
        config = _load_json(CONFIG_DIR / "client_ai.json")
        config["mode"] = config["client_mode"]
        config.pop("client_mode")
        client = Client(**config) 
        self.assertEqual(client.username, "ollama-player")
        self.assertEqual(client.mode, "ai")
        self.assertEqual(client._ollama_config["ollama_host"], "localhost")
        self.assertEqual(client._ollama_config["ollama_port"], 11434)
        self.assertEqual(client._ollama_config["ollama_model"], "llama2")

    def test_server_config_loading(self):
        server = load_config(CONFIG_DIR / "server_one_player.json")
        self.assertEqual(server._port, 12000)
        self.assertEqual(server._num_players, 1)
        self.assertIn("Mathematics", server._question_types)
        self.assertIn("Roman Numerals", server._question_formats)
