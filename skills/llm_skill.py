import requests
from skills.base_skill import BaseSkill
from memory.store import MemoryStore


class LlmSkill(BaseSkill):
    """
    Vangt alles op wat geen enkele andere skill herkent. Stuurt de vraag
    (met gespreksgeschiedenis) naar het lokale Ollama-model.
    Moet altijd als LAATSTE in de skills-lijst staan in main.py.
    """

    def __init__(self, model: str = "llama3.2:1b", user_name: str = "Sonny",
                 max_turns: int = 6, memory_store: MemoryStore = None):
        self.model = model
        self.url = "http://localhost:11434/api/chat"
        self.max_turns = max_turns
        self.system_prompt = (
            f"You are Sarah, a helpful local voice assistant. You run on {user_name}'s "
            "laptop, an HP Laptop 15-db1xxx with 8GB RAM and no dedicated GPU, running "
            f"Ubuntu Linux. The user's name is {user_name}. Keep answers short and "
            "conversational, since they will be spoken aloud by a text-to-speech system."
        )

        self.memory_store = memory_store or MemoryStore()
        self.history = self.memory_store.load_history()

    def can_handle(self, text: str) -> bool:
        return True

    def handle(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})
        recent_history = self.history[-(self.max_turns * 2):]
        messages = [{"role": "system", "content": self.system_prompt}] + recent_history

        try:
            response = requests.post(
                self.url,
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=30,
            )
            response.raise_for_status()
            answer = response.json()["message"]["content"].strip()
            self.history.append({"role": "assistant", "content": answer})
            self.memory_store.save_history(self.history)
            return answer
        except requests.exceptions.RequestException as e:
            return f"Ik kan het LLM nu niet bereiken: {e}"