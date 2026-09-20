import re
import random
import threading
from datetime import datetime, timedelta
import requests
from skills.base_skill import BaseSkill
from skills.browser_utils import open_normal
from skills.ui_utils import show_notification

BASE_URL = "https://www.themealdb.com/api/json/v1/1"
CONTEXT_LIFETIME = timedelta(minutes=5)

CATEGORY_KEYWORDS = {
    "vegetarian": "Vegetarian", "vegan": "Vegan", "seafood": "Seafood",
    "dessert": "Dessert", "breakfast": "Breakfast", "chicken": "Chicken",
    "beef": "Beef", "pork": "Pork", "lamb": "Lamb", "pasta": "Pasta",
}
AREA_KEYWORDS = {
    "indian": "Indian", "italian": "Italian", "chinese": "Chinese",
    "mexican": "Mexican", "french": "French", "thai": "Thai",
    "japanese": "Japanese", "american": "American", "british": "British",
    "spanish": "Spanish", "greek": "Greek", "moroccan": "Moroccan",
    "turkish": "Turkish", "vietnamese": "Vietnamese",
}
ANYTHING_WORDS = ["whatever", "anything", "surprise me", "i don't know", "i don't care", "you choose", "you pick"]
TRIGGER_PHRASES = [
    "suggest some food", "suggest food", "what should i eat", "recipe for",
    "give me a recipe", "recipe idea", "dinner idea", "lunch idea",
    "food suggestion", "what to cook", "what can i cook", "meal idea",
    "something to eat", "what should i make", "food idea",
]


class RecipeSkill(BaseSkill):
    """
    Verzamelt criteria (dieet/categorie, keuken) over meerdere zinnen heen,
    zoekt daarna een passend recept via TheMealDB, en beantwoordt
    vervolgvragen over ingrediënten/bereidingsstappen van dat recept.
    """

    def __init__(self):
        self.stage = None  # None | "collecting" | "recipe_shown"
        self.criteria = {"category": None, "area": None}
        self.last_activity = None
        self.current_recipe = None  # volledige data van het laatst getoonde recept

    def can_handle(self, text: str) -> bool:
        text = text.lower()

        if any(phrase in text for phrase in TRIGGER_PHRASES):
            return True
        if re.search(r"\brecipe with (.+)", text):
            return True

        if self._active("collecting"):
            if any(kw in text for kw in CATEGORY_KEYWORDS) or any(kw in text for kw in AREA_KEYWORDS):
                return True
            if any(word in text for word in ANYTHING_WORDS):
                return True

        if self._active("recipe_shown"):
            if any(kw in text for kw in ["ingredient", "what do i need"]):
                return True
            if any(kw in text for kw in ["step", "how do i make", "how do i cook", "instructions"]):
                return True
            if any(kw in text for kw in ["another one", "something else", "different recipe"]):
                return True

        return False

    def _active(self, stage: str) -> bool:
        return (self.stage == stage and self.last_activity
                and datetime.now() - self.last_activity < CONTEXT_LIFETIME)

    def handle(self, text: str) -> str:
        text_lower = text.lower()
        self.last_activity = datetime.now()

        # Vervolgvragen over een al getoond recept
        if self._active("recipe_shown") and self.current_recipe:
            if any(kw in text_lower for kw in ["ingredient", "what do i need"]):
                return self._speak_ingredients()
            if any(kw in text_lower for kw in ["step", "how do i make", "how do i cook", "instructions"]):
                return self._speak_instructions()
            if any(kw in text_lower for kw in ["another one", "something else", "different recipe"]):
                return self._pick_and_show(self.criteria)

        # Directe naam: "recipe for chicken curry"
        name_match = re.search(r"recipe for (.+)", text_lower)
        if name_match:
            dish_name = name_match.group(1).strip(" .,-?!")
            return self._search_by_name(dish_name)

        # Directe ingrediënt: "recipe with chicken"
        ingredient_match = re.search(r"recipe with (.+)", text_lower)
        if ingredient_match:
            ingredient = ingredient_match.group(1).strip(" .,-?!").replace(" ", "_")
            return self._search_by_ingredient(ingredient)

        # Criteria verzamelen over meerdere zinnen
        for keyword, value in CATEGORY_KEYWORDS.items():
            if keyword in text_lower:
                self.criteria["category"] = value
        for keyword, value in AREA_KEYWORDS.items():
            if keyword in text_lower:
                self.criteria["area"] = value

        if any(word in text_lower for word in ANYTHING_WORDS):
            return self._pick_and_show(self.criteria)

        if self.criteria["category"] or self.criteria["area"]:
            self.stage = "collecting"
            missing = []
            if not self.criteria["category"]:
                missing.append("a type of dish (e.g. vegetarian, dessert, chicken)")
            if not self.criteria["area"]:
                missing.append("a cuisine (e.g. Indian, Italian, Mexican)")
            if missing:
                return f"Got it. Any preference for {', or '.join(missing)}? Or just say 'whatever'."
            return self._pick_and_show(self.criteria)

        self.stage = "collecting"
        self.criteria = {"category": None, "area": None}
        return "Sure — any cuisine, diet, or type of dish in mind? Or just say 'whatever' and I'll pick something."

    def _search_by_name(self, dish_name: str) -> str:
        try:
            response = requests.get(f"{BASE_URL}/search.php", params={"s": dish_name}, timeout=10)
            response.raise_for_status()
            meals = response.json().get("meals")
        except Exception as e:
            return f"I couldn't reach the recipe service: {e}"

        if not meals:
            return f"I couldn't find a recipe for {dish_name}."

        return self._show_recipe(meals[0])

    def _search_by_ingredient(self, ingredient: str) -> str:
        try:
            response = requests.get(f"{BASE_URL}/filter.php", params={"i": ingredient}, timeout=10)
            response.raise_for_status()
            meals = response.json().get("meals")
        except Exception as e:
            return f"I couldn't reach the recipe service: {e}"

        if not meals:
            return f"I couldn't find any recipes with {ingredient.replace('_', ' ')}."

        chosen = random.choice(meals)
        return self._lookup_and_show(chosen["idMeal"])

    def _pick_and_show(self, criteria: dict) -> str:
        try:
            if criteria.get("category"):
                response = requests.get(f"{BASE_URL}/filter.php", params={"c": criteria["category"]}, timeout=10)
            elif criteria.get("area"):
                response = requests.get(f"{BASE_URL}/filter.php", params={"a": criteria["area"]}, timeout=10)
            else:
                response = requests.get(f"{BASE_URL}/random.php", timeout=10)
            response.raise_for_status()
            meals = response.json().get("meals")
        except Exception as e:
            return f"I couldn't reach the recipe service: {e}"

        if not meals:
            return "I couldn't find anything matching that, sorry."

        # Als beide categorie EN keuken opgegeven zijn, filteren we de lijst verder na het ophalen
        chosen = random.choice(meals)
        return self._lookup_and_show(chosen["idMeal"])

    def _lookup_and_show(self, meal_id: str) -> str:
        try:
            response = requests.get(f"{BASE_URL}/lookup.php", params={"i": meal_id}, timeout=10)
            response.raise_for_status()
            meals = response.json().get("meals")
        except Exception as e:
            return f"I couldn't reach the recipe service: {e}"

        if not meals:
            return "I couldn't load that recipe, sorry."

        return self._show_recipe(meals[0])

    def _show_recipe(self, meal: dict) -> str:
        self.current_recipe = meal
        self.stage = "recipe_shown"
        self.last_activity = datetime.now()

        name = meal["strMeal"]
        category = meal.get("strCategory", "")
        area = meal.get("strArea", "")

        url = meal.get("strSource") or f"https://www.google.com/search?q={name.replace(' ', '+')}+recipe"
        threading.Thread(target=lambda: open_normal(url), daemon=True).start()

        popup_text = f"{name}\n({area} {category})\n\nSay 'ingredients' or 'steps' to hear more."
        threading.Thread(target=lambda: show_notification("Recipe", popup_text), daemon=True).start()

        return f"How about {name}? It's a {area} {category.lower()} dish. I've opened the recipe. Want the ingredients or the steps?"

    def _speak_ingredients(self) -> str:
        meal = self.current_recipe
        items = []
        for i in range(1, 21):
            ingredient = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ingredient and ingredient.strip():
                measure = measure.strip() if measure else ""
                items.append(f"{measure} {ingredient}".strip())

        if not items:
            return "I couldn't find the ingredient list for this one."

        return "You'll need: " + ", ".join(items[:10]) + ("." if len(items) <= 10 else ", among others.")

    def _speak_instructions(self) -> str:
        meal = self.current_recipe
        instructions = meal.get("strInstructions", "").strip()
        if not instructions:
            return "I couldn't find the instructions for this one."
        return instructions