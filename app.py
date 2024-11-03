from flask import Flask, render_template, request, jsonify
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

@app.route('/')
def home():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
@error_handler
def chat():
    data = request.json
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
        
    # Get response using RAG
    response = llm_client.rag_query(message)
    
    return jsonify({
        "response": response,
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True)