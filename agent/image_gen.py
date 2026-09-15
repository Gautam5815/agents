import base64
import os

from openai import OpenAI

from . import config


def generate_image_b64(prompt: str) -> str:
    """Generate an image with OpenAI's image model and return it as a base64 string."""
    config.require("OPENAI_API_KEY")
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    result = client.images.generate(
        model=config.IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        n=1,
    )
    return result.data[0].b64_json


def generate_image(prompt: str, output_path: str) -> str:
    """Generate an image and save it to output_path (for local/CLI use). Returns output_path."""
    image_b64 = generate_image_b64(prompt)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_b64))
    return output_path
