"""
نسخة مضمونة 100% للاستضافة - بدون أي مكتبة ثقيلة
V1.1 - Fixed Build
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html dir="rtl"><head><meta charset="utf-8"><title>البوت شغال</title>
    <style>body{font-family:Tahoma;background:#f6f8ff;padding:30px}
    .card{background:white;padding:25px;border-radius:15px;max-width:700px;margin:auto;box-shadow:0 4px 15px rgba(0,0,0,.1)}
    textarea{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px}
    button{background:#0a7cff;color:white;padding:12px 20px;border:0;border-radius:8px;cursor:pointer;margin-top:10px}
    #a{background:#eef2ff;padding:12px;border-radius:8px;margin-top:15px;white-space:pre-wrap}
    </style></head><body><div class="card">
    <h2>✅ البوت شغال - V1.1</h2>
    <p>تم حل مشكلة البناء. جرب البوت:</p>
    <textarea id="m" rows="3" placeholder="اكتب: تقرير عن سوق التمور في القصيم"></textarea>
    <button onclick="send()">إرسال</button>
    <div id="a">الرد يظهر هنا...</div>
    </div><script>
    async function send(){
      let m=document.getElementById('m').value;
      document.getElementById('a').innerText='⏳ ثواني...';
      let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
      let d=await r.json();document.getElementById('a').innerText=d.reply;
    }
    </script></body></html>
    """

@app.get("/health")
def health():
    return {"status":"ok","version":"1.1_fixed"}

@app.post("/chat")
def chat(req: ChatRequest):
    # حتى لو OPENAI_API_KEY مو موجود، البوت ما يطيح
    try:
        from openai import OpenAI
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            return {"reply": "⚠️ البوت شغال لكن OPENAI_API_KEY غير مضاف. روح Render > Environment وأضفه."}
        client = OpenAI(api_key=key)
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":req.message}],
            max_tokens=500
        )
        return {"reply": res.choices[0].message.content}
    except Exception as e:
        return {"reply": f"البوت شغال لكن صار خطأ: {str(e)[:300]}"}

@app.get("/webhook")
async def verify(request: Request):
    p=request.query_params
    if p.get("hub.verify_token")=="buraydah123":
        return int(p.get("hub.challenge",0))
    return {"ok":True}

@app.post("/webhook")
async def hook(request: Request):
    return {"status":"ok"}
