from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__, static_folder='.', static_url_path='')

# === Gemini API KEY PLACEHOLDER ===
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"  # <-- Put your Gemini API key here

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    # Gemini API call
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + GEMINI_API_KEY
    payload = {
        "contents": [{"parts": [{"text": user_message}]}]
    }
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
        gemini_reply = r.json()['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"response": gemini_reply})
    except Exception as e:
        return jsonify({"response": "Sorry, I couldn't get an answer from the AI right now."})

if __name__ == '__main__':
    app.run(debug=True)