from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import AIAgent
from dotenv import load_dotenv
import os
from openai import OpenAI
import logging

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:8080"])

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agents = {}

@app.route('/validate', methods=['POST'])
def validate_api_key():
    data = request.json
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({'valid': False, 'error': 'No API key provided'}), 400
    
    try:
        # Try to create a client and make a simple API call to validate the key
        client = OpenAI(api_key=api_key)
        # Just list models to verify the key works
        models = client.models.list()
        return jsonify({'valid': True})
    except Exception as e:
        logger.error(f"API key validation error: {str(e)}")
        return jsonify({'valid': False, 'error': str(e)}), 401

@app.route('/chat', methods=['POST'])
def chat():
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({'error': 'No API key provided'}), 401
    
    # Get or create agent for this API key
    if api_key not in agents:
        agents[api_key] = AIAgent(api_key)
    
    data = request.json
    user_input = data.get('message', '')
    
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        response = agents[api_key].get_response(user_input)
        return jsonify({'response': response})
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 