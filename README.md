# MMEC AI Chatbot

Minimal prototype of Maratha Mandal Engineering College (MMEC) AI Chatbot.

Files:
- `index.html` — Frontend (single-file app)
- `app.py` — Flask backend (serves `index.html` and provides `/api/query` and `/api/logs`)
- `users.json` — Default credentials for demo
- `requirements.txt` — Combined dependency file (Flask, requests)

Run locally:

```powershell
pip install -r requirements.txt
python app.py
# Open http://localhost:5000 in a browser
```

API key (optional):
- To enable AI responses, set `GEMINI_API_KEY` or `OPENAI_API_KEY` in your environment and implement the provider call in `app.py`.
- Do NOT commit API keys into the repository.

Notes:
- Local images were replaced with public links. If you want to use local images, place them next to `index.html` and update the `<img>`/background URLs.
- This is a demo: passwords are stored in plain JSON only for prototyping. Replace with proper auth in production.


