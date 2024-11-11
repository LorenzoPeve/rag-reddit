from flask import Flask, render_template, Response, request, jsonify
from functools import wraps
import logging
from datetime import datetime
from src import db, rag

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
llm_client = rag.ThrottledOpenAI()


def error_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return decorated_function


@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
@error_handler
def chat():
    data = request.json
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    return Response(llm_client.rag_query(message), mimetype="text/event-stream")


@app.route("/api/find_ids", methods=["POST"])
def find_post_urls() -> dict:
    """
    Endpoint to retrieve post URLs based on provided post IDs.

    Expected request body format:
    {
        "post_ids": ["id1", "id2", "id3", ...]
    }

    Returns:
    {
        "urls": {
            "id1": "url1",
            "id2": "url2",
            ...
        }
    }
    """
    try:
        data = request.get_json()

        if not data or "post_ids" not in data:
            return jsonify({"error": "Missing post_ids in request body"}), 400

        post_ids: list[str] = data["post_ids"]

        if not isinstance(post_ids, list):
            return jsonify({"error": "post_ids must be a list"}), 400

        urls = db.get_posts_url(post_ids)

        return jsonify({"urls": urls})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)