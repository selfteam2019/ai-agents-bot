"""
AI Agents Bot - V3.2 Groq - Llama 3.1 70B -> Llama 3.3 70B
Llama 3.1 70B تم إيقافه رسمياً في Groq يوم 16 أغسطس 2026
البديل الرسمي: Llama 3.3 70B (نفس المعمارية + أداء أفضل)
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V3.2 Groq Llama 3.3", version="3.2")

GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

client = None

# Llama 3.1 70B تم إيقافه - هذه البدائل الرسمية من Groq
# حسب Groq Docs: Llama 3.3 70B هو البديل المباشر لنفس المعمارية مع تحسينات
WORKING_MODELS = [
    "llama-3.3-70b-versatile",                 # البديل المباشر لـ Llama 3.1 70B - نفس الحجم، أداء أفضل
    "openai/gpt-oss-20b",                     # توصية Groq الجديدة للمجاني
    "openai/gpt-oss-120b",                    # الأقوى 120B
    "meta-llama/llama-4-maverick-17b-128e-instruct",  # Llama 4 الجديد
    "llama-3.1-8b-instant",                   # السريع - قد يكون متقاعد أيضاً
]

model_name = WORKING_MODELS[0]

if GROQ_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        print(f"✅ Groq client - Llama 3.1 70B -> {model_name} (successor)")
    except Exception as e:
        print(f"⚠️ Groq init failed: {e}")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
            print("✅ Groq via OpenAI client")
        except Exception as e2:
            print(f"❌ Failed: {e2}")
            client = None

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = """
أنت مساعد AI Agents - بوت ذكي في السعودية.

كنت تعمل على Llama 3.1 70B، الآن تم ترقيتك إلى Llama 3.3 70B (نفس المعمارية 70B مع تحسينات في الاستدلال والبرمجة والرياضيات).

مهامك:
1. [تقرير] إذا طلب تقرير: اكتب تقرير احترافي (ملخص تنفيذي + نقاط رئيسية + توصيات + أرقام تقريبية)
2. [كود] إذا طلب برمجة: اكتب الكود مع شرح عربي مختصر وتعليقات داخل الكود
3. تحدث عربية بلهجة سعودية خفيفة، ردودك مختصرة للواتساب إلا إذا طلب تفصيل
4. أنت سريع جداً بفضل Groq LPU
"""

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Groq مربوط" if client else "❌ يحتاج GROQ_API_KEY"
    wa_status = "✅ مربوط" if WHATSAPP_TOKEN else "⚠️ غير مربوط"
    models_html = "".join([f"<span class='badge'>{m}</span>" for m in WORKING_MODELS])
    return f"""
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Agents Bot - Llama 3.3 70B</title>
    <style>
        body{{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#1a2980 0%,#26d0ce 100%);min-height:100vh;padding:20px;margin:0}}
        .container{{max-width:950px;margin:auto}}
        .card{{background:white;padding:25px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2);margin-bottom:20px}}
        .badge{{padding:6px 12px;border-radius:20px;font-size:12px;background:#e0f7ff;margin:3px;display:inline-block;border:1px solid #b0e0ff}}
        .badge-green{{background:#e0ffe0;border-color:#a0e0a0}}
        .badge-orange{{background:#fff3e0;border-color:#ffcc80}}
        textarea{{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:15px;resize:vertical;box-sizing:border-box}}
        button{{background:#1a2980;color:white;padding:12px 28px;border:none;border-radius:10px;cursor:pointer;font-weight:bold}}
        #answer{{background:#f8fbff;padding:16px;border-radius:12px;margin-top:15px;white-space:pre-wrap;line-height:1.8;border:1px solid #d0e8ff;min-height:80px}}
        .ex{{background:#f0f8ff;padding:7px 13px;border-radius:15px;font-size:12px;cursor:pointer;margin:4px;display:inline-block;border:1px solid #d0e8ff}}
        .alert{{background:#fff3cd;padding:12px;border-radius:10px;border:1px solid #ffe69c;font-size:13px;margin:10px 0}}
    </style></head><body><div class="container"><div class="card">
    <h2>🚀 البوت شغال - Llama 3.3 70B (خليفة Llama 3.1 70B)</h2>
    <div class="alert">⚠️ <b>Llama 3.1 70B</b> تم إيقافه رسمياً من Groq يوم 16 أغسطس 2026. البديل الرسمي هو <b>Llama 3.3 70B</b> - نفس المعمارية 70B مع أداء أفضل في البرمجة والاستدلال.</div>
    <div><span class="badge badge-green">{status}</span><span class="badge">WhatsApp: {wa_status}</span><span class="badge badge-green">Live ✅</span></div>
    <p style="font-size:12px;color:#666">الموديلات المجربة تلقائياً:</p>
    <div>{models_html}</div>
    <div style="margin:15px 0">
        <span class="ex" onclick="setEx('اكتب تقرير عن سوق التمور في القصيم مع أرقام وتوصيات')">📊 تقرير تمور</span>
        <span class="ex" onclick="setEx('اكتب كود بايثون يحلل مبيعات من ملف اكسل ويرسم بياني مع شرح')">💻 كود تحليل</span>
        <span class="ex" onclick="setEx('وش أفضل 5 مشاريع صغيرة في بريدة برأس مال 20 ألف؟')">💡 مشاريع بريدة</span>
    </div>
    <textarea id="msg" rows="4" placeholder="اكتب رسالتك هنا..."></textarea>
    <div style="margin-top:12px;display:flex;gap:10px">
        <button onclick="send()">إرسال ⚡ Llama 3.3</button>
        <button onclick="clearAll()" style="background:#eee;color:#333">مسح</button>
    </div>
    <div id="answer">الإجابة ستظهر هنا...</div></div></div>
    <script>
        function setEx(t){{document.getElementById('msg').value=t;}}
        function clearAll(){{document.getElementById('msg').value='';document.getElementById('answer').innerText='الإجابة ستظهر هنا...';}}
        async function send(){{
            const msg=document.getElementById('msg').value.trim();if(!msg)return;
            const ans=document.getElementById('answer');ans.innerText='⚡ يجرب Llama 3.3 70B...';
            try{{const res=await fetch('/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:msg}})}});
            const data=await res.json();ans.innerText=data.reply+(data.model_used?`\\n\\n---\\nالموديل: ${{data.model_used}}`:'');}}catch(e){{ans.innerText='❌ '+e.message;}}
        }}
    </script></body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.2-llama3.3", "note": "Llama 3.1 70B decommissioned, using Llama 3.3 70B as successor", "groq": bool(client), "models_tried": WORKING_MODELS}

@app.get("/models")
def list_models():
    """يعرض الموديلات المتاحة في حسابك"""
    if not client:
        return {"error": "No GROQ_API_KEY"}
    try:
        models = client.models.list()
        return {"available": [m.id for m in models.data], "trying": WORKING_MODELS}
    except Exception as e:
        return {"error": str(e), "trying": WORKING_MODELS}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "❌ GROQ_API_KEY غير موجود"}
    
    last_error = None
    for current_model in WORKING_MODELS:
        try:
            print(f"🔄 Trying {current_model}...")
            res = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": req.message}
                ],
                temperature=0.6,
                max_tokens=3500
            )
            print(f"✅ Success: {current_model}")
            return {"reply": res.choices[0].message.content, "model_used": current_model}
        except Exception as e:
            last_error = str(e)
            print(f"❌ {current_model} failed: {e}")
            if any(x in last_error.lower() for x in ["model", "decommissioned", "not_found", "does not exist", "404", "400"]):
                continue
            else:
                break
    
    return {"reply": f"❌ كل الموديلات فشلت.\nآخر خطأ: {last_error}\n\nالموديلات المجربة: {', '.join(WORKING_MODELS)}\n\nملاحظة: Llama 3.1 70B تم إيقافه يوم 16 أغسطس 2026، جرب Llama 3.3 70B أو openai/gpt-oss-20b"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge", 0))
    return JSONResponse({"error": "verification failed"}, status_code=403)

@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    from_number = msg.get("from")
                    text = msg.get("text", {}).get("body", "") if msg.get("type") == "text" else ""
                    if not text: continue
                    reply_data = chat_endpoint(ChatRequest(message=text))
                    send_whatsapp_message(from_number, reply_data.get("reply", "عذراً"))
    except Exception as e:
        print(f"Webhook error: {e}")
    return {"status": "ok"}

def send_whatsapp_message(to: str, text: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID: return
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:3800]}}
    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
