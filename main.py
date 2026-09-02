"""
AI Agents Bot - V3.0 Groq - مجاني وسريع
يستخدم Groq Llama 3.1 بدل OpenAI
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V3 Groq", version="3.0")

GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")  # يدعم الاثنين
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

client = None
model_name = "llama-3.3-70b-versatile"

if GROQ_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        print(f"✅ Groq client created - Model: {model_name}")
    except Exception as e:
        print(f"⚠️ Groq failed, trying OpenAI compatible: {e}")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
            print("✅ Groq via OpenAI client created")
        except Exception as e2:
            print(f"❌ Both failed: {e2}")
            client = None

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = """
أنت مساعد AI Agents - بوت ذكي في السعودية، تعمل على Groq Llama 3.3.

مهامك:
1. [تقرير] إذا طلب تقرير: اكتب تقرير احترافي (ملخص تنفيذي + نقاط رئيسية + توصيات)
2. [كود] إذا طلب برمجة: اكتب الكود مع شرح عربي مختصر وتعليقات
3. [بحث] إذا طلب معلومات: لخص الإجابة بشكل مفيد
4. تحدث عربية بلهجة سعودية خفيفة، ردودك مختصرة للواتساب إلا إذا طلب تفصيل
5. أنت سريع جداً بفضل Groq
"""

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Groq مربوط" if client else "❌ يحتاج GROQ_API_KEY"
    wa_status = "✅ مربوط" if WHATSAPP_TOKEN else "⚠️ غير مربوط"
    return f"""
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Agents Bot - V3 Groq</title>
    <style>
        body{{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#00d2ff 0%,#3a7bd5 100%);min-height:100vh;padding:20px;margin:0}}
        .container{{max-width:900px;margin:auto}}
        .card{{background:white;padding:25px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2);margin-bottom:20px}}
        .badge{{padding:6px 12px;border-radius:20px;font-size:13px;background:#e0f7ff;margin:3px;display:inline-block}}
        .badge-green{{background:#e0ffe0}}
        textarea{{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:15px;resize:vertical;box-sizing:border-box}}
        button{{background:#3a7bd5;color:white;padding:12px 28px;border:none;border-radius:10px;cursor:pointer;font-weight:bold;font-size:15px}}
        button:hover{{background:#2a6bc5}}
        #answer{{background:#f8fbff;padding:16px;border-radius:12px;margin-top:15px;white-space:pre-wrap;line-height:1.8;border:1px solid #d0e8ff;min-height:60px}}
        .ex{{background:#f0f8ff;padding:6px 12px;border-radius:15px;font-size:12px;cursor:pointer;margin:3px;display:inline-block;border:1px solid #d0e8ff}}
        .ex:hover{{background:#d0e8ff}}
    </style></head><body><div class="container"><div class="card">
    <h2>⚡ البوت شغال - V3.0 Groq (مجاني وسريع)</h2>
    <div><span class="badge badge-green">{status}</span><span class="badge">WhatsApp: {wa_status}</span><span class="badge">Model: {model_name}</span><span class="badge badge-green">Live ✅</span></div>
    <p style="color:#666;font-size:13px">Groq أسرع 10x من OpenAI ومجاني تماماً</p>
    <div style="margin:10px 0">
        <span class="ex" onclick="setEx('اكتب تقرير عن سوق التمور في القصيم مع أرقام')">📊 تقرير تمور</span>
        <span class="ex" onclick="setEx('اكتب كود بايثون يحلل مبيعات من ملف اكسل ويرسم بياني')">💻 كود تحليل</span>
        <span class="ex" onclick="setEx('وش أفضل 5 مشاريع صغيرة في بريدة برأس مال 20 ألف؟')">💡 مشاريع</span>
        <span class="ex" onclick="setEx('اشرح لي كيف أربط بوت واتساب مع قاعدة بيانات')">🔗 ربط واتساب</span>
    </div>
    <textarea id="msg" rows="4" placeholder="اكتب رسالتك هنا..."></textarea>
    <div style="margin-top:12px;display:flex;gap:10px">
        <button onclick="send()">إرسال ⚡</button>
        <button onclick="clearAll()" style="background:#eee;color:#333">مسح</button>
    </div>
    <div id="answer">الإجابة ستظهر هنا...</div></div>
    <div class="card" style="font-size:13px"><h4>✅ تم التحويل لـ Groq</h4><p>لا يحتاج رصيد، مجاني وسريع جداً. الموديل: Llama 3.1 70B</p></div>
    </div>
    <script>
        function setEx(t){{document.getElementById('msg').value=t;}}
        function clearAll(){{document.getElementById('msg').value='';document.getElementById('answer').innerText='الإجابة ستظهر هنا...';}}
        async function send(){{
            const msg=document.getElementById('msg').value.trim();if(!msg)return;
            const ans=document.getElementById('answer');ans.innerText='⚡ البوت يفكر بسرعة Groq...';
            try{{const res=await fetch('/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:msg}})}});
            const data=await res.json();ans.innerText=data.reply||'ما وصل رد';}}catch(e){{ans.innerText='❌ '+e.message;}}
        }}
    </script></body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0-groq", "groq": bool(client), "model": model_name, "whatsapp": bool(WHATSAPP_TOKEN)}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "❌ GROQ_API_KEY غير موجود. روح Render > Environment > Add Variable > GROQ_API_KEY = gsk_..."}
    try:
        res = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": req.message}
            ],
            temperature=0.6,
            max_tokens=3000
        )
        return {"reply": res.choices[0].message.content}
    except Exception as e:
        return {"reply": f"❌ خطأ Groq: {str(e)}"}

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
