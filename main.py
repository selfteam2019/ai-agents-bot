"""
AI Agents Bot - V2.0 Full Version
جاهز لـ Render Docker + WhatsApp Cloud API + OpenAI
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V2", version="2.0")

# إعدادات من Environment Variables في Render
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = """
أنت مساعد AI Agents - بوت ذكي في السعودية.

مهامك:
1. [تقرير] إذا طلب تقرير: اكتب تقرير احترافي (ملخص تنفيذي + نقاط رئيسية + توصيات + مصادر مقترحة)
2. [كود] إذا طلب برمجة: اكتب الكود مع شرح عربي مختصر وتعليقات في الكود
3. [بحث] إذا طلب معلومات حديثة: لخص الإجابة كأنك بحثت، واقترح مصادر
4. تحدث عربية بلهجة سعودية خفيفة، ردودك مختصرة للواتساب إلا إذا طلب تفصيل
5. إذا الرسالة غير واضحة، اسأل سؤال توضيحي واحد فقط
"""

# ========== الصفحة الرئيسية ==========
@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ مربوط" if OPENAI_KEY else "❌ يحتاج OPENAI_API_KEY"
    wa_status = "✅ مربوط" if WHATSAPP_TOKEN else "⚠️ غير مربوط"
    return f"""
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>AI Agents Bot - V2.0</title>
        <style>
            body{{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;margin:0}}
            .container{{max-width:900px;margin:auto}}
            .card{{background:white;padding:25px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2);margin-bottom:20px}}
            .status{{display:flex;gap:10px;flex-wrap:wrap;margin:15px 0}}
            .badge{{padding:6px 12px;border-radius:20px;font-size:13px;background:#f0f4ff}}
            textarea{{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:15px;resize:vertical;box-sizing:border-box}}
            textarea:focus{{border-color:#667eea;outline:none}}
            button{{background:#667eea;color:white;padding:12px 28px;border:none;border-radius:10px;cursor:pointer;font-size:15px;font-weight:bold;transition:0.2s}}
            button:hover{{background:#5a6fd6;transform:translateY(-1px)}}
            #answer{{background:#f8f9ff;padding:16px;border-radius:12px;margin-top:15px;white-space:pre-wrap;line-height:1.7;border:1px solid #e8eaff;min-height:60px}}
            .examples{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}
            .ex{{background:#f0f0f0;padding:6px 12px;border-radius:15px;font-size:12px;cursor:pointer}}
            .ex:hover{{background:#e0e0e0}}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h2>🤖 البوت شغال - V2.0</h2>
                <div class="status">
                    <span class="badge">OpenAI: {status}</span>
                    <span class="badge">WhatsApp: {wa_status}</span>
                    <span class="badge">الحالة: Live ✅</span>
                </div>
                <p>جرب البوت هنا قبل ربط الواتساب:</p>
                <div class="examples">
                    <span class="ex" onclick="setEx('اكتب تقرير عن سوق التمور في القصيم')">📊 تقرير تمور</span>
                    <span class="ex" onclick="setEx('اكتب كود بايثون يحلل مبيعات من اكسل')">💻 كود تحليل</span>
                    <span class="ex" onclick="setEx('وش أفضل طريقة لبدء متجر إلكتروني؟')">💡 فكرة مشروع</span>
                </div>
                <textarea id="msg" rows="4" placeholder="مثال: اكتب لي تقرير عن سوق التمور، أو حلل لي هذا الكود..."></textarea>
                <div style="margin-top:10px;display:flex;gap:10px">
                    <button onclick="send()">إرسال للبوت 🚀</button>
                    <button onclick="clearAll()" style="background:#eee;color:#333">مسح</button>
                </div>
                <div id="answer">الإجابة ستظهر هنا...</div>
            </div>
            <div class="card" style="font-size:13px">
                <h4>🔧 كيف تربط الواتساب؟</h4>
                <ol style="line-height:2">
                    <li>في Meta for Developers > WhatsApp > Configuration</li>
                    <li>ضع Webhook URL: <code>{os.getenv('RENDER_EXTERNAL_URL', 'https://YOUR-URL.onrender.com')}/webhook</code></li>
                    <li>Verify Token: <code>{VERIFY_TOKEN}</code></li>
                    <li>Subscribe لـ messages</li>
                </ol>
            </div>
        </div>
        <script>
            function setEx(t){{document.getElementById('msg').value=t;}}
            function clearAll(){{document.getElementById('msg').value='';document.getElementById('answer').innerText='الإجابة ستظهر هنا...';}}
            async function send(){{
                const msg=document.getElementById('msg').value.trim();
                if(!msg) return;
                const ans=document.getElementById('answer');
                ans.innerText='⏳ البوت يفكر...';
                try{{
                    const res=await fetch('/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:msg}})}});
                    const data=await res.json();
                    ans.innerText=data.reply || 'ما وصل رد';
                }}catch(e){{ans.innerText='❌ خطأ: '+e.message;}}
            }}
        </script>
    </body></html>
    """

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.0",
        "openai": bool(OPENAI_KEY),
        "whatsapp": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID),
        "verify_token": VERIFY_TOKEN
    }

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "❌ OPENAI_API_KEY غير موجود. روح Render > Environment وأضفه."}
    
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": req.message}
            ],
            temperature=0.6,
            max_tokens=2000
        )
        return {"reply": res.choices[0].message.content}
    except Exception as e:
        return {"reply": f"❌ خطأ من OpenAI: {str(e)}"}

# ========== WhatsApp Webhook ==========
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print(f"✅ Webhook verified: {challenge}")
        return int(challenge) if challenge else 0
    print(f"❌ Verification failed. Expected {VERIFY_TOKEN}, got {token}")
    return JSONResponse({"error": "verification failed"}, status_code=403)

@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    print("📩 Webhook:", body)
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    from_number = msg.get("from")
                    text = msg.get("text", {}).get("body", "") if msg.get("type") == "text" else ""
                    
                    if not text:
                        continue
                    
                    # استدعاء البوت
                    reply_data = chat_endpoint(ChatRequest(message=text))
                    reply_text = reply_data.get("reply", "عذراً، ما قدرت أرد.")
                    
                    send_whatsapp_message(from_number, reply_text)
    except Exception as e:
        print(f"❌ Webhook error: {e}")
    return {"status": "ok"}

def send_whatsapp_message(to: str, text: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        print("⚠️ WhatsApp not configured")
        return
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    # واتساب الحد 4096 حرف
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:3800]}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"📤 WhatsApp send: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"❌ Send error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
