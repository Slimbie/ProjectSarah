import re
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import requests
from skills.base_skill import BaseSkill
from skills.ui_utils import show_notification

FEEDS = {
    "top": "http://feeds.bbci.co.uk/news/rss.xml",
    "world": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "sport": "http://feeds.bbci.co.uk/sport/rss.xml",
    "science": "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
}

# Alleen ECHTE brede categorieën hier - specifieke namen (NASA, SpaceX, personen,
# landen, gebeurtenissen) horen bij de zoek-route, niet bij een topic-feed.
TOPIC_KEYWORDS = {
    "world": ["world news", "international news", "global news"],
    "technology": ["technology", "tech news"],
    "business": ["business", "economy", "economic", "finance", "market"],
    "sport": ["sport", "sports"],
    "science": ["science", "scientific"],
}

TRIGGER_PHRASES = ["news", "update", "what's happening", "headlines"]
FOLLOWUP_PHRASES = [
    "tell me more about", "more about", "more info about", "info about",
    "is there anything about", "is there info about", "anything on", "what about",
]
NAMED_QUERY_PATTERN = re.compile(r"news (?:about|on|regarding) (.+)")
SEARCH_FEEDS = ["top", "world", "science", "technology", "business"]
CONTEXT_LIFETIME = timedelta(minutes=15)

GROUNDING_RULE = (
    "Only use information that is literally present in the text below. "
    "Do not add facts, dates, numbers, or context from your own background knowledge, "
    "even if you think you know more about the topic. If the text doesn't say it, don't say it. "
    "Never mention the same story more than once, even in different words."
)


class NewsSkill(BaseSkill):
    """
    Haalt actuele koppen op via gratis BBC RSS-feeds. Brede categorieën
    (technology, science, sport, ...) gebruiken de bijpassende topic-feed;
    specifieke namen/onderwerpen (NASA, een land, een gebeurtenis) worden
    doorzocht over meerdere feeds. Strikt gegrond op de opgehaalde tekst.
    """

    def __init__(self, model: str = "llama3.2:1b", default_topic: str = "top"):
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        self.default_topic = default_topic
        self.last_items = []
        self.last_topic = None
        self.last_fetch_time = None

    def can_handle(self, text: str) -> bool:
        text_lower = text.lower()
        if any(phrase in text_lower for phrase in TRIGGER_PHRASES):
            return True
        if self._has_recent_context() and any(phrase in text_lower for phrase in FOLLOWUP_PHRASES):
            return True
        return False

    def handle(self, text: str) -> str:
        text_lower = text.lower()

        if any(phrase in text_lower for phrase in TRIGGER_PHRASES):
            return self._handle_news_request(text_lower)

        return self._answer_followup(text_lower)

    def _has_recent_context(self) -> bool:
        if not self.last_items or not self.last_fetch_time:
            return False
        return datetime.now() - self.last_fetch_time < CONTEXT_LIFETIME

    def _match_topic(self, text: str):
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return topic
        return None

    def _fetch_items(self, url: str, limit: int = 10) -> list:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall(".//item")[:limit]
        result = []
        for item in items:
            title_el = item.find("title")
            desc_el = item.find("description")
            if title_el is not None and title_el.text:
                result.append({
                    "title": title_el.text,
                    "description": desc_el.text if desc_el is not None and desc_el.text else "",
                })
        return result

    def _handle_news_request(self, text_lower: str) -> str:
        # Specifiek genoemd onderwerp ("news about NASA") heeft voorrang
        # boven brede categorie-herkenning.
        named_match = NAMED_QUERY_PATTERN.search(text_lower)
        if named_match:
            keyword = named_match.group(1).strip(" ?.,-!")
            if keyword not in ("", "today", "the news"):
                return self._search_named_topic(keyword)

        topic = self._match_topic(text_lower) or self.default_topic
        return self._fetch_and_summarize_topic(topic)

    def _fetch_and_summarize_topic(self, topic: str) -> str:
        feed_url = FEEDS.get(topic, FEEDS["top"])
        try:
            items = self._fetch_items(feed_url, limit=10)
        except Exception as e:
            return f"I couldn't reach the news right now: {e}"

        if not items:
            return "I couldn't find any news right now."

        self.last_items = items
        self.last_topic = topic
        self.last_fetch_time = datetime.now()

        popup_text = "\n".join(f"- {i['title']}" for i in items)
        threading.Thread(target=lambda: show_notification(f"News: {topic}", popup_text), daemon=True).start()

        return self._summarize_importance(items)

    def _search_named_topic(self, keyword: str) -> str:
        matches = []
        searched_items = []

        for feed_name in SEARCH_FEEDS:
            try:
                items = self._fetch_items(FEEDS[feed_name], limit=15)
            except Exception:
                continue
            searched_items.extend(items)
            matches.extend(i for i in items
                            if keyword in i["title"].lower() or keyword in i["description"].lower())

        if searched_items:
            self.last_items = searched_items
            self.last_topic = "top"
            self.last_fetch_time = datetime.now()

        if not matches:
            return (f"I don't see any current news about {keyword}. "
                    "My source is BBC, so it might just not be covered there right now.")

        # Dubbele treffers (zelfde titel uit meerdere feeds) eruit filteren
        seen_titles = set()
        unique_matches = []
        for m in matches:
            if m["title"] not in seen_titles:
                seen_titles.add(m["title"])
                unique_matches.append(m)

        popup_text = "\n".join(f"- {m['title']}" for m in unique_matches[:8])
        threading.Thread(target=lambda: show_notification(f"News about {keyword}", popup_text), daemon=True).start()

        context_text = "\n".join(f"- {m['title']}: {m['description']}" for m in unique_matches[:5])
        prompt = (
            f"{GROUNDING_RULE}\n\n"
            f"Here is what the news source says about '{keyword}':\n{context_text}\n\n"
            f"Summarize this in 2-3 short spoken sentences, each about a different story."
        )
        return self._ask_llm(prompt, fallback=context_text)

    def _summarize_importance(self, items: list) -> str:
        headlines_text = "\n".join(f"- {i['title']}" for i in items)
        prompt = (
            f"{GROUNDING_RULE}\n\n"
            "Here are today's news headlines:\n"
            f"{headlines_text}\n\n"
            "Pick only the genuinely significant stories (major world events, politics, "
            "disasters, big economic or tech news) that a general person should know about "
            "today. Ignore minor, celebrity, or soft-news items. For each significant story, "
            "give exactly ONE short spoken sentence using only what the headline itself says - "
            "do not describe the same story twice. If none of the headlines are genuinely "
            "significant, reply with exactly: 'Nothing major in the news today.' Keep your "
            "entire reply under 80 words, plain text, no bullet points, no preamble."
        )
        return self._ask_llm(prompt, fallback="Here are today's top headlines: " + "; ".join(i["title"] for i in items[:3]))

    def _answer_followup(self, text_lower: str) -> str:
        keyword = text_lower
        for phrase in FOLLOWUP_PHRASES:
            keyword = keyword.replace(phrase, "")
        keyword = keyword.strip(" ?.,-")

        if not keyword:
            return "What would you like more info about?"

        return self._search_named_topic(keyword)

    def _ask_llm(self, prompt: str, fallback: str) -> str:
        try:
            response = requests.post(
                self.ollama_url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except requests.exceptions.RequestException:
            return fallback