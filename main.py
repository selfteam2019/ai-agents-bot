"""
AI Agents Bot - V4.0 Stocks - متابعة أسهم لحظية
المميزات:
- أسعار لحظية للسوق السعودي (تداول) + الأمريكي
- تحليل فني سريع + تنبيهات
- تكامل مع الشات: إذا سألت عن سهم يجيب سعره لحظياً
"""
import os
import re
import time
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V4 Stocks", version="4.0")

GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

client = None
model_name = "llama-3.1-8b-instant"

if GROQ_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        print(f"✅ Groq client - {model_name}")
    except Exception as e:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
            print("✅ Groq via OpenAI client")
        except Exception as e2:
            print(f"❌ Groq failed: {e2}")
            client = None

# ========== إعدادات الأسهم ==========
# خريطة رموز سعودية مشهورة -> رمز Yahoo
SAUDI_SYMBOLS = {
    "ارامكو": "2222.SR", "أرامكو": "2222.SR", "ARAMCO": "2222.SR", "2222": "2222.SR",
    "الراجحي": "1120.SR", "راجحي": "1120.SR", "1120": "1120.SR",
    "سابك": "2010.SR", "2010": "2010.SR",
    "STC": "7010.SR", "الاتصالات": "7010.SR", "7010": "7010.SR",
    "الاهلي": "1180.SR", "SNB": "1180.SR", "1180": "1180.SR",
    "لوسيد": "LCID", "تسلا": "TSLA", "ابل": "AAPL", "نيو": "NIO",
    "مايكروستراتيجي": "MSTR", "بيتكوين": "BTC-USD", "الذهب": "GC=F"
}

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT = """
أنت مساعد AI Agents - بوت ذكي في السعودية، متخصص في التقارير والبرمجة والأسهم.

مهامك:
1. [تقرير] إذا طلب تقرير: اكتب تقرير احترافي
2. [كود] إذا طلب برمجة: اكتب الكود مع شرح عربي
3. [سهم] إذا سأل عن سهم: إذا أعطيتك بيانات السعر، حللها (هل مرتفع/منخفض، دعم ومقاومة، نصيحة سريعة غير ملزمة)
4. تحدث عربية بلهجة سعودية خفيفة، ردودك مختصرة للواتساب
5. تنبيه: معلومات الأسهم للتوعية فقط وليست نصيحة استثمارية
"""

# ========== دوال الأسهم ==========
def get_stock_price(symbol: str) -> Dict:
    """يجيب سعر سهم من Yahoo Finance بدون مفتاح"""
    symbol = symbol.strip().upper()
    # تحويل الرموز العربية
    if symbol in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[symbol]
    # إذا رقم سعودي بدون .SR أضفها
    if symbol.isdigit() and len(symbol) == 4:
        symbol = f"{symbol}.SR"
    
    try:
        # Yahoo Finance API المجاني (v8)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"interval": "1d", "range": "1d"}
        r = requests.get(url, headers=headers, params=params, timeout=8)
        data = r.json()
        
        if "chart" not in data or data["chart"]["error"]:
            return {"error": f"الرمز {symbol} غير موجود", "symbol": symbol}
        
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        prev_close = meta.get("previousClose")
        change = price - prev_close if price and prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        # بيانات إضافية
        quote = result["indicators"]["quote"][0] if result["indicators"]["quote"] else {}
        
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
            "is_saudi": ".SR" in symbol
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

def detect_stock_symbols(text: str) -> List[str]:
    """يكشف رموز الأسهم في النص"""
    found = []
    text_upper = text.upper()
    
    # رموز سعودية بالأرقام
    for m in re.findall(r'\b(\d{4})\b', text):
        found.append(m)
    
    # رموز عربية مشهورة
    for arabic, sym in SAUDI_SYMBOLS.items():
        if arabic in text or arabic.upper() in text_upper:
            found.append(arabic)
    
    # رموز أمريكية $AAPL أو سهم تسلا
    for m in re.findall(r'\$([A-Z]{1,5})\b', text_upper):
        found.append(m)
    
    # كلمات مفتاحية للأسهم
    stock_keywords = ["سهم", "سعر", "تداول", "ارامكو", "الراجحي", "سابك"]
    if any(k in text for k in stock_keywords):
        # إذا ذكر سهم بدون رمز، حاول استخراج
        if not found:
            found.append("2222")  # افترض أرامكو كمثال
    
    return list(set(found))[:3]  # حد أقصى 3 أسهم

# ========== الواجهة الرئيسية ==========
@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Groq" if client else "❌"
    wa_status = "✅" if WHATSAPP_TOKEN else "⚠️"
    return f"""
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Agents Bot - V4 Stocks</title>
    <style>
        body{{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#0f2027 0%,#203a43 50%,#2c5364 100%);min-height:100vh;padding:20px;margin:0;color:#fff}}
        .container{{max-width:1000px;margin:auto}}
        .card{{background:white;color:#222;padding:22px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.3);margin-bottom:18px}}
        .badge{{padding:5px 11px;border-radius:20px;font-size:12px;background:#e0f7ff;margin:3px;display:inline-block;border:1px solid #b0e0ff}}
        .badge-green{{background:#d4edda;border-color:#a3d9a5}} .badge-blue{{background:#cce5ff}} .badge-orange{{background:#fff3cd}}
        .stock-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:12px 0}}
        .stock-card{{background:#f8f9ff;border:1px solid #d0e0ff;border-radius:14px;padding:14px;text-align:center;cursor:pointer;transition:0.2s}}
        .stock-card:hover{{transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,0.1)}}
        .price{{font-size:22px;font-weight:bold;margin:6px 0}} .up{{color:#28a745}} .down{{color:#dc3545}}
        textarea{{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:14px;box-sizing:border-box}}
        button{{background:#2c5364;color:white;padding:11px 22px;border:none;border-radius:10px;cursor:pointer;font-weight:bold;margin:3px}}
        button:hover{{background:#203a43}}
        #answer{{background:#f8fbff;padding:15px;border-radius:12px;margin-top:12px;white-space:pre-wrap;line-height:1.7;border:1px solid #d0e0ff;min-height:60px;color:#222}}
        .ex{{background:#eef6ff;padding:6px 12px;border-radius:15px;font-size:11px;cursor:pointer;margin:3px;display:inline-block;border:1px solid #d0e0ff}}
        input{{padding:10px;border:1px solid #ddd;border-radius:8px;width:120px}}
    </style></head><body><div class="container">
    
    <div class="card">
        <h2>📈 البوت شغال - V4.0 متابعة أسهم لحظية</h2>
        <div><span class="badge badge-green">Groq: {status}</span><span class="badge">WhatsApp: {wa_status}</span><span class="badge badge-blue">Stocks: Live ✅</span><span class="badge badge-orange">Model: {model_name}</span></div>
        
        <h4 style="margin:15px 0 8px">🔥 أسهم سريعة (اضغط للتحديث):</h4>
        <div class="stock-grid" id="stocks"></div>
        
        <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <input id="sym" placeholder="رمز مثل 2222 أو AAPL" value="2222">
            <button onclick="fetchOne()">جلب السعر</button>
            <button onclick="loadAll()" style="background:#eee;color:#222">تحديث الكل</button>
        </div>
    </div>

    <div class="card">
        <h4>💬 اسأل البوت عن أي سهم</h4>
        <div style="margin:8px 0">
            <span class="ex" onclick="setEx('كم سعر سهم ارامكو الآن؟')">📊 ارامكو</span>
            <span class="ex" onclick="setEx('حلل لي سهم الراجحي 1120')">📈 الراجحي</span>
            <span class="ex" onclick="setEx('وش وضع تسلا اليوم؟')">🚗 تسلا</span>
            <span class="ex" onclick="setEx('اعطني تقرير عن سابك 2010 مع تحليل')">📝 تقرير سابك</span>
            <span class="ex" onclick="setEx('قارن بين ارامكو وسابك')">⚖️ مقارنة</span>
        </div>
        <textarea id="msg" rows="3" placeholder="مثال: كم سعر ارامكو؟ أو حلل لي سهم 1120"></textarea>
        <div style="margin-top:10px"><button onclick="send()">إرسال للبوت ⚡</button></div>
        <div id="answer">الإجابة ستظهر هنا...</div>
    </div>

    <div class="card" style="font-size:12px">
        <b>Endpoints جديدة:</b> <code>/stock/2222</code> , <code>/stock/1120</code> , <code>/stock/AAPL</code> , <code>/stocks?symbols=2222,1120,2010</code>
    </div>

    </div>
    <script>
        const quick = ["2222","1120","2010","7010","1180","AAPL","TSLA"];
        async function loadAll(){{
            const grid=document.getElementById('stocks'); grid.innerHTML='⏳ جاري التحميل...';
            try{{
                const res=await fetch('/stocks?symbols='+quick.join(',')); const data=await res.json();
                grid.innerHTML='';
                data.forEach(s=>{{
                    if(s.error) return;
                    const cls=s.change>=0?'up':'down'; const arrow=s.change>=0?'▲':'▼';
                    grid.innerHTML+=`<div class="stock-card" onclick="document.getElementById('sym').value='${{s.symbol}}';fetchOne()">
                        <div style="font-size:12px;color:#666">${{s.name}}</div>
                        <div style="font-weight:bold">${{s.symbol}}</div>
                        <div class="price">${{s.price}} <small style="font-size:11px">${{s.currency}}</small></div>
                        <div class="${{cls}}">${{arrow}} ${{s.change}} (${{s.change_pct}}%)</div>
                    </div>`;
                }});
            }}catch(e){{grid.innerHTML='❌ '+e.message;}}
        }}
        async function fetchOne(){{
            const sym=document.getElementById('sym').value.trim(); if(!sym) return;
            const ans=document.getElementById('answer'); ans.innerText='⏳ جلب '+sym+'...';
            try{{
                const res=await fetch('/stock/'+encodeURIComponent(sym)); const data=await res.json();
                if(data.error) ans.innerText='❌ '+data.error;
                else ans.innerText=`📈 ${{data.name}} (${{data.symbol}})
السعر: ${{data.price}} ${{data.currency}}
التغيير: ${{data.change}} (${{data.change_pct}}%)
الإغلاق السابق: ${{data.prev_close}}
السوق: ${{data.market}}
الوقت: ${{data.time}}`;
            }}catch(e){{ans.innerText='❌ '+e.message;}}
        }}
        function setEx(t){{document.getElementById('msg').value=t;}}
        async function send(){{
            const msg=document.getElementById('msg').value.trim(); if(!msg) return;
            const ans=document.getElementById('answer'); ans.innerText='⚡ البوت يحلل...';
            try{{
                const res=await fetch('/chat',{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:msg}})}});
                const data=await res.json(); ans.innerText=data.reply;
            }}catch(e){{ans.innerText='❌ '+e.message;}}
        }}
        loadAll();
    </script></body></html>
    """

@app.get("/health")
def health():
    return {"status": "ok", "version": "4.0-stocks", "groq": bool(client), "model": model_name, "stocks": "live"}

# ========== Endpoints الأسهم ==========
@app.get("/stock/{symbol}")
def stock_one(symbol: str):
    return get_stock_price(symbol)

@app.get("/stocks")
def stocks_many(symbols: str = Query(..., description="مثال: 2222,1120,AAPL")):
    syms = [s.strip() for s in symbols.split(",") if s.strip()][:10]
    results = [get_stock_price(s) for s in syms]
    return results

# ========== Chat مع دمج الأسهم ==========
@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "❌ GROQ_API_KEY غير موجود"}
    
    # 1. هل الرسالة فيها أسهم؟ جيب أسعارها أولاً
    detected = detect_stock_symbols(req.message)
    stock_context = ""
    if detected:
        stock_data = []
        for sym in detected:
            data = get_stock_price(sym)
            if "error" not in data:
                stock_data.append(data)
        
        if stock_data:
            stock_context = "\n\n[بيانات أسهم لحظية من Yahoo Finance]:\n"
            for d in stock_data:
                stock_context += f"- {d['name']} ({d['symbol']}): {d['price']} {d['currency']} | التغيير: {d['change']} ({d['change_pct']}%) | إغلاق سابق: {d['prev_close']} | وقت: {d['time']}\n"
            stock_context += "\nاستخدم هذه البيانات في تحليلك. إذا سأل عن سعر، اذكر السعر الحالي والتغيير. إذا طلب تحليل، حلل بناءً على هذه الأرقام مع تنبيه أن هذا ليس نصيحة استثمارية.\n"
    
    # 2. أرسل للـ LLM مع بيانات الأسهم
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + stock_context},
            {"role": "user", "content": req.message}
        ]
        res = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.6,
            max_tokens=3500
        )
        reply = res.choices[0].message.content
        
        # إذا فيه بيانات أسهم، أضفها في نهاية الرد بشكل منسق
        if stock_context and "error" not in stock_context:
            # لا نكرر إذا البوت ذكرها
            pass
        
        return {"reply": reply, "stocks_detected": detected}
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
