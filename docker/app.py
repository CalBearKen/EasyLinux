from flask import Flask, request, jsonify
from flask_cors import CORS
from agent import AIAgent
from openai import OpenAI
from config import Config

app = Flask(__name__)
CORS(app, origins=Config.CORS_ORIGINS)

agents = {}

@app.route('/validate', methods=['POST'])
def validate_api_key():
    data = request.json
    api_key = data.get('api_key', '')
    
    if not api_key:
        return jsonify({'valid': False})
    
    try:
        client = OpenAI(api_key=api_key)
        client.models.list()
        return jsonify({'valid': True})
    except Exception as e:
        return jsonify({'valid': False})

@app.route('/chat', methods=['POST'])
def chat():
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({'error': 'No API key provided'}), 401
    
    if api_key not in agents:
        agents[api_key] = AIAgent(api_key)
    
    data = request.json
    user_input = data.get('message', '')
    
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    response = agents[api_key].get_response(user_input)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT) 