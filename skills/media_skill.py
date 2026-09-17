import re
import yt_dlp
from skills.base_skill import BaseSkill
from skills.browser_utils import open_incognito
from skills.browser_utils import open_incognito, open_normal


class MediaSkill(BaseSkill):
    """
    Opent YouTube, of zoekt een video op en opent die rechtstreeks in de
    browser (incognito). Gebruikt yt-dlp puur om te zoeken, niet om de
    video te downloaden of te streamen - dat voorkomt YouTube's
    JS-runtime-vereisten voor het ophalen van afspeelbare formats.
    """

    def can_handle(self, text: str) -> bool:
        text = text.lower()
        if "youtube" in text and "open" in text:
            return True
        if re.search(r"\bplay (.+)", text):
            return True
        return False

    def handle(self, text: str) -> str:
        text_lower = text.lower()

        if "youtube" in text_lower and "open" in text_lower:
            open_normal("https://www.youtube.com")
            return "Opening YouTube."

        match = re.search(r"\bplay (.+)", text_lower)
        if match:
            query = match.group(1).strip().rstrip(".?!")
            return self._play_via_browser(query)

        return "I'm not sure what to play."

    def _play_via_browser(self, query: str) -> str:
        try:
            ydl_opts = {"quiet": True, "extract_flat": True, "noplaylist": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                entries = info.get("entries") or []
                if not entries:
                    return f"I couldn't find anything for {query}."
                video_id = entries[0]["id"]

            video_url = f"https://www.youtube.com/watch?v={video_id}"
            open_incognito(video_url)
            return f"Playing {query} on YouTube."
        except Exception as e:
            return f"I couldn't find that: {e}"