"""
AI Agents Bot - V4.2 Stocks + New Models
- أسعار لحظية
- موديلات Groq الجديدة بعد إيقاف Llama 3.1
"""
import os
import re
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V4.2 Stocks", version="4.2")

GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

WORKING_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]
model_name = WORKING_MODELS[0]
client = None

if GROQ_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        print(f"✅ Groq - Models: {WORKING_MODELS}")
    except Exception as e:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
        except Exception as e2:
            print(f"❌ {e2}")
            client = None

SAUDI_SYMBOLS = {
    "ارامكو": "2222.SR", "أرامكو": "2222.SR", "2222": "2222.SR",
    "الراجحي": "1120.SR", "راجحي": "1120.SR", "1120": "1120.SR",
    "سابك": "2010.SR", "2010": "2010.SR",
    "STC": "7010.SR", "7010": "7010.SR",
    "الاهلي": "1180.SR", "1180": "1180.SR",
}

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = "أنت مساعد AI Agents - بوت ذكي في السعودية، متخصص في التقارير والبرمجة والأسهم. حلل الأسهم مع تنبيه أنها ليست نصيحة استثمارية. لهجة سعودية خفيفة."

def get_stock_price(symbol: str) -> Dict:
    symbol = symbol.strip().upper()
    if symbol in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[symbol]
    if symbol.isdigit() and len(symbol) == 4:
        symbol = f"{symbol}.SR"
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, params={"interval": "1d", "range": "1d"}, timeout=8)
        data = r.json()
        if "chart" not in data or data["chart"]["error"]:
            return {"error": f"الرمز {symbol} غير موجود", "symbol": symbol}
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        prev_close = meta.get("previousClose")
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {
            "symbol": symbol,
            "name": meta.get("longName") or meta.get("shortName") or symbol,
            "price": round(float(price), 2) if price else None,
            "prev_close": round(float(prev_close), 2) if prev_close else None,
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "currency": meta.get("currency", "SAR"),
            "market": meta.get("exchangeName", ""),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def detect_stock_symbols(text: str) -> List[str]:
    found = []
    text_upper = text.upper()
    for m in re.findall(r'\b(\d{4})\b', text):
        found.append(m)
    for arabic in SAUDI_SYMBOLS.keys():
        if arabic in text or arabic.upper() in text_upper:
            found.append(arabic)
    return list(set(found))[:3]

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Groq" if client else "❌"
    wa_status = "✅" if WHATSAPP_TOKEN else "⚠️"
    html = """
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Agents Bot - V4.2 Stocks New Models</title>
    <style>
        body{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#0f2027 0%,#203a43 50%,#2c5364 100%);min-height:100vh;padding:20px;margin:0;color:#fff}
        .container{max-width:1000px;margin:auto}
        .card{background:white;color:#222;padding:22px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.3);margin-bottom:18px}
        .badge{padding:5px 11px;border-radius:20px;font-size:12px;background:#e0f7ff;margin:3px;display:inline-block}
        .badge-green{background:#d4edda} .badge-blue{background:#cce5ff} .badge-orange{background:#fff3cd}
        .stock-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:12px 0}
        .stock-card{background:#f8f9ff;border:1px solid #d0e0ff;border-radius:14px;padding:14px;text-align:center;cursor:pointer}
        .price{font-size:22px;font-weight:bold} .up{color:#28a745} .down{color:#dc3545}
        textarea{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:14px;box-sizing:border-box}
        button{background:#2c5364;color:white;padding:11px 22px;border:none;border-radius:10px;cursor:pointer;font-weight:bold;margin:3px}
        #answer{background:#f8fbff;padding:15px;border-radius:12px;margin-top:12px;white-space:pre-wrap;line-height:1.7;border:1px solid #d0e0ff;min-height:60px;color:#222}
        .ex{background:#eef6ff;padding:6px 12px;border-radius:15px;font-size:11px;cursor:pointer;margin:3px;display:inline-block}
        input{padding:10px;border:1px solid #ddd;border-radius:8px;width:140px}
        .alert{background:#fff3cd;padding:10px;border-radius:8px;font-size:12px;margin:10px 0}
    </style></head><body><div class="container">
    <div class="card">
        <h2>📈 V4.2 أسهم + موديلات Groq الجديدة</h2>
        <div class="alert">⚠️ Llama 3.1 تم إيقافه. نستخدم الآن: openai/gpt-oss-20b (السريع) و gpt-oss-120b (الأقوى)</div>
        <div><span class="badge badge-green">__STATUS__</span><span class="badge">WhatsApp: __WA__</span><span class="badge badge-blue">Stocks Live</span><span class="badge badge-orange">__MODEL__</span></div>
        <h4 style="margin:15px 0 8px">🔥 أسهم سريعة:</h4>
        <div class="stock-grid" id="stocks"></div>
        <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap">
            <input id="sym" placeholder="2222 أو AAPL" value="2222">
            <button onclick="fetchOne()">جلب السعر</button>
            <button onclick="loadAll()" style="background:#eee;color:#222">تحديث الكل</button>
        </div>
    </div>
    <div class="card">
        <h4>💬 اسأل البوت</h4>
        <div style="margin:8px 0">
            <span class="ex" onclick="setEx('كم سعر سهم ارامكو الآن؟')">📊 ارامكو</span>
            <span class="ex" onclick="setEx('حلل لي سهم الراجحي 1120')">📈 الراجحي</span>
            <span class="ex" onclick="setEx('وش وضع تسلا اليوم؟')">🚗 تسلا</span>
        </div>
        <textarea id="msg" rows="3" placeholder="مثال: كم سعر ارامكو؟"></textarea>
        <div style="margin-top:10px"><button onclick="send()">إرسال ⚡</button></div>
        <div id="answer">الإجابة ستظهر هنا...</div>
    </div>
    </div>
    <script>
        const quick = ["2222","1120","2010","7010","1180","AAPL","TSLA"];
        async function loadAll(){
            const grid=document.getElementById('stocks'); grid.innerHTML='⏳...';
            try{
                const res=await fetch('/stocks?symbols='+quick.join(',')); const data=await res.json();
                grid.innerHTML='';
                data.forEach(s=>{
                    if(s.error) return;
                    const cls=s.change>=0?'up':'down'; const arrow=s.change>=0?'▲':'▼';
                    grid.innerHTML+=`<div class="stock-card" onclick="document.getElementById('sym').value='${s.symbol}';fetchOne()"><div style="font-size:12px;color:#666">${s.name}</div><div style="font-weight:bold">${s.symbol}</div><div class="price">${s.price} ${s.currency}</div><div class="${cls}">${arrow} ${s.change} (${s.change_pct}%)</div></div>`;
                });
            }catch(e){grid.innerHTML='❌ '+e.message;}
        }
        async function fetchOne(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return;
            const ans=document.getElementById('answer'); ans.innerText='⏳ جلب '+sym+'...';
            try{
                const res=await fetch('/stock/'+encodeURIComponent(sym)); const data=await res.json();
                if(data.error) ans.innerText='❌ '+data.error;
                else ans.innerText=`📈 ${data.name} (${data.symbol})\\nالسعر: ${data.price} ${data.currency}\\nالتغيير: ${data.change} (${data.change_pct}%)\\nالسابق: ${data.prev_close}\\nالوقت: ${data.time}`;
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        function setEx(t){document.getElementById('msg').value=t;}
        async function send(){
            const msg=document.getElementById('msg').value.trim(); if(!msg) return;
            const ans=document.getElementById('answer'); ans.innerText='⚡ يحلل...';
            try{
                const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
                const data=await res.json(); ans.innerText=data.reply+(data.model_used?'\\n\\n---\\nالموديل: '+data.model_used:'');
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        loadAll();
    </script></body></html>
    """
    html = html.replace("__STATUS__", status).replace("__WA__", wa_status).replace("__MODEL__", model_name)
    return HTMLResponse(content=html)

@app.get("/health")
def health():
    return {"status": "ok", "version": "4.2-stocks-new-models", "models": WORKING_MODELS}

@app.get("/stock/{symbol}")
def stock_one(symbol: str):
    return get_stock_price(symbol)

@app.get("/stocks")
def stocks_many(symbols: str = Query(...)):
    syms = [s.strip() for s in symbols.split(",") if s.strip()][:10]
    return [get_stock_price(s) for s in syms]

@app.get("/models")
def list_models():
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
    detected = detect_stock_symbols(req.message)
    stock_context = ""
    if detected:
        stock_data = []
        for sym in detected:
            data = get_stock_price(sym)
            if "error" not in data:
                stock_data.append(data)
        if stock_data:
            stock_context = "\n\n[أسهم لحظية Yahoo]:\n"
            for d in stock_data:
                stock_context += f"- {d['name']} ({d['symbol']}): {d['price']} {d['currency']} | {d['change']} ({d['change_pct']}%)\n"
    
    last_error = None
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT + stock_context},
                    {"role": "user", "content": req.message}
                ],
                temperature=0.6,
                max_tokens=3500
            )
            return {"reply": res.choices[0].message.content, "model_used": current_model, "stocks_detected": detected}
        except Exception as e:
            last_error = str(e)
            if any(x in last_error.lower() for x in ["model", "decommissioned", "not_found", "does not exist", "404", "400"]):
                continue
            else:
                break
    return {"reply": f"❌ فشل: {last_error}\nالموديلات: {', '.join(WORKING_MODELS)}"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge", 0))
    return JSONResponse({"error": "failed"}, status_code=403)

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
