import json
from pathlib import Path


class MemoryStore:
    """
    Simpele persistente opslag voor gespreksgeschiedenis, als JSON-bestand.
    Weet niks over LLM's of skills - puur lezen/schrijven van data.
    """

    def __init__(self, file_path: str = "memory/conversation_history.json"):
        self.file_path = Path(file_path)

    def load_history(self) -> list:
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def save_history(self, history: list):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)