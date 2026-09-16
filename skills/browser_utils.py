import subprocess
import webbrowser

CHROME_CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]


def open_incognito(url: str, browser: str = "chrome"):
    """
    Opent een URL in een incognito/private venster. Probeert een paar
    mogelijke commandonamen voor Chrome/Chromium, valt terug op de
    standaardbrowser als niks daarvan gevonden wordt.
    """
    if browser == "chrome":
        for candidate in CHROME_CANDIDATES:
            try:
                subprocess.Popen([candidate, "--incognito", url])
                return
            except FileNotFoundError:
                continue
        webbrowser.open(url)  # geen enkele Chrome-variant gevonden
    elif browser == "firefox":
        try:
            subprocess.Popen(["firefox", "--private-window", url])
        except FileNotFoundError:
            webbrowser.open(url)
    else:
        webbrowser.open(url)