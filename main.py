"""
AI Agents Bot - V2.1 Fixed - يحل مشكلة proxies
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V2.1", version="2.1")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

# إنشاء عميل OpenAI بشكل آمن - لا يطيح السيرفر إذا فشل
client = None
if OPENAI_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        print("✅ OpenAI client created")
    except Exception as e:
        print(f"⚠️ OpenAI client failed: {e}")
        client = None

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = """
أنت مساعد AI Agents - بوت ذكي في السعودية.
1. [تقرير] إذا طلب تقرير: اكتب تقرير احترافي (ملخص+نقاط+توصيات)
2. [كود] إذا طلب برمجة: اكتب الكود مع شرح عربي مختصر
3. تحدث عربية بلهجة سعودية خفيفة، ردودك مختصرة للواتساب إلا إذا طلب تفصيل
"""

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ مربوط" if client else "❌ يحتاج OPENAI_API_KEY أو خطأ في المكتبة"
    wa_status = "✅ مربوط" if WHATSAPP_TOKEN else "⚠️ غير مربوط"
    return f"""
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Agents Bot - V2.1</title>
    <style>
        body{{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;margin:0}}
        .container{{max-width:900px;margin:auto}}
        .card{{background:white;padding:25px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2);margin-bottom:20px}}
        .badge{{padding:6px 12px;border-radius:20px;font-size:13px;background:#f0f4ff;margin:3px;display:inline-block}}
        textarea{{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:15px;resize:vertical;box-sizing:border-box}}
        button{{background:#667eea;color:white;padding:12px 28px;border:none;border-radius:10px;cursor:pointer;font-weight:bold}}
        #answer{{background:#f8f9ff;padding:16px;border-radius:12px;margin-top:15px;white-space:pre-wrap;line-height:1.7;border:1px solid #e8eaff;min-height:60px}}
        .ex{{background:#f0f0f0;padding:6px 12px;border-radius:15px;font-size:12px;cursor:pointer;margin:3px;display:inline-block}}
    </style></head><body><div class="container"><div class="card">
    <h2>🤖 البوت شغال - V2.1 Fixed ✅</h2>
    <div><span class="badge">OpenAI: {status}</span><span class="badge">WhatsApp: {wa_status}</span><span class="badge">Live</span></div>
    <div style="margin:10px 0">
        <span class="ex" onclick="setEx('اكتب تقرير عن سوق التمور في القصيم')">📊 تقرير تمور</span>
        <span class="ex" onclick="setEx('اكتب كود بايثون يحلل مبيعات من اكسل')">💻 كود تحليل</span>
        <span class="ex" onclick="setEx('وش أفضل طريقة لبدء متجر إلكتروني؟')">💡 مشروع</span>
    </div>
    <textarea id="msg" rows="4" placeholder="اكتب رسالتك هنا..."></textarea>
    <div style="margin-top:10px"><button onclick="send()">إرسال 🚀</button></div>
    <div id="answer">الإجابة ستظهر هنا...</div></div></div>
    <script>
        function setEx(t){{document.getElementById('msg').value=t;}}
        async function send(){{
            const msg=document.getElementById('msg').value.trim();if(!msg)return;
            const ans=document.getElementById('answer');ans.innerText='⏳ يفكر...';
            try{{const res=await fetch('/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:msg}})}});
            const data=await res.json();ans.innerText=data.reply||'ما وصل رد';}}catch(e){{ans.innerText='❌ '+e.message;}}
        }}
    </script></body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.1", "openai": bool(client), "whatsapp": bool(WHATSAPP_TOKEN)}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "❌ OPENAI_API_KEY غير موجود أو فيه خطأ في الإعداد. تأكد من إضافته في Render > Environment"}
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":req.message}],
            temperature=0.6,
            max_tokens=2000
        )
        return {"reply": res.choices[0].message.content}
    except Exception as e:
        return {"reply": f"❌ خطأ: {str(e)}"}

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
