from flask import Flask, send_from_directory, request, jsonify, send_file
import json
import os
from datetime import datetime
import uuid
import sqlite3

# Load .env if present to make development easier without committing secrets
try:
    # use dynamic import to avoid static import errors when python-dotenv isn't installed
    import importlib
    dotenv = importlib.import_module('dotenv')
    load_dotenv = getattr(dotenv, 'load_dotenv', None)
    if callable(load_dotenv):
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
except Exception:
    # dotenv is optional; environment variables may be set by the process or OS
    pass

app = Flask(__name__, static_folder='.', static_url_path='')

CHAT_LOG_FILE = 'chat_logs.json'
USERS_FILE = 'users.json'
SETTINGS_FILE = os.path.join('data','settings.json')

# Simple in-memory session store: token -> username
SESSIONS = {}

def _ensure_settings():
    base = os.path.dirname(SETTINGS_FILE)
    if base and not os.path.exists(base):
        os.makedirs(base, exist_ok=True)
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE,'w',encoding='utf-8') as f:
            json.dump({'allow_external_queries': True}, f)

def read_settings():
    _ensure_settings()
    try:
        with open(SETTINGS_FILE,'r',encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'allow_external_queries': True}

def write_settings(d):
    _ensure_settings()
    with open(SETTINGS_FILE,'w',encoding='utf-8') as f:
        json.dump(d, f, indent=2)

def is_external_allowed():
    # env var overrides file setting
    env = os.getenv('ALLOW_EXTERNAL_QUERIES')
    if env is not None:
        return str(env).lower() in ('1','true','yes')
    s = read_settings()
    return bool(s.get('allow_external_queries', True))

# Load or initialize chat logs
def load_logs():
    if not os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'w') as f:
            json.dump([], f, indent=2)
    with open(CHAT_LOG_FILE, 'r') as f:
        return json.load(f)

def save_logs(logs):
    with open(CHAT_LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=2)

# Load users (simple JSON with plain text passwords for prototype)
def load_users():
    if not os.path.exists(USERS_FILE):
        # default credentials - change in production
        default = {
            "Student": "student123",
            "Faculty": "faculty123",
            "Admin": "admin123"
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(default, f, indent=2)
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

# Serve index.html
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# API: Query - receives {message, role}
@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.get_json() or {}
    message = data.get('message', '')
    role = data.get('role', 'Guest')
    # Normalize message and treat MMEC specially
    msg_norm = (message or '').strip()
    msg_lower = msg_norm.lower()
    # treat MMEC as full college name for context
    if 'mmec' in msg_lower:
        msg_lower = msg_lower.replace('mmec', 'maratha mandal engineering college')

    # Simple server-side offline FAQ (mirrors frontend). Developers: update here as needed.
    offline_faq = [
        {"triggers": ["about","about the college","college","mmec","history","established","location","address","contact","website"],
         "answer": "Maratha Mandal Engineering College (MMEC) is located at R.S. No. 104, Halbhavi Village, New Vantmuri Post, Via-Kakati, Belagavi – 591113, Karnataka, India. Established in 1997, it is approved by AICTE and affiliated to VTU, Belagavi. Managed by Maratha Mandal (founded 1931). Website: https://www.mmec.edu.in. Contact: +91 9353364643, info@mmec.edu.in."},
        {"triggers": ["branches","courses","streams","departments","what branches","courses offered","programs"],
         "answer": "MMEC offers these major streams: Computer Science & Engineering (CSE); Robotics & Artificial Intelligence (R&AI); Mechanical Engineering; Electronics & Communication Engineering (ECE). All programs are affiliated to VTU and focus on practical skills and innovation."},
        {"triggers": ["fees","fee","tuition","payment","payment details","fee structure"],
         "answer": "Management Quota:\n- Computer Science and Engineering: ₹2,00,000/- per year\n- Electronics & Communication Engineering: ₹1,75,000/- per year\n- Robotics & Artificial Intelligence: ₹1,70,000/- per year\n- Mechanical Engineering: ₹35,000/- for 1st year, ₹55,000/- per year from 2nd year onwards\n\nMerit Students: ₹1,00,000/- per year\n\nOther Fees:\n- Admission form Fees: ₹1,200/-\n- Alumni Association Fees: ₹500/- (One time)\n- Dept. Association Fees: ₹500/- (Every year)\n- Transportation Fees: ₹12,000/- (Every year, ₹6,000 paid by Management, ₹6,000 by Student)\n\nHostel Fees:\n- Accommodation: ₹40,000/- per year\n- Deposit: ₹10,000/- (Non Refundable)\n- Food: ₹3,500/- to ₹3,800/- per month (subject to market rates)\n\nNotes: Admissions on merit via MMEC entrance test or KEA. No donations. Payments via online banking, UPI, cash, or DD. Bank cheques not accepted. Contact +91 9353364643 for details."},
        {"triggers": ["admissions","how to apply","admission process","apply","eligibility"],
         "answer": "Admissions to MMEC are based on relevant state and national entrance processes (KCET/COMEDK/JEE etc.) and VTU guidelines. Check https://www.mmec.edu.in/admissions or contact admissions at +91 9353364643 for current procedures and dates."},
        {"triggers": ["placements","placement","jobs","placement support","career"],
         "answer": "MMEC provides placement support through a dedicated placement cell that organizes training, internships and campus recruitment. Top recruiters include Infosys, TCS, Accenture and Bosch. Visit https://www.mmec.edu.in/placements for more details."},
        {"triggers": ["contact","contact info","phone","email","website"],
         "answer": "Contact: +91 9353364643 | info@mmec.edu.in. Website: https://www.mmec.edu.in"},
        {"triggers": ["hod cse", "head of department cse", "faculty head cse", "hod computer science", "head computer science"],
         "answer": "The Head of Department for Computer Science and Engineering (CSE) at MMEC is Swati Patil."},
        {"triggers": ["hod ece", "head of department ece", "faculty head ece", "hod electronics", "head electronics"],
         "answer": "The Head of Department for Electronics and Communication Engineering (ECE) at MMEC is Prof. Vaibhav Kakade."},
        {"triggers": ["hod mechanical", "head of department mechanical", "faculty head mechanical", "hod mech", "head mech"],
         "answer": "The Head of Department for Mechanical Engineering at MMEC is Anand Mattikal."},
        {"triggers": ["director","principal","vice principal","leadership"],
         "answer": "Director: Dr. Deepak G. Kulkarni (PhD Management Sciences, M.E. Mech). Principal: Dr. Praveen Chitti (PhD Image Processing, M.Tech VLSI, B.E. ECE). Vice-Principal: Dr. Suresh Mashyal (Hybrid Wind-Diesel Energy Systems)."},
        {"triggers": ["at a glance","mmec at a glance","overview"],
         "answer": "MMEC, established 1997, provides technical education in North Karnataka. Affiliated to VTU, approved by AICTE. Focus on science, technology, innovation. Managed by Maratha Mandal (1931). Mission: Advance knowledge for nation/world challenges."},
        {"triggers": ["department","departments"],
         "answer": "Departments: CSE, ECE, Mechanical, Robotics & AI."},
        {"triggers": ["placement cell","placement"],
         "answer": "Dedicated placement cell for training, internships, campus recruitment. Top recruiters: Infosys, TCS, Accenture, Bosch. Visit https://www.mmec.edu.in/placements."},
        {"triggers": ["nirf","ranking"],
         "answer": "NIRF ranking: Check https://www.mmec.edu.in for latest."},
        {"triggers": ["library"],
         "answer": "Library facilities available; contact college for details."},
        {"triggers": ["gallery"],
         "answer": "Photo gallery on website: https://www.mmec.edu.in/gallery."},
        {"triggers": ["e news letter","newsletter"],
         "answer": "E-newsletter available; subscribe via website."},
        {"triggers": ["facilities","facilities & others"],
         "answer": "Various facilities including labs, sports, etc.; visit https://www.mmec.edu.in/facilities."},
        {"triggers": ["multilingual books","books"],
         "answer": "Multilingual books available in library."},
        {"triggers": ["alumni cell","alumni"],
         "answer": "Alumni cell for networking and events."},
        {"triggers": ["nsdc"],
         "answer": "NSDC training programs available."},
        {"triggers": ["contact us"],
         "answer": "Contact: +91 9353364643 | info@mmec.edu.in. Website: https://www.mmec.edu.in"},
        {"triggers": ["faculty","staff","teachers","professors"],
         "answer": "Faculty information is not updated yet. Please check back later."}
    ]
    # Simplified offline matching: check if any trigger appears in normalized message
    for entry in offline_faq:
        for tr in entry['triggers']:
            if tr in msg_lower or msg_lower in tr:
                # return short authoritative offline answer
                return jsonify({"answer": entry['answer'], "source": "offline"})

    # Next: search data/college_info files for a direct answer (exact keywords or small fuzzy search)
    def search_college_files(query_lower):
        base = os.path.join('data', 'college_info')
        if not os.path.exists(base):
            return None
        # check info.md for phrase matches
        info_path = os.path.join(base, 'info.md')
        try:
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    txt = f.read().lower()
                if query_lower in txt:
                    # return a short extract: first 400 chars around first occurrence
                    idx = txt.find(query_lower)
                    start = max(0, idx - 120)
                    snippet = txt[start:start+400].strip()
                    return snippet
        except Exception:
            pass
        # check json files for keys or values
        for fn in os.listdir(base):
            if fn.endswith('.json'):
                try:
                    with open(os.path.join(base, fn), 'r', encoding='utf-8') as f:
                        j = json.load(f)
                    sj = json.dumps(j).lower()
                    if query_lower in sj:
                        # return tiny summary
                        return f"Found relevant data in {fn}. Use the college info panel for details."
                except Exception:
                    continue
        return None

    college_answer = search_college_files(msg_lower)
    if college_answer:
        return jsonify({"answer": college_answer, "source": "college_data"})

    # If we reach here the query is outside our local knowledge. Use AI fallback but keep it college-focused.
    # The policy: the bot is college-only. If the user asks about unrelated topics, respond with a short refusal.
    # Lightweight heuristic: if the query contains words like 'weather','movie','news' treat as outside scope.
    outside_keywords = ['weather', 'movie', 'news', 'stock', 'football', 'cricket', 'recipe']
    if any(k in msg_lower for k in outside_keywords):
        return jsonify({"answer": "This chatbot provides information about Maratha Mandal Engineering College (MMEC) only. For other queries please use a general search.", "source": "policy"})

    # Otherwise call AI fallback (OpenAI preferred)
    ai_answer = call_gemini(message, role)
    # Prefix with disclaimer when AI is used (not official college data)
    prefix = "Note: This answer is not from official MMEC data — "
    # If the ai_answer already contains our '[AI not configured]' style message, return short fallback instead
    if isinstance(ai_answer, str) and ai_answer.startswith('[AI not configured]'):
        # keep it short and actionable
        return jsonify({"answer": "Sorry, AI service is not configured on the server. The chatbot answers college FAQs from local data.", "source": "error"})
    if isinstance(ai_answer, str) and ai_answer.startswith('[AI error]'):
        return jsonify({"answer": "Error contacting AI provider. Try again later or ask a college-specific question.", "source": "error"})
    # Ensure short answer: limit to 400 chars
    if isinstance(ai_answer, str):
        short = ai_answer.strip()
        if len(short) > 400:
            short = short[:390].rsplit('.',1)[0] + '.'
        return jsonify({"answer": prefix + short, "source": "ai"})
    return jsonify({"answer": "Sorry, couldn't generate an answer.", "source": "error"})

@app.route('/api/logs', methods=['GET','POST','DELETE'])
def api_logs():
    # GET: return logs
    if request.method == 'GET':
        logs = load_logs()
        return jsonify({"logs": logs})
    # POST: append a log entry
    if request.method == 'POST':
        data = request.get_json() or {}
        entry = {
            "ts": datetime.utcnow().isoformat() + 'Z',
            "user": data.get('user', 'Guest'),
            "user_msg": data.get('user_msg', ''),
            "bot_msg": data.get('bot_msg', ''),
            "offline": bool(data.get('offline', False))
        }
        logs = load_logs()
        logs.append(entry)
        save_logs(logs)
        return jsonify({"ok": True})
    # DELETE: clear logs
    if request.method == 'DELETE':
        save_logs([])
        return jsonify({"ok": True})


@app.route('/api/login', methods=['POST'])
def api_login():
    """Simple login endpoint that validates against users.json.
    Expects JSON: { username: "Student"|"Faculty"|"Admin", password: "..." }
    Returns: { ok: True, role: username } on success or { ok: False, error: 'msg' } on failure
    """
    try:
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({"ok": False, "error": "missing credentials"}), 400
        users = load_users()
        expected = users.get(username)
        if expected and expected == password:
            # create a short session token for admin (simple prototype)
            token = str(uuid.uuid4())
            SESSIONS[token] = username
            return jsonify({"ok": True, "role": username, "token": token})
        return jsonify({"ok": False, "error": "invalid credentials"}), 401
    except Exception as e:
        print('Login error', e)
        return jsonify({"ok": False, "error": "server error"}), 500


@app.route('/upload', methods=['POST'])
def upload_files():
    """Accept multipart form uploads for logo and student images.
    Expected form fields: file-logo, file-student-1, file-student-2
    Saves files to ./static/ with fixed filenames and returns their public paths.
    """
    upload_dir = os.path.join(os.getcwd(), 'static')
    os.makedirs(upload_dir, exist_ok=True)

    saved = {}
    mapping = [
        ('file-logo', 'logo.jpg'),
        ('file-student-1', 'student_1.jpg'),
        ('file-student-2', 'student_2.jpg'),
    ]
    for field, out_name in mapping:
        f = request.files.get(field)
        if f and getattr(f, 'filename', ''):
            # Save to static folder with consistent filename
            dest = os.path.join(upload_dir, out_name)
            try:
                f.save(dest)
                # return a cache-busting URL so clients update immediately
                saved[field] = f"/static/{out_name}?v={int(datetime.utcnow().timestamp())}"
            except Exception as e:
                print('Failed saving upload', field, e)
    if saved:
        return jsonify({"ok": True, "files": saved})
    return jsonify({"ok": False, "error": "no files uploaded"}), 400

def call_gemini(message, role):
    """
    TODO: Integrate the Gemini API here.
    The intended model is: gemini-2.0-flash (generateContent).
    This function must:
      - Construct the prompt/context (include role or basic system prompt)
      - Send the request to Gemini
      - Return the text response.

    Example notes (developer):
    - Place your Gemini or Google Generative API key in environment variable GEMINI_API_KEY.
    - Using Google Generative API may require client library or service account.
    """
    # Prefer GEMINI_API_KEY, but allow an OpenAI fallback using OPENAI_API_KEY.
    gemini_key = os.getenv('GEMINI_API_KEY', '')
    openai_key = os.getenv('OPENAI_API_KEY', '')

    # Try Gemini (Google Generative) first if key present and library available
    if gemini_key:
        try:
            import importlib
            genai = importlib.import_module('google.generativeai')
            try:
                # some versions/clients expect configure(); others accept api_key
                if hasattr(genai, 'configure'):
                    genai.configure(api_key=gemini_key)
                else:
                    setattr(genai, 'api_key', gemini_key)
            except Exception:
                pass
            # Attempt using GenerativeModel if available
            if hasattr(genai, 'GenerativeModel'):
                try:
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    prompt = (f"You are an assistant for Maratha Mandal Engineering College (MMEC). "
                              f"Answer college-related queries concisely and helpfully. If the user asks unrelated topics, say you only provide MMEC information.\nUser: {message}")
                    resp = model.generate_content(prompt)
                    ans = getattr(resp, 'text', None) or getattr(resp, 'content', None) or str(resp)
                    if isinstance(ans, str):
                        ans = ans.strip()
                        if len(ans) > 800:
                            ans = ans[:790].rsplit('.',1)[0] + '.'
                    return ans
                except Exception as e:
                    print('Gemini model.generate_content error:', e)
            # Fallback: some genai wrappers provide a generate_text helper
            try:
                if hasattr(genai, 'generate_text'):
                    out = genai.generate_text(model='models/text-bison-001', input=f"MMEC assistant: {message}")
                    ans = getattr(out, 'text', None) or str(out)
                    return ans
            except Exception as e:
                print('Gemini generate_text error:', e)
        except Exception as e:
            print('Gemini import/config error:', e)

    # Next: OpenAI fallback (if configured and allowed)
    allow_external = is_external_allowed()
    if openai_key and allow_external:
        try:
            import openai
            openai.api_key = openai_key
            system = "You are an assistant for Maratha Mandal Engineering College (MMEC). Answer college-related queries concisely and helpfully. If the user asks unrelated topics, say you only provide MMEC information."
            resp = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=[{'role':'system','content':system},{'role':'user','content':message}],
                max_tokens=300,
                temperature=0.2
            )
            ans = resp.choices[0].message.content.strip()
            if len(ans) > 600:
                ans = ans[:590].rsplit('.',1)[0] + '.'
            return ans
        except Exception as e:
            print('OpenAI call error:', e)
            return "[AI error] Failed to call OpenAI. Check server logs."

    # If nothing worked
    return ("[AI not configured] No usable AI provider configured or external queries are disallowed. "
            "Set OPENAI_API_KEY and ALLOW_EXTERNAL_QUERIES=1 or ensure GEMINI_API_KEY and google.generativeai are installed.")


# Serve college information from data files
@app.route('/api/college_info', methods=['GET'])
def api_college_info():
    info_path = os.path.join('data', 'college_info', 'info.md')
    if os.path.exists(info_path):
        with open(info_path, 'r', encoding='utf-8') as f:
            txt = f.read()
        return jsonify({"ok": True, "text": txt})
    return jsonify({"ok": False, "error": "info not found"}), 404


@app.route('/api/status', methods=['GET'])
def api_status():
    """Return a small status object indicating if AI fallback is configured and allowed.
    Does NOT return any secret keys.
    """
    gemini_key = bool(os.getenv('GEMINI_API_KEY'))
    openai_key = bool(os.getenv('OPENAI_API_KEY'))
    # Check whether gemini client library is installed (so gemini is actually usable)
    gemini_ready = False
    if gemini_key:
        try:
            import importlib
            importlib.import_module('google.generativeai')
            gemini_ready = True
        except Exception:
            gemini_ready = False
    usable = (openai_key and is_external_allowed()) or gemini_ready
    return jsonify({
        "ok": True,
        "ai_provider_available": usable,
        "openai_present": openai_key,
        "gemini_key_present": gemini_key,
        "gemini_ready": gemini_ready,
        "external_allowed": is_external_allowed()
    })


@app.route('/api/class_strengths', methods=['GET'])
def api_class_strengths():
    p = os.path.join('data', 'college_info', 'class_strengths.json')
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return jsonify({"ok": True, "data": json.load(f)})
    return jsonify({"ok": False, "error": "not found"}), 404


# Persist user histories under data/histories/<username>.json
HIST_DIR = os.path.join('data', 'histories')
os.makedirs(HIST_DIR, exist_ok=True)

# Optional SQLite DB (created by migration script)
DB_PATH = os.path.join('data', 'mmec.db')

def db_available():
    return os.path.exists(DB_PATH)

def db_get_history(username, page, size):
    # returns list of items latest-first for compatibility
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    offset = (page-1)*size
    cur.execute('SELECT sender, text, ts FROM histories WHERE username=? ORDER BY id DESC LIMIT ? OFFSET ?', (username, size, offset))
    rows = cur.fetchall()
    conn.close()
    out = []
    for sender, text, ts in rows:
        out.append({'from': sender or 'user', 'text': text or '', 'ts': ts})
    return out

def db_append_history(username, item):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO histories (username, role, sender, text, ts) VALUES (?,?,?,?,?)', (
        username, username, item.get('from','user'), item.get('text',''), item.get('ts', datetime.utcnow().isoformat() + 'Z')
    ))
    conn.commit()
    conn.close()

def db_clear_history(username):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM histories WHERE username=?', (username,))
    conn.commit()
    conn.close()


def history_path(username):
    safe = username.replace('/', '_')
    return os.path.join(HIST_DIR, f'{safe}.json')


@app.route('/api/history', methods=['GET','POST','DELETE'])
def api_history():
    # GET: ?user=Student&page=1&size=20
    if request.method == 'GET':
        user = request.args.get('user', 'guest')
        page = int(request.args.get('page', '1'))
        size = int(request.args.get('size', '20'))
        # If SQLite DB available, use it for histories
        if db_available():
            items = db_get_history(user, page, size)
            # estimate total is unknown here; client uses emptiness to stop
            return jsonify({"ok": True, "history": items, "page": page, "size": size})
        # else fallback to JSON file storage
        p = history_path(user)
        if not os.path.exists(p):
            return jsonify({"ok": True, "history": [], "page": page, "size": size})
        with open(p, 'r', encoding='utf-8') as f:
            hist = json.load(f)
        # return paginated (latest first)
        hist.reverse()
        start = (page-1)*size
        end = start + size
        page_items = hist[start:end]
        return jsonify({"ok": True, "history": page_items, "page": page, "size": size, "total": len(hist)})

    # POST: append history item {user, from, text, ts}
    if request.method == 'POST':
        data = request.get_json() or {}
        user = data.get('user', 'guest')
        item = { 'from': data.get('from','user'), 'text': data.get('text',''), 'ts': data.get('ts') or datetime.utcnow().isoformat() + 'Z' }
        # Use DB if available
        if db_available():
            try:
                db_append_history(user, item)
                return jsonify({"ok": True})
            except Exception as e:
                print('DB append history error', e)
                return jsonify({"ok": False, "error": "db error"}), 500
        # Fallback to JSON file
        p = history_path(user)
        lst = []
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                try:
                    lst = json.load(f)
                except Exception:
                    lst = []
        lst.append(item)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(lst, f, indent=2)
        return jsonify({"ok": True})

    # DELETE: clear user history (expects JSON { user: 'Student' })
    if request.method == 'DELETE':
        data = request.get_json() or {}
        user = data.get('user', 'guest')
        if db_available():
            try:
                db_clear_history(user)
                return jsonify({"ok": True})
            except Exception as e:
                print('DB clear history error', e)
                return jsonify({"ok": False, "error": "db error"}), 500
        p = history_path(user)
        if os.path.exists(p):
            os.remove(p)
        return jsonify({"ok": True})


@app.route('/api/reports/class_strengths', methods=['GET'])
def api_class_strengths_report():
    # Try to generate a simple PDF report if reportlab available; otherwise return JSON
    p = os.path.join('data', 'college_info', 'class_strengths.json')
    if not os.path.exists(p):
        return jsonify({"ok": False, "error": "not found"}), 404
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    try:
        import importlib
        # Dynamically import reportlab modules to avoid static import errors when package is not installed
        rl_pages = importlib.import_module('reportlab.lib.pagesizes')
        rl_canvas_mod = importlib.import_module('reportlab.pdfgen.canvas')
        from io import BytesIO
        letter = rl_pages.letter
        Canvas = rl_canvas_mod.Canvas
        buf = BytesIO()
        c = Canvas(buf, pagesize=letter)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(72, 720, 'Class Strengths Report - MMEC')
        y = 700
        c.setFont('Helvetica', 11)
        for dept, vals in data.items():
            if dept == 'faculty_head' or dept == 'faculty_count_other_depts':
                continue
            c.drawString(72, y, f'{dept}:')
            y -= 16
            for k, v in vals.items():
                c.drawString(92, y, f'{k}: {v}')
                y -= 14
            y -= 8
        c.showPage()
        c.save()
        buf.seek(0)
        return send_file(buf, mimetype='application/pdf', download_name='class_strengths.pdf')
    except Exception as e:
        # reportlab not installed or failed, return JSON instead
        return jsonify({"ok": True, "data": data})


@app.route('/api/admin/upload', methods=['POST','GET'])
def api_admin_upload():
    """Authenticated admin upload and list endpoint.
    GET: list files in data/college_info
    POST: multipart form upload with field 'file' and optional 'target' filename
    Requires header: X-Session-Token: <token>
    """
    token = request.headers.get('X-Session-Token') or request.args.get('token')
    user = SESSIONS.get(token)
    if not user or user != 'Admin':
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    base = os.path.join('data', 'college_info')
    os.makedirs(base, exist_ok=True)
    if request.method == 'GET':
        files = []
        for fn in sorted(os.listdir(base)):
            files.append(fn)
        return jsonify({"ok": True, "files": files})

    # POST -> upload
    f = request.files.get('file')
    target = request.form.get('target') or (f.filename if f else None)
    if not f or not target:
        return jsonify({"ok": False, "error": "no file"}), 400
    safe = os.path.basename(target)
    dest = os.path.join(base, safe)
    try:
        f.save(dest)
        return jsonify({"ok": True, "file": safe})
    except Exception as e:
        print('admin upload error', e)
        return jsonify({"ok": False, "error": "failed"}), 500


@app.route('/api/admin/toggle_ai', methods=['POST'])
def api_admin_toggle_ai():
    """Toggle the allow_external_queries setting persisted in data/settings.json.
    Requires header: X-Session-Token: <token> or ?token= in querystring. Only Admin may call.
    Returns: { ok: True, allow_external_queries: bool }
    """
    token = request.headers.get('X-Session-Token') or request.args.get('token')
    user = SESSIONS.get(token)
    if not user or user != 'Admin':
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    # Read, flip, write
    s = read_settings()
    cur = bool(s.get('allow_external_queries', True))
    s['allow_external_queries'] = not cur
    write_settings(s)
    return jsonify({"ok": True, "allow_external_queries": s['allow_external_queries']})

if __name__ == '__main__':
    # Ensure logs file exists
    if not os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'w') as f:
            json.dump([], f)
    # Ensure users file exists (loaded by load_users)
    _ = load_users()
    app.run(host='0.0.0.0', port=5000, debug=True)
