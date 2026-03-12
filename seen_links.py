"""
Persist and read seen job links to avoid applying twice.
"""
import os

from config import SEEN_FILE


def load_seen_links(path: str = SEEN_FILE) -> set[str]:
    """Load previously applied job links from file to avoid duplicates."""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def append_seen_link(link: str, path: str = SEEN_FILE) -> None:
    """Append a processed job link to the tracking file."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(link + "\n")
