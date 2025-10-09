from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import google.generativeai as genai
import difflib
import re
import json
import os

app = Flask(__name__)

CORS(app)

genai.configure(api_key=os.getenv('AIzaSyBWww4kst4F3WZFx9sRm37YAKfuMvfAbC8'))

FAQ_DATA = {
    "about": {
        "keywords": ["about", "college", "mmec", "history", "established", "location", "address", "contact", "website"],
        "response": """Maratha Mandal Engineering College (MMEC) is located at R.S. No. 104, Halbhavi Village, New Vantmuri Post, Via-Kakati, Belagavi – 591113, Karnataka, India. Established in 1997, it is approved by AICTE and affiliated to Visvesvaraya Technological University (VTU), Belagavi. Managed by Maratha Mandal, Belagavi (founded in 1931), MMEC emphasizes academic excellence, discipline, strong placement support, and ethical values. Website: <a href="https://www.mmec.edu.in">www.mmec.edu.in</a>. Contact: 📞 9353364643 | ✉ <a href="mailto:info@mmec.edu.in">info@mmec.edu.in</a>."""
    },
    "courses": {
        "keywords": ["courses", "branches", "streams", "programs", "engineering", "cse", "ai", "mechanical", "ece"],
        "response": """MMEC offers the following undergraduate streams:\n🖥 Computer Science & Engineering (CSE)\n🤖 Robotics & Artificial Intelligence (R&AI)\n⚙ Mechanical Engineering\n📡 Electronics & Communication Engineering (ECE). All programs are affiliated with VTU and focus on practical skills and innovation."""
    },
    "admissions": {
        "keywords": ["admissions", "admission", "apply", "entrance", "eligibility"],
        "response": """Admissions to MMEC are based on KCET/COMEDK/JEE Main scores for B.E. programs. Eligibility: 10+2 with Physics, Chemistry, and Mathematics (minimum 45% aggregate). Apply via the official website <a href="https://www.mmec.edu.in">www.mmec.edu.in</a> or contact admissions office at 9353364643. Key dates and forms are updated annually—check the site for the latest."""
    },
    "fees": {
        "keywords": ["fees", "fee", "payment", "tuition", "cost", "structure"],
        "response": """The fee structure for B.E. programs at MMEC is approximately ₹1,00,000 - ₹1,50,000 per year (government quota) and higher for management quota (subject to change). This includes tuition and other charges. Scholarships are available for meritorious/SC/ST students. For exact details, visit <a href="https://www.mmec.edu.in">www.mmec.edu.in</a> or email info@mmec.edu.in."""
    },
    "placements": {
        "keywords": ["placements", "placement", "jobs", "career", "support"],
        "response": """MMEC has strong placement support with 80-90% placement rate. Top recruiters include Infosys, TCS, Accenture, and Bosch. The placement cell offers training, workshops, and internships. Average package: ₹4-6 LPA. Contact the placement officer via the website <a href="https://www.mmec.edu.in">www.mmec.edu.in</a>."""
    },
    "greetings": {
        "keywords": ["hi", "hello", "hey", "thank you", "bye", "goodbye"],
        "response": "Hello! How can I help you with MMEC today? Ask about courses, admissions, or anything college-related. 😊"
    }
}

def find_best_match(user_message, options):
    user_words = re.findall(r'\w+', user_message.lower())
    best_score = 0
    best_key = None
    for key, data in FAQ_DATA.items():
        for keyword in data["keywords"]:
            for word in user_words:
                score = difflib.SequenceMatcher(None, word, keyword).ratio()
                if score > best_score and score > 0.6:
                    best_score = score
                    best_key = key
    return best_key

def get_gemini_response(prompt):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(f"You are an AI assistant for Maratha Mandal Engineering College (MMEC), Belagavi. Respond helpfully and professionally to this query, focusing only on college-related topics: {prompt}. If irrelevant, politely guide back to college info like courses, admissions, or contact.")
        return response.text
    except Exception as e:
        return "Sorry, I'm having trouble connecting to the AI service right now. Please ask about MMEC FAQs like courses or admissions! 😔"

@app.route('/')
def index():
    with open('index.html', 'r') as f:
        html_content = f.read()
    return html_content

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip().lower()

    if not user_message:
        return jsonify({'response': 'Please enter a message!'})

    if any(greet in user_message for greet in ["hi", "hello", "hey", "thank", "bye"]):
        return jsonify({'response': FAQ_DATA['greetings']['response']})

    matched_key = find_best_match(user_message, FAQ_DATA)
    if matched_key and matched_key != 'greetings':
        response = FAQ_DATA[matched_key]['response']
    else:
        response = get_gemini_response(user_message)
        if "irrelevant" in response.lower() or len(response) < 20:
            response = "That doesn't seem related to MMEC. I can help with college info like courses, admissions, fees, or contact details. What would you like to know? 📚"

    return jsonify({'response': response})

if __name__ == '_main_':
    app.run(debug=True, host='0.0.0.0', port=5000)