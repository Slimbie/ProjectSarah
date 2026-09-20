import re
import threading
from datetime import datetime, timedelta
import requests
from skills.base_skill import BaseSkill
from skills.ui_utils import show_notification
from skills.browser_utils import open_incognito, open_normal

WEATHER_CODES = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog with frost",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    56: "light freezing drizzle", 57: "dense freezing drizzle",
    61: "light rain", 63: "moderate rain", 65: "heavy rain",
    66: "light freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "moderate snow", 75: "heavy snow", 77: "snow grains",
    80: "light rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    85: "light snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with light hail", 99: "thunderstorm with heavy hail",
}
RAINY_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SNOWY_CODES = {71, 73, 75, 77, 85, 86}

FOLLOWUP_KEYWORDS = [
    "jacket", "coat", "umbrella", "rain", "raining", "snow", "snowing",
    "run", "running", "jog", "jogging", "bike", "cycle", "cycling",
    "walk", "outside", "cold", "hot", "warm", "sunny", "nice weather",
]
CONTEXT_LIFETIME = timedelta(minutes=15)


def describe_weather_code(code: int) -> str:
    return WEATHER_CODES.get(code, "unknown conditions")


class WeatherSkill(BaseSkill):
    """
    Haalt actueel weer op via de gratis Open-Meteo API en beantwoordt
    ook eenvoudige vervolgvragen ('should I bring a jacket', 'is it
    gonna rain', 'good weather to run') op basis van de laatst
    opgehaalde data - regelgebaseerd, dus geen LLM nodig en snel.
    """

    def __init__(self, default_city: str = "Antwerp"):
        self.default_city = default_city
        self.last_weather = None  # dict met condition/temperature/etc.
        self.last_fetch_time = None

    def can_handle(self, text: str) -> bool:
        text_lower = text.lower()
        if "weather" in text_lower:
            return True
        if self._has_recent_context() and any(kw in text_lower for kw in FOLLOWUP_KEYWORDS):
            return True
        return False

    def handle(self, text: str) -> str:
        text_lower = text.lower()

        if "weather" in text_lower:
            return self._handle_weather_request(text_lower)

        return self._answer_followup(text_lower)

    def _has_recent_context(self) -> bool:
        if not self.last_weather or not self.last_fetch_time:
            return False
        return datetime.now() - self.last_fetch_time < CONTEXT_LIFETIME

    def _handle_weather_request(self, text_lower: str) -> str:
        match = re.search(r"weather in (.+)", text_lower)
        city = match.group(1).strip(" .,-?!") if match else self.default_city

        try:
            lat, lon, resolved_name = self._geocode(city)
        except Exception:
            return f"I couldn't find a location called {city}."

        try:
            data = self._fetch_weather(lat, lon)
        except Exception as e:
            return f"I couldn't reach the weather service: {e}"

        current = data["current"]
        self.last_weather = {
            "city": resolved_name,
            "temperature": round(current["temperature_2m"]),
            "feels_like": round(current["apparent_temperature"]),
            "humidity": current["relative_humidity_2m"],
            "wind": current["wind_speed_10m"],
            "code": current["weather_code"],
        }
        self.last_fetch_time = datetime.now()

        condition = describe_weather_code(self.last_weather["code"])
        rain_note = ""
        if self.last_weather["code"] in RAINY_CODES:
            rain_note = "You'll probably want an umbrella."
        elif self.last_weather["code"] in SNOWY_CODES:
            rain_note = "Expect some snow."

        spoken = (
            f"It's currently {self.last_weather['temperature']} degrees in {resolved_name}, "
            f"with {condition}. It feels like {self.last_weather['feels_like']} degrees. {rain_note}"
        ).strip()

        popup_text = (
            f"Location: {resolved_name}\n"
            f"Condition: {condition}\n"
            f"Temperature: {self.last_weather['temperature']}°C "
            f"(feels like {self.last_weather['feels_like']}°C)\n"
            f"Humidity: {self.last_weather['humidity']}%\n"
            f"Wind: {self.last_weather['wind']} km/h"
        )
        threading.Thread(target=lambda: show_notification("Weather", popup_text), daemon=True).start()
        threading.Thread(target=lambda: open_incognito("https://www.meteo.be/en/weather"), daemon=True).start()

        return spoken

    def _answer_followup(self, text_lower: str) -> str:
        w = self.last_weather
        code = w["code"]
        temp = w["temperature"]
        is_rainy = code in RAINY_CODES
        is_snowy = code in SNOWY_CODES

        if "rain" in text_lower or "raining" in text_lower:
            return "Yes, it looks like rain." if is_rainy else "No rain expected right now."

        if "snow" in text_lower or "snowing" in text_lower:
            return "Yes, there's snow expected." if is_snowy else "No snow expected right now."

        if "jacket" in text_lower or "coat" in text_lower:
            if is_rainy or is_snowy or temp < 12:
                return f"Yes, I'd bring a jacket - it's {temp} degrees with {describe_weather_code(code)}."
            return f"You probably won't need one - it's {temp} degrees and {describe_weather_code(code)}."

        if "umbrella" in text_lower:
            return "Yes, take an umbrella." if is_rainy else "You shouldn't need one."

        if any(w_ in text_lower for w_ in ["run", "running", "jog", "jogging", "bike", "cycle", "cycling", "walk", "outside"]):
            if is_rainy or is_snowy:
                return f"Not ideal - it's {describe_weather_code(code)} right now."
            if temp > 28:
                return f"It's quite warm ({temp} degrees), so stay hydrated if you go."
            if temp < 3:
                return f"It's pretty cold ({temp} degrees), dress warmly if you go."
            return f"Sounds like decent weather for that - {temp} degrees and {describe_weather_code(code)}."

        if any(w_ in text_lower for w_ in ["cold", "hot", "warm", "sunny", "nice weather"]):
            return f"It's {temp} degrees in {w['city']} with {describe_weather_code(code)}."

        return f"Right now it's {temp} degrees in {w['city']} with {describe_weather_code(code)}."

    def _geocode(self, city: str):
        response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results")
        if not results:
            raise ValueError(f"No location found for {city}")
        top = results[0]
        return top["latitude"], top["longitude"], top["name"]

    def _fetch_weather(self, lat: float, lon: float):
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()