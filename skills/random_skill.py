import random
import re
import tkinter as tk
from skills.base_skill import BaseSkill


class RandomSkill(BaseSkill):
    """
    Muntje flippen, dobbelsteen rollen, of een willekeurig getal geven,
    met een kort animatie-schermpje (~1,5 sec) dat snel door de opties
    heen wisselt voor het op de uitkomst landt. Blokkeert bewust kort
    tijdens die animatie, zodat het gesproken antwoord altijd matcht
    met wat je op het scherm ziet.
    """

    NUMBER_PATTERN = re.compile(r"number between (\d+) and (\d+)")

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        if "flip" in text and "coin" in text:
            return True
        if "roll" in text and ("dice" in text or "die" in text):
            return True
        if self.NUMBER_PATTERN.search(text):
            return True
        return False

    def handle(self, text: str) -> str:
        text_lower = text.lower()

        if "flip" in text_lower and "coin" in text_lower:
            result = random.choice(["Heads", "Tails"])
            self._animate(options=["Heads", "Tails"], final_value=result, title="Coin Flip")
            return f"It's {result}."

        if "roll" in text_lower and ("dice" in text_lower or "die" in text_lower):
            result = random.randint(1, 6)
            self._animate(options=[str(n) for n in range(1, 7)], final_value=str(result), title="Dice Roll")
            return f"You rolled a {result}."

        match = self.NUMBER_PATTERN.search(text_lower)
        if match:
            low, high = int(match.group(1)), int(match.group(2))
            if low > high:
                low, high = high, low
            result = random.randint(low, high)
            self._animate(number_range=(low, high), final_value=str(result), title="Random Number")
            return f"Your number is {result}."

        return "I couldn't generate that."

    def _animate(self, final_value: str, title: str, options=None, number_range=None, steps: int = 14, interval: int = 90):
        root = tk.Tk()
        root.title(title)
        root.geometry("220x120")
        root.attributes("-topmost", True)

        label = tk.Label(root, text="...", font=("Sans", 28))
        label.pack(expand=True)

        def tick(step):
            if step >= steps:
                label.config(text=final_value, font=("Sans", 32, "bold"))
                root.after(900, root.destroy)
                return

            display_value = random.randint(*number_range) if number_range else random.choice(options)
            label.config(text=str(display_value))
            root.after(interval, lambda: tick(step + 1))

        tick(0)
        root.mainloop()