import argparse
import json
import sys
from datetime import datetime

from agent import config, content, image_gen, linkedin_client, research


def run(topic: str, skip_confirm: bool = False) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log: dict = {"topic": topic, "timestamp": timestamp, "dry_run": config.DRY_RUN}

    print(f"\n=== LinkedIn Post Agent ===\nTopic: {topic}\n")
    if config.DRY_RUN:
        print("(DRY_RUN is on: the pipeline will run fully but will NOT publish to LinkedIn)\n")

    print("Step 1/4: Researching topic...")
    results = research.search_topic(topic)
    research_text = research.format_research_for_prompt(results)
    log["research"] = results
    print(f"  Found {len(results)} research snippet(s).")

    print("Step 2/4: Writing post + image prompt with GPT...")
    generated = content.generate_post_and_image_prompt(topic, research_text)
    post_text = generated["post"]
    image_prompt = generated["image_prompt"]
    log["post"] = post_text
    log["image_prompt"] = image_prompt

    print("Step 3/4: Generating image with OpenAI...")
    image_path = f"output/post_{timestamp}.png"
    image_gen.generate_image(image_prompt, image_path)
    log["image_path"] = image_path
    print(f"  Image saved to {image_path}")

    print("\n----- POST PREVIEW -----")
    print(post_text)
    print("-------------------------")
    print(f"Image prompt used: {image_prompt}")
    print(f"Image file: {image_path}\n")

    if config.DRY_RUN:
        log["published"] = False
        _write_log(timestamp, log)
        print("DRY_RUN is on — skipping LinkedIn publish. Nothing was posted.")
        return

    if not skip_confirm:
        answer = input("Post this to LinkedIn now? [y/N]: ").strip().lower()
        if answer != "y":
            log["published"] = False
            _write_log(timestamp, log)
            print("Aborted. Nothing was posted.")
            return

    print("Step 4/4: Posting to LinkedIn...")
    result = linkedin_client.post_with_image(post_text, image_path)
    log["published"] = True
    log["linkedin_result"] = result
    _write_log(timestamp, log)
    print(f"Posted successfully. {result}")


def _write_log(timestamp: str, log: dict) -> None:
    log_path = f"output/run_{timestamp}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    print(f"Run log written to {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI agent that researches a topic, "
                                      "writes a LinkedIn post with an AI-generated image, "
                                      "and publishes it to LinkedIn.")
    parser.add_argument("topic", nargs="?", help="Topic for the LinkedIn post")
    parser.add_argument("--yes", "-y", action="store_true",
                         help="Skip the confirmation prompt and post immediately")
    args = parser.parse_args()

    topic = args.topic or input("Enter the topic for your LinkedIn post: ").strip()
    if not topic:
        print("A topic is required.")
        sys.exit(1)

    required = ["OPENAI_API_KEY", "SERPAPI_API_KEY"]
    if not config.DRY_RUN:
        required.append("LINKEDIN_ACCESS_TOKEN")
    try:
        config.require(*required)
        run(topic, skip_confirm=args.yes)
    except config.MissingConfigError as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
