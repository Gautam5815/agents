import os
from datetime import date

_TOPICS_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "daily_topics.md")


def _load_topics() -> list[str]:
    with open(_TOPICS_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    topics = []
    in_comment = False
    for line in lines:
        line = line.strip()
        if line.startswith("<!--"):
            in_comment = True
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line:
            topics.append(line)
    return topics


def pick_daily_topic(for_date: date | None = None) -> str:
    """Deterministically picks a topic based on the day of the year, cycling through
    prompts/daily_topics.md. Stateless — no counter/database needed, and calling this
    twice on the same day always returns the same topic."""
    topics = _load_topics()
    if not topics:
        raise ValueError(f"{_TOPICS_PATH} has no topics defined.")

    d = for_date or date.today()
    index = d.toordinal() % len(topics)
    return topics[index]
