import re


def parse_genres(listed_in: str) -> list[str]:
    if not listed_in:
        return []
    return [g.strip() for g in listed_in.split(",") if g.strip()]


def parse_duration_to_minutes(duration: str) -> int | None:
    """
    Для Movie: "90 min" -> 90
    Для TV Show: "2 Seasons" -> None (минуты неизвестны)
    """
    if not duration:
        return None
    m = re.search(r"(\d+)\s*min", duration.lower())
    if m:
        return int(m.group(1))
    return None


def parse_seasons(duration: str) -> int | None:
    if not duration:
        return None
    m = re.search(r"(\d+)\s*season", duration.lower())
    if m:
        return int(m.group(1))
    return None


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())