"""
AI Agents Bot - V5.0 Deep Analysis - تحليل عميق للأسهم اللحظية
الميزات:
- أسعار لحظية + تاريخ 3 شهور
- مؤشرات فنية: RSI, SMA20/50, Bollinger, Support/Resistance
- تحليل عميق بالذكاء الاصطناعي
- تقرير احترافي عربي
"""
import os
import re
import math
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V5 Deep Stocks", version="5.0")

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
        print(f"✅ Groq Deep - Models: {WORKING_MODELS}")
    except Exception as e:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
            print("✅ Groq via OpenAI")
        except Exception as e2:
            print(f"❌ {e2}")
            client = None

SAUDI_SYMBOLS = {
    "ارامكو": "2222.SR", "أرامكو": "2222.SR", "ARAMCO": "2222.SR", "2222": "2222.SR",
    "الراجحي": "1120.SR", "راجحي": "1120.SR", "1120": "1120.SR",
    "سابك": "2010.SR", "2010": "2010.SR",
    "STC": "7010.SR", "الاتصالات": "7010.SR", "7010": "7010.SR",
    "الاهلي": "1180.SR", "SNB": "1180.SR", "1180": "1180.SR",
    "الانماء": "1150.SR", "1150": "1150.SR",
    "لوسيد": "LCID", "تسلا": "TSLA", "ابل": "AAPL", "نيفيديا": "NVDA",
}

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT_DEEP = """
أنت محلل أسهم سعودي محترف - CFA + خبرة 15 سنة في تداول.

عندما أعطيك بيانات سهم لحظية + مؤشرات فنية، قم بتحليل عميق بالعربية بلهجة سعودية خفيفة واحترافية:

هيكل التحليل المطلوب:
📊 **1. نظرة عامة لحظية**
- السعر الحالي والتغيير ومعناه
- السيولة والحجم

📈 **2. التحليل الفني العميق**
- المتوسطات: SMA20 vs SMA50 (هل تقاطع إيجابي/سلبي؟)
- RSI: هل تشبع شرائي >70 أو بيعي <30؟ وما معناه
- الدعوم والمقاومات القريبة (من البيانات)
- Bollinger Bands: هل السعر قريب من العلوي/السفلي؟
- الاتجاه العام: صاعد/هابط/عرضي

📅 **3. الأداء الزمني**
- أداء أسبوع/شهر/3 شهور - هل هناك زخم؟
- أعلى وأدنى سعر في الفترة

⚠️ **4. المخاطر والفرص**
- 3 فرص محتملة
- 3 مخاطر يجب مراقبتها

💡 **5. الخلاصة والتوصية العامة** (ليست نصيحة استثمارية)
- ملخص 3 أسطر
- مستويات مهمة للمراقبة

مهم:
- استخدم الأرقام التي أعطيك إياها فقط، لا تخترع
- اذكر أن هذا تحليل توعوي وليس نصيحة شراء/بيع
- كن مختصر لكن عميق - مناسب للواتساب
- إذا السهم سعودي، اذكر أنه في تداول
"""

def calc_rsi(prices, period=14):
    """حساب RSI"""
    if len(prices) < period+1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d>0 else 0 for d in deltas]
    losses = [-d if d<0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain*(period-1) + gains[i]) / period
        avg_loss = (avg_loss*(period-1) + losses[i]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1+rs))
    return round(rsi, 2)

def calc_sma(prices, period):
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)

def get_stock_deep(symbol: str) -> Dict:
    """يجيب تحليل عميق: لحظي + تاريخي + مؤشرات"""
    symbol = symbol.strip().upper()
    if symbol in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[symbol]
    if symbol.isdigit() and len(symbol) == 4:
        symbol = f"{symbol}.SR"
    
    try:
        # نجيب 3 شهور يومي + سنة للأداء
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # بيانات 3 شهور
        params_3m = {"interval": "1d", "range": "3mo"}
        r = requests.get(url, headers=headers, params=params_3m, timeout=10)
        data = r.json()
        if "chart" not in data or data["chart"]["error"]:
            return {"error": f"الرمز {symbol} غير موجود", "symbol": symbol}
        
        result = data["chart"]["result"][0]
        meta = result["meta"]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]
        highs = result["indicators"]["quote"][0]["high"]
        lows = result["indicators"]["quote"][0]["low"]
        
        # تنظيف البيانات (إزالة None)
        valid_data = [(c, v, h, l) for c, v, h, l in zip(closes, volumes, highs, lows) if c is not None]
        if not valid_data:
            return {"error": "لا توجد بيانات", "symbol": symbol}
        
        closes_clean = [x[0] for x in valid_data]
        volumes_clean = [x[1] or 0 for x in valid_data]
        highs_clean = [x[2] or 0 for x in valid_data]
        lows_clean = [x[3] or 0 for x in valid_data]
        
        price = closes_clean[-1]
        prev_close = meta.get("previousClose") or (closes_clean[-2] if len(closes_clean)>=2 else price)
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        
        # مؤشرات فنية
        sma20 = calc_sma(closes_clean, 20)
        sma50 = calc_sma(closes_clean, 50)
        rsi = calc_rsi(closes_clean, 14)
        
        # Bollinger Bands (20, 2)
        bb_upper = bb_lower = None
        if len(closes_clean) >= 20:
            sma20_bb = sum(closes_clean[-20:]) / 20
            std = math.sqrt(sum((x - sma20_bb)**2 for x in closes_clean[-20:]) / 20)
            bb_upper = round(sma20_bb + 2*std, 2)
            bb_lower = round(sma20_bb - 2*std, 2)
        
        # دعوم ومقاومات (أعلى/أدنى 20 يوم)
        recent_high = round(max(highs_clean[-20:]), 2) if len(highs_clean)>=20 else round(max(highs_clean), 2)
        recent_low = round(min(lows_clean[-20:]), 2) if len(lows_clean)>=20 else round(min(lows_clean), 2)
        
        # أداء زمني
        perf_1w = round((closes_clean[-1] / closes_clean[-5] - 1)*100, 2) if len(closes_clean)>=5 else None
        perf_1m = round((closes_clean[-1] / closes_clean[-20] - 1)*100, 2) if len(closes_clean)>=20 else None
        perf_3m = round((closes_clean[-1] / closes_clean[0] - 1)*100, 2) if len(closes_clean)>=1 else None
        
        # حجم
        avg_vol_20 = round(sum(volumes_clean[-20:]) / 20) if len(volumes_clean)>=20 else None
        last_vol = volumes_clean[-1]
        vol_ratio = round(last_vol / avg_vol_20, 2) if avg_vol_20 else None
        
        # أعلى/أدنى 3 شهور
        high_3m = round(max(closes_clean), 2)
        low_3m = round(min(closes_clean), 2)
        
        return {
            "symbol": symbol,
            "name": meta.get("longName") or meta.get("shortName") or symbol,
            "price": round(float(price), 2),
            "prev_close": round(float(prev_close), 2) if prev_close else None,
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "currency": meta.get("currency", "SAR"),
            "market": meta.get("exchangeName", ""),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_saudi": ".SR" in symbol,
            "technical": {
                "sma20": sma20,
                "sma50": sma50,
                "rsi14": rsi,
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "recent_high_20d": recent_high,
                "recent_low_20d": recent_low,
                "high_3m": high_3m,
                "low_3m": low_3m,
                "perf_1w": perf_1w,
                "perf_1m": perf_1m,
                "perf_3m": perf_3m,
                "avg_vol_20": avg_vol_20,
                "last_vol": last_vol,
                "vol_ratio": vol_ratio,
                "closes_last_20": closes_clean[-20:],  # للرسم لاحقاً
            }
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
    for m in re.findall(r'\$([A-Z]{1,5})\b', text_upper):
        found.append(m)
    keywords = ["سهم", "حللي", "تحليل", "سعر", "تداول", "ارامكو", "الراجحي", "سابك"]
    if any(k in text for k in keywords):
        if not found:
            found.append("2222")
    return list(set(found))[:2]

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Groq" if client else "❌"
    wa_status = "✅" if WHATSAPP_TOKEN else "⚠️"
    html = """
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>V5 Deep Analysis</title>
    <style>
        body{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%);min-height:100vh;padding:20px;margin:0;color:#fff}
        .container{max-width:1100px;margin:auto}
        .card{background:white;color:#222;padding:22px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.3);margin-bottom:18px}
        .badge{padding:5px 11px;border-radius:20px;font-size:12px;background:#e0f7ff;margin:3px;display:inline-block}
        .badge-green{background:#d4edda} .badge-blue{background:#cce5ff} .badge-orange{background:#fff3cd} .badge-purple{background:#e8daff}
        .stock-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:12px 0}
        .stock-card{background:#f8f9ff;border:1px solid #d0e0ff;border-radius:14px;padding:14px;text-align:center;cursor:pointer;transition:0.2s}
        .stock-card:hover{transform:translateY(-3px);box-shadow:0 6px 16px rgba(0,0,0,0.15)}
        .price{font-size:22px;font-weight:bold} .up{color:#28a745} .down{color:#dc3545}
        textarea{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:14px;box-sizing:border-box}
        button{background:#302b63;color:white;padding:11px 22px;border:none;border-radius:10px;cursor:pointer;font-weight:bold;margin:3px}
        #answer{background:#f8fbff;padding:18px;border-radius:12px;margin-top:12px;white-space:pre-wrap;line-height:1.8;border:1px solid #d0e0ff;min-height:80px;color:#222;font-size:14px}
        .ex{background:#eef6ff;padding:7px 13px;border-radius:15px;font-size:11px;cursor:pointer;margin:3px;display:inline-block;border:1px solid #d0e0ff}
        input{padding:10px;border:1px solid #ddd;border-radius:8px;width:140px}
        .metric{font-size:11px;background:#f0f0f0;padding:3px 7px;border-radius:10px;margin:2px;display:inline-block}
    </style></head><body><div class="container">
    <div class="card">
        <h2>🔬 V5.0 تحليل عميق للأسهم اللحظية</h2>
        <div><span class="badge badge-green">__STATUS__</span><span class="badge">WhatsApp: __WA__</span><span class="badge badge-blue">Deep Analysis Live</span><span class="badge badge-purple">RSI + SMA + Bollinger</span><span class="badge badge-orange">__MODEL__</span></div>
        <div style="background:#f3f0ff;padding:10px;border-radius:10px;margin:10px 0;font-size:12px">
        <b>كيف يعمل؟</b> يجيب السعر اللحظي + 3 شهور تاريخ + يحسب RSI14, SMA20/50, Bollinger Bands, دعوم/مقاومات، أداء أسبوع/شهر/3شهور، ثم Groq يحلل بعمق.
        </div>
        <h4 style="margin:12px 0 8px">⚡ أسهم جاهزة للتحليل العميق:</h4>
        <div class="stock-grid" id="stocks"></div>
        <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <input id="sym" placeholder="2222 أو AAPL" value="2222">
            <button onclick="fetchDeep()">تحليل عميق 🔬</button>
            <button onclick="fetchPrice()" style="background:#eee;color:#222">سعر سريع</button>
            <button onclick="loadAll()" style="background:#eee;color:#222">تحديث الكل</button>
        </div>
    </div>
    <div class="card">
        <h4>💬 اسأل عن أي سهم بتحليل عميق</h4>
        <div style="margin:8px 0">
            <span class="ex" onclick="setEx('حلل لي سهم ارامكو 2222 تحليل عميق')">🔬 ارامكو عميق</span>
            <span class="ex" onclick="setEx('تحليل فني شامل للراجحي 1120 مع دعوم ومقاومات')">📈 الراجحي فني</span>
            <span class="ex" onclick="setEx('هل سهم سابك 2010 مناسب للشراء الآن؟ حلل RSI والمتوسطات')">⚖️ سابك RSI</span>
            <span class="ex" onclick="setEx('قارن تحليل ارامكو وسابك من ناحية فنية')">🔍 مقارنة عميقة</span>
        </div>
        <textarea id="msg" rows="3" placeholder="مثال: حلل لي ارامكو 2222 تحليل عميق شامل"></textarea>
        <div style="margin-top:10px"><button onclick="send()">تحليل عميق ⚡</button></div>
        <div id="answer">التحليل العميق سيظهر هنا...

مثال: يجيب السعر اللحظي + RSI + SMA20/50 + Bollinger + أداء 3 شهور + حجم التداول + تحليل AI

Endpoints:
- /analyze/2222 → تحليل عميق كامل
- /stock/2222 → سعر سريع
- /stocks?symbols=2222,1120,2010
</div>
    </div>
    </div>
    <script>
        const quick = ["2222","1120","2010","7010","1180","1150","AAPL","TSLA"];
        async function loadAll(){
            const grid=document.getElementById('stocks'); grid.innerHTML='⏳...';
            try{
                const res=await fetch('/stocks?symbols='+quick.join(',')); const data=await res.json();
                grid.innerHTML='';
                data.forEach(s=>{
                    if(s.error) return;
                    const cls=s.change>=0?'up':'down'; const arrow=s.change>=0?'▲':'▼';
                    grid.innerHTML+=`<div class="stock-card" onclick="document.getElementById('sym').value='${s.symbol}';fetchDeep()"><div style="font-size:11px;color:#666">${s.name}</div><div style="font-weight:bold">${s.symbol}</div><div class="price">${s.price} ${s.currency}</div><div class="${cls}">${arrow} ${s.change} (${s.change_pct}%)</div></div>`;
                });
            }catch(e){grid.innerHTML='❌ '+e.message;}
        }
        async function fetchPrice(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return;
            const ans=document.getElementById('answer'); ans.innerText='⏳ جلب سعر '+sym+'...';
            try{
                const res=await fetch('/stock/'+encodeURIComponent(sym)); const data=await res.json();
                if(data.error) ans.innerText='❌ '+data.error;
                else ans.innerText=`📈 ${data.name} (${data.symbol})\\nالسعر: ${data.price} ${data.currency}\\nالتغيير: ${data.change} (${data.change_pct}%)\\nالوقت: ${data.time}`;
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        async function fetchDeep(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return;
            const ans=document.getElementById('answer'); ans.innerText='🔬 جاري التحليل العميق لـ '+sym+'...\\n\\n(يجيب 3 شهور + يحسب RSI/SMA/Bollinger + يحلل بـ AI)';
            try{
                const res=await fetch('/analyze/'+encodeURIComponent(sym)); const data=await res.json();
                if(data.error) ans.innerText='❌ '+data.error;
                else ans.innerText=data.deep_analysis + "\\n\\n---\\n📊 البيانات الفنية:\\n" + JSON.stringify(data.technical, null, 2);
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        function setEx(t){document.getElementById('msg').value=t;}
        async function send(){
            const msg=document.getElementById('msg').value.trim(); if(!msg) return;
            const ans=document.getElementById('answer'); ans.innerText='🔬 يحلل بعمق... (يجيب أسعار لحظية + مؤشرات فنية + تحليل AI)';
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
    return {"status": "ok", "version": "5.0-deep", "models": WORKING_MODELS, "features": ["realtime", "RSI", "SMA", "Bollinger", "deep-analysis"]}

@app.get("/stock/{symbol}")
def stock_one(symbol: str):
    data = get_stock_deep(symbol)
    if "error" in data:
        return data
    # نسخة مختصرة للسعر السريع
    return {
        "symbol": data["symbol"],
        "name": data["name"],
        "price": data["price"],
        "change": data["change"],
        "change_pct": data["change_pct"],
        "currency": data["currency"],
        "time": data["time"],
    }

@app.get("/stocks")
def stocks_many(symbols: str = Query(...)):
    syms = [s.strip() for s in symbols.split(",") if s.strip()][:8]
    results = []
    for s in syms:
        d = get_stock_deep(s)
        if "error" not in d:
            results.append({
                "symbol": d["symbol"],
                "name": d["name"],
                "price": d["price"],
                "change": d["change"],
                "change_pct": d["change_pct"],
                "currency": d["currency"],
            })
        else:
            results.append(d)
    return results

@app.get("/analyze/{symbol}")
def analyze_deep(symbol: str):
    """تحليل عميق كامل + AI"""
    deep = get_stock_deep(symbol)
    if "error" in deep:
        return deep
    
    # بناء سياق للـ AI
    tech = deep["technical"]
    context = f"""
بيانات سهم {deep['name']} ({deep['symbol']}) اللحظية:
- السعر الحالي: {deep['price']} {deep['currency']} (التغيير: {deep['change']} {deep['change_pct']}%)
- الإغلاق السابق: {deep['prev_close']}
- السوق: {deep['market']} | الوقت: {deep['time']}

المؤشرات الفنية (3 شهور):
- SMA20: {tech['sma20']} | SMA50: {tech['sma50']} | تقاطع: {'إيجابي (20 فوق 50)' if tech['sma20'] and tech['sma50'] and tech['sma20']>tech['sma50'] else 'سلبي أو غير متوفر'}
- RSI14: {tech['rsi14']} (تشبع شرائي >70، بيعي <30)
- Bollinger: العلوي {tech['bb_upper']} - السفلي {tech['bb_lower']} - السعر الحالي {deep['price']}
- دعوم/مقاومات 20 يوم: مقاومة {tech['recent_high_20d']} - دعم {tech['recent_low_20d']}
- أعلى/أدنى 3 شهور: {tech['high_3m']} / {tech['low_3m']}
- الأداء: أسبوع {tech['perf_1w']}% | شهر {tech['perf_1m']}% | 3 شهور {tech['perf_3m']}%
- الحجم: آخر حجم {tech['last_vol']} | متوسط 20 يوم {tech['avg_vol_20']} | نسبة الحجم {tech['vol_ratio']}x

حلل هذا السهم بعمق حسب الهيكل المطلوب.
"""
    
    # طلب التحليل من Groq
    if not client:
        return {"error": "No GROQ_API_KEY", "technical": tech, "raw": deep}
    
    last_error = None
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_DEEP},
                    {"role": "user", "content": context}
                ],
                temperature=0.5,
                max_tokens=4000
            )
            deep_analysis = res.choices[0].message.content
            return {
                "symbol": deep["symbol"],
                "name": deep["name"],
                "price": deep["price"],
                "change_pct": deep["change_pct"],
                "technical": tech,
                "deep_analysis": deep_analysis,
                "model_used": current_model,
                "time": deep["time"]
            }
        except Exception as e:
            last_error = str(e)
            if any(x in last_error.lower() for x in ["model", "decommissioned", "not_found", "404"]):
                continue
            else:
                break
    
    return {"error": f"فشل التحليل: {last_error}", "technical": tech, "raw": deep}

@app.get("/models")
def list_models():
    if not client:
        return {"error": "No key"}
    try:
        models = client.models.list()
        return {"available": [m.id for m in models.data], "trying": WORKING_MODELS}
    except Exception as e:
        return {"error": str(e), "trying": WORKING_MODELS}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "❌ GROQ_API_KEY غير موجود"}
    
    # هل يطلب تحليل عميق؟
    is_deep = any(k in req.message for k in ["عميق", "تحليل فني", "RSI", "شامل", "مفصل"])
    detected = detect_stock_symbols(req.message)
    
    if detected and is_deep:
        # تحليل عميق ل أول سهم
        deep_result = analyze_deep(detected[0])
        if "deep_analysis" in deep_result:
            return {"reply": deep_result["deep_analysis"], "model_used": deep_result.get("model_used"), "technical": deep_result.get("technical")}
    
    # تحليل عادي مع أسعار لحظية
    stock_context = ""
    if detected:
        stock_data = []
        for sym in detected:
            data = get_stock_deep(sym)
            if "error" not in data:
                stock_data.append(data)
        if stock_data:
            stock_context = "\n\n[بيانات لحظية + فنية]:\n"
            for d in stock_data:
                t = d["technical"]
                stock_context += f"- {d['name']} ({d['symbol']}): {d['price']} {d['currency']} ({d['change_pct']}%) | RSI {t['rsi14']} | SMA20 {t['sma20']} SMA50 {t['sma50']} | دعم {t['recent_low_20d']} مقاومة {t['recent_high_20d']} | أداء شهر {t['perf_1m']}% | 3شهور {t['perf_3m']}%\n"
    
    last_error = None
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_DEEP + stock_context},
                    {"role": "user", "content": req.message}
                ],
                temperature=0.6,
                max_tokens=3500
            )
            return {"reply": res.choices[0].message.content, "model_used": current_model}
        except Exception as e:
            last_error = str(e)
            if "model" in last_error.lower() or "404" in last_error:
                continue
            break
    
    return {"reply": f"❌ فشل: {last_error}"}

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
