import json
import os

from openai import OpenAI

from . import config

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "writer_prompt.md")


def _load_system_prompt() -> str:
    with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def generate_post_and_image_prompt(topic: str, research_text: str) -> dict:
    config.require("OPENAI_API_KEY")
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    system_prompt = _load_system_prompt()
    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Web research:\n{research_text}\n\n"
        "Write the LinkedIn post and image prompt as instructed."
    )

    response = client.chat.completions.create(
        model=config.TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return {
        "post": data["post"].strip(),
        "image_prompt": data["image_prompt"].strip(),
    }
