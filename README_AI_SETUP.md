Enabling OpenAI fallback for MMEC Chatbot

1) Create a .env file in the project root (same folder as app.py) and add:

OPENAI_API_KEY=sk-...your key...
ALLOW_EXTERNAL_QUERIES=1

2) Restart the Flask server (stop existing server and start again).

PowerShell example:

# from project root
$env:OPENAI_API_KEY='sk-...'
$env:ALLOW_EXTERNAL_QUERIES='1'
Start-Process -FilePath python -ArgumentList 'app.py' -WorkingDirectory 'C:\Users\Nida\OneDrive\Desktop\Mmec_Chatbot-main\Mmec_Chatbot-main' -NoNewWindow

3) Test status and a sample query:

curl.exe -s http://127.0.0.1:5000/api/status

# Example query (PowerShell preferred):
$body = @{ message='Tell me about placements at MMEC'; role='Student' } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/query -Method Post -ContentType 'application/json' -Body $body

If the server returns an AI response, you'll see `source: "ai"` and a prefixed disclaimer in the answer.

Notes:
- The server's `call_gemini()` prefers Gemini if GEMINI_API_KEY is set, but Gemini call is not implemented in this repo. OpenAI is used as a fallback when configured.
- The Admin UI toggle writes to `data/settings.json` but an environment variable `ALLOW_EXTERNAL_QUERIES` overrides that setting while present.
