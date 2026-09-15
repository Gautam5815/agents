import base64

from flask import Flask, jsonify, render_template, request

from agent import config, content, image_gen, linkedin_client, research

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", dry_run=config.DRY_RUN)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    topic = (request.json or {}).get("topic", "").strip()
    if not topic:
        return jsonify({"error": "Topic is required."}), 400

    try:
        results = research.search_topic(topic)
        research_text = research.format_research_for_prompt(results)

        generated = content.generate_post_and_image_prompt(topic, research_text)
        post_text = generated["post"]
        image_prompt = generated["image_prompt"]

        image_b64 = image_gen.generate_image_b64(image_prompt)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "post": post_text,
        "image_prompt": image_prompt,
        "image_b64": image_b64,
        "research_count": len(results),
    })


@app.route("/api/publish", methods=["POST"])
def api_publish():
    if config.DRY_RUN:
        return jsonify({"error": "DRY_RUN is enabled — publishing is disabled."}), 400

    body = request.json or {}
    post_text = (body.get("post") or "").strip()
    image_b64 = body.get("image_b64")

    if not post_text or not image_b64:
        return jsonify({"error": "Both 'post' and 'image_b64' are required."}), 400

    try:
        image_bytes = base64.b64decode(image_b64)
        result = linkedin_client.post_with_image_bytes(post_text, image_bytes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
