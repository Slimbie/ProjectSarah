import subprocess
import webbrowser

CHROME_CANDIDATES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]


def open_incognito(url: str, browser: str = "chrome"):
    """Opent een URL in een incognito/private venster."""
    if browser == "chrome":
        for candidate in CHROME_CANDIDATES:
            try:
                subprocess.Popen([candidate, "--incognito", url])
                return
            except FileNotFoundError:
                continue
        webbrowser.open(url)
    elif browser == "firefox":
        try:
            subprocess.Popen(["firefox", "--private-window", url])
        except FileNotFoundError:
            webbrowser.open(url)
    else:
        webbrowser.open(url)


def open_normal(url: str, browser: str = "chrome"):
    """Opent een URL gewoon, zonder incognito/private modus."""
    if browser == "chrome":
        for candidate in CHROME_CANDIDATES:
            try:
                subprocess.Popen([candidate, url])
                return
            except FileNotFoundError:
                continue
        webbrowser.open(url)
    else:
        webbrowser.open(url)