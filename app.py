from flask import Flask, render_template, request, jsonify, make_response
import json, requests, uuid, re
import os

app = Flask(__name__)
app.secret_key = "secret-key"

# 🔑 PUT NEW KEY HERE
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyBPa_O29r77HFRWSW5osyHEaQZnhB3hjJc')
# ✅ CORRECT ENDPOINT + MODEL
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
SESSIONS = {}

QUESTIONS = [
    "Hey! When making big decisions, do you think deeply or go with your gut?",
    "How do you handle stress?",
    "What's a dream you don't usually share?",
    "What matters most in relationships?",
    "What's a habit you want to change?",
    "What does success mean to you?",
    "Where do you see yourself in 5 years?",
    "What advice would you give your younger self?"
]

ACK = [
    "Interesting.", "Nice.", "That says a lot.",
    "Makes sense.", "Good one.", "I like that.",
    "That's honest.", "Appreciate that."
]


# 🔥 STRONG JSON EXTRACTOR
def extract_json(text):
    if not text:
        return None

    print("\n=== RAW AI OUTPUT ===\n", text, "\n====================\n")

    text = re.sub(r'```json', '', text)
    text = re.sub(r'```', '', text).strip()

    # Try direct
    try:
        return json.loads(text)
    except:
        pass

    # Extract JSON block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception as e:
            print("PARSE ERROR:", e)

    return None


# 🔥 GENERATE PROFILE
def generate_profile(answers):
    convo = ""
    for i, (q, a) in enumerate(zip(QUESTIONS, answers)):
        convo += f"Q{i+1}: {q}\nA: {a}\n\n"

    prompt = f"""
Analyze this conversation and return ONLY JSON.

{convo}

STRICT RULES:
- ONLY JSON
- NO text before or after
- NO markdown

FORMAT:
{{
  "personality_type": "name",
  "summary": "2-3 sentences",
  "traits": [
    {{"trait": "Creativity", "level": 7, "description": "one line"}},
    {{"trait": "Empathy", "level": 8, "description": "one line"}},
    {{"trait": "Ambition", "level": 6, "description": "one line"}},
    {{"trait": "Discipline", "level": 5, "description": "one line"}},
    {{"trait": "Confidence", "level": 7, "description": "one line"}}
  ],
  "thinking_style": "text",
  "emotional_pattern": "text",
  "hidden_strength": "text",
  "blind_spot": "text",
  "improvements": [
    {{"area": "Productivity", "suggestion": "text"}},
    {{"area": "Relationships", "suggestion": "text"}},
    {{"area": "Mental Health", "suggestion": "text"}},
    {{"area": "Career", "suggestion": "text"}}
  ],
  "quote": "text"
}}
"""

    try:
        r = requests.post(
            GEMINI_URL,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1500
                }
            },
            timeout=30
        )

        print("STATUS:", r.status_code)

        if r.status_code != 200:
            print("ERROR RESPONSE:", r.text)
            return None

        data = r.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]

        return extract_json(text)

    except Exception as e:
        print("REQUEST ERROR:", e)
        return None


# ───────── ROUTES ─────────

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/start', methods=['POST'])
def start():
    sid = str(uuid.uuid4())
    SESSIONS[sid] = []

    res = make_response(jsonify({
        "message": QUESTIONS[0],
        "question_number": 1,
        "total": 8,
        "done": False
    }))
    res.set_cookie("sid", sid)
    return res


@app.route('/chat', methods=['POST'])
def chat():
    sid = request.cookies.get("sid")

    if not sid or sid not in SESSIONS:
        return jsonify({"message": "Session expired", "done": False})

    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify({"message": "Please type something", "done": False})

    answers = SESSIONS[sid]
    answers.append(msg)

    if len(answers) == 8:
        return jsonify({
            "message": "Done! Click below to see your profile ✨",
            "question_number": 8,
            "total": 8,
            "done": True
        })

    return jsonify({
        "message": f"{ACK[len(answers)-1]} {QUESTIONS[len(answers)]}",
        "question_number": len(answers)+1,
        "total": 8,
        "done": False
    })


@app.route('/profile')
def profile():
    sid = request.cookies.get("sid")

    if not sid or sid not in SESSIONS:
        return jsonify({"error": "Session expired"})

    answers = SESSIONS[sid]

    if len(answers) < 8:
        return jsonify({"error": "Answer all questions first"})

    result = generate_profile(answers)

    # ✅ FALLBACK (never break UI)
    if not result:
        return jsonify({
            "personality_type": "The Balanced Thinker",
            "summary": "You show a mix of reflection and intuition.",
            "traits": [
                {"trait": "Creativity", "level": 6, "description": "Moderate"},
                {"trait": "Empathy", "level": 6, "description": "Balanced"},
                {"trait": "Ambition", "level": 6, "description": "Steady"},
                {"trait": "Discipline", "level": 5, "description": "Growing"},
                {"trait": "Confidence", "level": 6, "description": "Improving"}
            ],
            "thinking_style": "Balanced thinking.",
            "emotional_pattern": "Stable emotions.",
            "hidden_strength": "Adaptability",
            "blind_spot": "Self-doubt",
            "improvements": [
                {"area": "Productivity", "suggestion": "Build routines"},
                {"area": "Relationships", "suggestion": "Communicate clearly"},
                {"area": "Mental Health", "suggestion": "Rest properly"},
                {"area": "Career", "suggestion": "Set goals"}
            ],
            "quote": "Keep moving forward."
        })

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)