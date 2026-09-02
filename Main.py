"""
النسخة 1.0 للاستضافة - بوت موحد جاهز لـ Render / Railway
يشمل: واجهة ويب للتجربة + واتساب ويب هوك + بوت التقارير والبرمجة
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V1")

# مفاتيح - سيتم وضعها في Render Environment Variables
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

class ChatRequest(BaseModel):
    message: str

# ========== واجهة الويب للتجربة السريعة ==========
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html dir="rtl" lang="ar">
    <head><meta charset="utf-8"><title>بوت التقارير والبرمجة</title>
    <style>
    body{font-family:Tahoma;background:#f5f7fb;padding:30px;max-width:800px;margin:auto}
    .card{background:white;padding:25px;border-radius:15px;box-shadow:0 5px 15px rgba(0,0,0,0.1)}
    input,textarea{width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:8px}
    button{background:#0a7cff;color:white;padding:12px 25px;border:none;border-radius:8px;cursor:pointer}
    #answer{background:#f0f4ff;padding:15px;border-radius:8px;margin-top:15px;white-space:pre-wrap}
    </style></head>
    <body>
    <div class="card">
    <h2>🤖 البوت شغال - V1.0</h2>
    <p>هذه الواجهة لتجربة البوت قبل ربط الواتساب</p>
    <textarea id="msg" rows="3" placeholder="مثال: اكتب لي تقرير عن سوق التمور في القصيم أو حلل لي هذا الكود..."></textarea>
    <button onclick="send()">إرسال للبوت</button>
    <div id="answer">الإجابة ستظهر هنا...</div>
    </div>
    <script>
    async function send(){
        const msg=document.getElementById('msg').value;
        document.getElementById('answer').innerText='⏳ البوت يفكر...';
        const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
        const data=await res.json();
        document.getElementById('answer').innerText=data.reply;
    }
    </script>
    </body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0", "openai_configured": bool(OPENAI_KEY)}

@app.post("/chat")
def chat(req: ChatRequest):
    if not client:
        return {"reply": "❌ OPENAI_API_KEY غير موجود في الإعدادات"}
    
    system_prompt = """
    أنت مساعد ذكي في بريدة - وظيفتك:
    1. إذا طلب تقرير: ابدأ بـ [تقرير] واكتب هيكل تقرير سريع (ملخص+نقاط+توصيات)
    2. إذا طلب برمجة أو تحليل بيانات: ابدأ بـ [كود] واكتب الكود مع شرح عربي مختصر
    3. تحدث بالعربية بلهجة سعودية خفيفة ومفهومة
    4. ردودك قصيرة (واتساب) إلا إذا طلب تقرير مفصل
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":req.message}],
            temperature=0.5
        )
        return {"reply": res.choices[0].message.content}
    except Exception as e:
        return {"reply": f"خطأ: {str(e)}"}

# ========== واتساب Webhook ==========
@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge", 0))
    return {"error": "verification failed"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    print("Webhook received:", body)
    try:
        entry = body['entry'][0]['changes'][0]['value']
        if 'messages' in entry:
            msg = entry['messages'][0]
            from_number = msg['from']
            text = msg.get('text', {}).get('body', '')
            
            # رد عبر نفس منطق /chat
            reply_text = chat(ChatRequest(message=text))['reply']
            send_whatsapp(from_number, reply_text)
    except Exception as e:
        print(f"Webhook error: {e}")
    return {"status": "ok"}

def send_whatsapp(to: str, text: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        print("WhatsApp not configured, skipping")
        return
    url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text[:3500]}
    }
    requests.post(url, headers=headers, json=data)

# للتشغيل المحلي
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
