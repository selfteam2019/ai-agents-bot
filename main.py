
"""
AI Agents Bot - V8.0 Universal Stock Analyzer
جاهز لتحليل أي سهم بمجرد إعطاء الاسم (عربي/انجليزي/رقم)
- يبحث عن الرمز تلقائياً
- أسعار لحظية + مؤشرات فنية + رسم بياني + TradingView + تحليل عميق
"""
import os
import re
import math
import io
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V8 Universal Stocks", version="8.0")

GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")
BASE_URL = os.getenv("BASE_URL", "") or os.getenv("RENDER_EXTERNAL_URL", "")

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
        print(f"✅ V8 Universal - Models: {WORKING_MODELS}")
    except Exception as e:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
            print("✅ Groq via OpenAI")
        except Exception as e2:
            print(f"❌ Groq failed: {e2}")
            client = None

SAUDI_SYMBOLS = {
    "ارامكو": "2222.SR", "أرامكو": "2222.SR", "ARAMCO": "2222.SR", "2222": "2222.SR",
    "بترورابغ": "2380.SR", "2380": "2380.SR",
    "الراجحي": "1120.SR", "راجحي": "1120.SR", "1120": "1120.SR",
    "الاهلي": "1180.SR", "SNB": "1180.SR", "1180": "1180.SR", "البنك الاهلي": "1180.SR",
    "الانماء": "1150.SR", "1150": "1150.SR", "مصرف الانماء": "1150.SR",
    "الرياض": "1010.SR", "1010": "1010.SR", "بنك الرياض": "1010.SR",
    "الجزيرة": "1020.SR", "1020": "1020.SR",
    "البلاد": "1140.SR", "1140": "1140.SR", "بنك البلاد": "1140.SR",
    "الفرنسي": "1050.SR", "1050": "1050.SR",
    "ساب": "1060.SR", "1060": "1060.SR",
    "العربي": "1080.SR", "1080": "1080.SR",
    "سابك": "2010.SR", "2010": "2010.SR",
    "سابك للمغذيات": "2020.SR", "2020": "2020.SR",
    "ينساب": "2290.SR", "2290": "2290.SR",
    "كيان": "2350.SR", "2350": "2350.SR",
    "STC": "7010.SR", "الاتصالات": "7010.SR", "7010": "7010.SR", "اس تي سي": "7010.SR",
    "زين": "7030.SR", "7030": "7030.SR",
    "موبايلي": "7020.SR", "7020": "7020.SR",
    "لومي": "7203.SR", "7203": "7203.SR",
    "لوسيد": "LCID", "تسلا": "TSLA", "ابل": "AAPL", "نيفيديا": "NVDA", "مايكروسوفت": "MSFT",
    "امازون": "AMZN", "جوجل": "GOOGL", "ميتا": "META", "نتفلكس": "NFLX",
}

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT_DEEP = """
أنت محلل أسهم سعودي محترف CFA - متخصص في تداول.
عندما أعطيك بيانات سهم (لحظية + فنية)، حلل بعمق بالعربية بلهجة سعودية خفيفة:
الهيكل:
📊 نظرة لحظية: السعر والتغيير والسيولة
📈 فني عميق: SMA20/50 تقاطع، RSI تشبع، Bollinger، دعوم/مقاومات
📅 أداء: أسبوع/شهر/3شهور + أعلى/أدنى
⚠️ فرص ومخاطر (3 لكل)
💡 خلاصة + مستويات مراقبة
مهم: استخدم الأرقام المعطاة فقط، اذكر أنه توعوي ليس نصيحة، مختصر لكن عميق.
"""

def calc_rsi(prices, period=14):
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
    return round(100 - (100/(1+rs)), 2)

def get_tradingview_link(symbol: str) -> str:
    sym = symbol.strip().upper()
    if sym in SAUDI_SYMBOLS:
        sym = SAUDI_SYMBOLS[sym]
    if sym.isdigit():
        sym = f"{sym}.SR"
    if ".SR" in sym:
        code = sym.replace(".SR","")
        return f"https://www.tradingview.com/symbols/TADAWUL-{code}/"
    else:
        return f"https://www.tradingview.com/symbols/{sym}/"

def search_yahoo_symbol(query: str) -> Optional[str]:
    try:
        query = query.strip()
        if query.isdigit() and len(query)==4:
            return f"{query}.SR"
        if query in SAUDI_SYMBOLS:
            return SAUDI_SYMBOLS[query]
        if query.upper() in SAUDI_SYMBOLS:
            return SAUDI_SYMBOLS[query.upper()]
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": 5, "newsCount": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, params=params, timeout=8)
        data = r.json()
        quotes = data.get("quotes", [])
        if not quotes:
            return None
        is_arabic = any('\u0600' <= c <= '\u06FF' for c in query)
        for q in quotes:
            sym = q.get("symbol","")
            if is_arabic and ".SR" in sym:
                return sym
        for q in quotes:
            sym = q.get("symbol","")
            if sym and "=" not in sym or ".SR" in sym:
                return sym
        if quotes:
            return quotes[0].get("symbol")
        return None
    except Exception as e:
        print(f"Search error for {query}: {e}")
        return None

def get_stock_deep(symbol_or_name: str) -> Dict:
    original_input = symbol_or_name.strip()
    symbol = None
    if original_input in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[original_input]
    elif original_input.upper() in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[original_input.upper()]
    elif original_input.isdigit() and len(original_input)==4:
        symbol = f"{original_input}.SR"
    elif re.match(r'^[A-Z]{1,5}$', original_input.upper()) or ".SR" in original_input.upper():
        symbol = original_input.upper()
    else:
        print(f"🔍 Searching for symbol: {original_input}")
        symbol = search_yahoo_symbol(original_input)
        if not symbol:
            if any('\u0600' <= c <= '\u06FF' for c in original_input):
                symbol = search_yahoo_symbol(original_input + " تداول")
            if not symbol:
                return {"error": f"ما لقيت رمز للسهم '{original_input}'. جرب رقم السهم (مثل 2222) أو الرمز الإنجليزي (مثل AAPL)", "input": original_input}
    print(f"✅ Resolved '{original_input}' -> '{symbol}'")
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"interval": "1d", "range": "3mo"}
        r = requests.get(url, headers=headers, params=params, timeout=12)
        data = r.json()
        if "chart" not in data or data["chart"]["error"]:
            err = data.get("chart",{}).get("error",{})
            return {"error": f"الرمز {symbol} غير موجود ({err.get('description','')})", "symbol": symbol, "input": original_input}
        result = data["chart"]["result"][0]
        meta = result["meta"]
        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]
        highs = result["indicators"]["quote"][0]["high"]
        lows = result["indicators"]["quote"][0]["low"]
        timestamps = result["timestamp"]
        valid = [(c, v, h, l, ts) for c, v, h, l, ts in zip(closes, volumes, highs, lows, timestamps) if c is not None]
        if not valid:
            return {"error": "لا توجد بيانات", "symbol": symbol, "input": original_input}
        closes_clean = [x[0] for x in valid]
        volumes_clean = [x[1] or 0 for x in valid]
        highs_clean = [x[2] or 0 for x in valid]
        lows_clean = [x[3] or 0 for x in valid]
        ts_clean = [x[4] for x in valid]
        price = closes_clean[-1]
        prev_close = meta.get("previousClose") or closes_clean[-2]
        change = price - prev_close
        change_pct = (change/prev_close*100) if prev_close else 0
        sma20_list = []
        bb_upper_list = []
        bb_lower_list = []
        for i in range(len(closes_clean)):
            if i+1 >= 20:
                window = closes_clean[i+1-20:i+1]
                sma = sum(window)/20
                sma20_list.append(sma)
                std = math.sqrt(sum((x-sma)**2 for x in window)/20)
                bb_upper_list.append(sma + 2*std)
                bb_lower_list.append(sma - 2*std)
            else:
                sma20_list.append(None)
                bb_upper_list.append(None)
                bb_lower_list.append(None)
        sma20 = round(sma20_list[-1],2) if sma20_list[-1] else None
        sma50 = round(sum(closes_clean[-50:])/50,2) if len(closes_clean)>=50 else None
        rsi = calc_rsi(closes_clean, 14)
        recent_high = round(max(highs_clean[-20:]),2) if len(highs_clean)>=20 else round(max(highs_clean),2))
        recent_low = round(min(lows_clean[-20:]),2) if len(lows_clean)>=20 else round(min(lows_clean),2))
        high_3m = round(max(closes_clean),2)
        low_3m = round(min(closes_clean),2)
        perf_1w = round((closes_clean[-1]/closes_clean[-5]-1)*100,2) if len(closes_clean)>=5 else None
        perf_1m = round((closes_clean[-1]/closes_clean[-20]-1)*100,2) if len(closes_clean)>=20 else None
        perf_3m = round((closes_clean[-1]/closes_clean[0]-1)*100,2)
        avg_vol = round(sum(volumes_clean[-20:])/20) if len(volumes_clean)>=20 else None
        vol_ratio = round(volumes_clean[-1]/avg_vol,2) if avg_vol else None
        return {
            "input": original_input,
            "symbol": symbol,
            "name": meta.get("longName") or meta.get("shortName") or symbol,
            "price": round(float(price),2),
            "prev_close": round(float(prev_close),2) if prev_close else None,
            "change": round(float(change),2),
            "change_pct": round(float(change_pct),2),
            "currency": meta.get("currency","SAR"),
            "market": meta.get("exchangeName",""),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tradingview": get_tradingview_link(symbol),
            "closes": closes_clean,
            "timestamps": ts_clean,
            "sma20_list": sma20_list,
            "bb_upper_list": bb_upper_list,
            "bb_lower_list": bb_lower_list,
            "technical": {
                "sma20": sma20,
                "sma50": sma50,
                "rsi14": rsi,
                "recent_high_20d": recent_high,
                "recent_low_20d": recent_low,
                "high_3m": high_3m,
                "low_3m": low_3m,
                "perf_1w": perf_1w,
                "perf_1m": perf_1m,
                "perf_3m": perf_3m,
                "avg_vol_20": avg_vol,
                "last_vol": volumes_clean[-1],
                "vol_ratio": vol_ratio,
            }
        }
    except Exception as e:
        print(f"Deep error for {symbol}: {e}")
        return {"error": str(e), "symbol": symbol, "input": original_input}

def generate_chart_png(symbol_data: Dict) -> bytes:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from datetime import datetime as dt
        closes = symbol_data["closes"]
        timestamps = symbol_data["timestamps"]
        dates = [dt.fromtimestamp(ts) for ts in timestamps]
        sma20_list = symbol_data["sma20_list"]
        bb_upper = symbol_data["bb_upper_list"]
        bb_lower = symbol_data["bb_lower_list"]
        sma50_list = []
        for i in range(len(closes)):
            if i+1 >= 50:
                sma50_list.append(sum(closes[i+1-50:i+1])/50)
            else:
                sma50_list.append(None)
        plt.figure(figsize=(12,6))
        plt.plot(dates, closes, label=f"{symbol_data['symbol']} Close", color='#1f77b4', linewidth=2.2)
        sma20_dates = [d for d, v in zip(dates, sma20_list) if v is not None]
        sma20_vals = [v for v in sma20_list if v is not None]
        if sma20_vals:
            plt.plot(sma20_dates, sma20_vals, label='SMA 20', color='orange', linestyle='--', alpha=0.8)
        sma50_dates = [d for d, v in zip(dates, sma50_list) if v is not None]
        sma50_vals = [v for v in sma50_list if v is not None]
        if sma50_vals:
            plt.plot(sma50_dates, sma50_vals, label='SMA 50', color='green', linestyle='--', alpha=0.8)
        bb_dates = [d for d, u, l in zip(dates, bb_upper, bb_lower) if u is not None]
        bb_u_vals = [u for u in bb_upper if u is not None]
        bb_l_vals = [l for l in bb_lower if l is not None]
        if bb_u_vals:
            plt.plot(bb_dates, bb_u_vals, color='gray', linestyle=':', alpha=0.5, label='Bollinger')
            plt.plot(bb_dates, bb_l_vals, color='gray', linestyle=':', alpha=0.5)
            plt.fill_between(bb_dates, bb_l_vals, bb_u_vals, color='gray', alpha=0.1)
        plt.title(f"{symbol_data['name']} ({symbol_data['symbol']}) - {symbol_data['price']} {symbol_data['currency']} ({symbol_data['change_pct']}%)", fontsize=13, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel(f"Price ({symbol_data['currency']})")
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=9)
        plt.xticks(rotation=25)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        print(f"Chart error: {e}")
        return None

def get_base_url(request: Request = None) -> str:
    if BASE_URL:
        return BASE_URL.rstrip('/')
    if request:
        scheme = request.url.scheme
        host = request.headers.get('host', '')
        if host:
            return f"{scheme}://{host}"
    return os.getenv("RENDER_EXTERNAL_URL", "https://ai-agents-bot.onrender.com").rstrip('/')

def detect_stock_input(text: str) -> List[str]:
    candidates = []
    for m in re.findall(r'\b(\d{4})\b', text):
        candidates.append(m)
    for m in re.findall(r'\$?([A-Z]{1,5})\b', text.upper()):
        if len(m)>=1 and m not in ["انا","وش","كيف","هل","ماذا"]:
            candidates.append(m)
    for arabic in SAUDI_SYMBOLS.keys():
        if arabic in text:
            candidates.append(arabic)
    stripped = text.strip()
    if 2 <= len(stripped) <= 30 and not any(k in stripped for k in ["حلل","سعر","كيف","وش","اعطني","تقرير","كود"]):
        candidates.append(stripped)
    cleaned = []
    for c in candidates:
        c = c.strip()
        if c and len(c)>=2 and c not in cleaned:
            if c.lower() not in ["سهم","السهم","سعر","الاسهم","تحليل","عميق","حلل","ارسم","شارت"]:
                cleaned.append(c)
    return cleaned[:3]

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    status = "✅ Groq" if client else "❌"
    wa_status = "✅" if WHATSAPP_TOKEN else "⚠️ قبل الربط"
    base_url = get_base_url(request)
    html = """
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>V8 Universal Stocks - حلل أي سهم بالاسم</title>
    <style>
        body{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%);min-height:100vh;padding:20px;margin:0;color:#fff}
        .container{max-width:1150px;margin:auto}
        .card{background:white;color:#222;padding:22px;border-radius:20px;box-shadow:0 10px 30px rgba(0,0,0,0.3);margin-bottom:18px}
        .badge{padding:5px 11px;border-radius:20px;font-size:12px;background:#e0f7ff;margin:3px;display:inline-block}
        .badge-green{background:#d4edda} .badge-blue{background:#cce5ff} .badge-orange{background:#fff3cd} .badge-purple{background:#e8daff}
        .stock-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:12px 0}
        .stock-card{background:#f8f9ff;border:1px solid #d0e0ff;border-radius:14px;padding:14px;text-align:center;cursor:pointer;transition:0.2s}
        .stock-card:hover{transform:translateY(-3px);box-shadow:0 6px 16px rgba(0,0,0,0.15)}
        .price{font-size:22px;font-weight:bold} .up{color:#28a745} .down{color:#dc3545}
        textarea{width:100%;padding:14px;border:2px solid #e0e0e0;border-radius:12px;font-size:14px;box-sizing:border-box}
        button{background:#302b63;color:white;padding:11px 22px;border:none;border-radius:10px;cursor:pointer;font-weight:bold;margin:3px}
        #answer{background:#f8fbff;padding:18px;border-radius:12px;margin-top:12px;white-space:pre-wrap;line-height:1.8;border:1px solid #d0e0ff;min-height:80px;color:#222;font-size:14px}
        .ex{background:#eef6ff;padding:7px 13px;border-radius:15px;font-size:11px;cursor:pointer;margin:3px;display:inline-block;border:1px solid #d0e0ff}
        input{padding:12px;border:2px solid #ddd;border-radius:10px;width:200px;font-size:14px}
        .chart-box{background:#fff;border:1px solid #ddd;border-radius:12px;padding:10px;margin:10px 0;text-align:center}
        .chart-box img{max-width:100%;border-radius:8px}
        .tv-link{display:inline-block;background:#131722;color:white;padding:6px 12px;border-radius:8px;text-decoration:none;font-size:12px;margin:4px}
        .alert{background:#d4edda;padding:12px;border-radius:10px;font-size:13px;margin:10px 0;border:1px solid #a3d9a5}
        .search-box{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:12px 0}
        .hint{font-size:11px;color:#666;margin:4px 0}
    </style></head><body><div class="container">
    <div class="card">
        <h2>🔍 V8.0 محلل شامل - حلل أي سهم بالاسم</h2>
        <div class="alert">✅ جاهز لتحليل <b>أي سهم</b> بمجرد كتابة اسمه (عربي/انجليزي/رقم) - قبل ربط الواتساب. يبحث تلقائياً عن الرمز ويجيب السعر اللحظي + تحليل عميق + رسم بياني.</div>
        <div><span class="badge badge-green">__STATUS__</span><span class="badge">WhatsApp: __WA__</span><span class="badge badge-blue">Universal Search Live</span><span class="badge badge-purple">Chart + TV</span><span class="badge badge-orange">__MODEL__</span></div>
        <div class="hint">Base: __BASE_URL__</div>
        <h4 style="margin:14px 0 6px">🔎 ابحث عن أي سهم بالاسم:</h4>
        <div class="search-box">
            <input id="sym" placeholder="مثال: ارامكو أو 1120 أو AAPL أو تسلا" value="" style="width:280px">
            <button onclick="fetchDeep()">تحليل عميق 🔬</button>
            <button onclick="fetchChart()">رسم 📈</button>
            <button onclick="openTV()" style="background:#131722">TradingView ↗</button>
        </div>
        <div class="hint">جرب: ارامكو، الراجحي، سابك، STC، تسلا، ابل، نيفيديا، لوسيد، أو أي اسم شركة</div>
        <h4 style="margin:12px 0 8px">⚡ أسهم سريعة:</h4>
        <div class="stock-grid" id="stocks"></div>
        <div id="chartArea"></div>
    </div>
    <div class="card">
        <h4>💬 اسأل عن أي سهم (عربي أو انجليزي)</h4>
        <div style="margin:8px 0">
            <span class="ex" onclick="setEx('ارامكو')">ارامكو</span>
            <span class="ex" onclick="setEx('الراجحي')">الراجحي</span>
            <span class="ex" onclick="setEx('سابك')">سابك</span>
            <span class="ex" onclick="setEx('STC')">STC</span>
            <span class="ex" onclick="setEx('تسلا')">تسلا</span>
            <span class="ex" onclick="setEx('ابل')">ابل</span>
            <span class="ex" onclick="setEx('نيفيديا')">نيفيديا</span>
            <span class="ex" onclick="setEx('البنك الاهلي')">البنك الاهلي</span>
            <span class="ex" onclick="setEx('مصرف الانماء')">الانماء</span>
            <span class="ex" onclick="setEx('لوسيد')">لوسيد</span>
            <span class="ex" onclick="setEx('حلل لي سهم 1010')">بنك الرياض 1010</span>
            <span class="ex" onclick="setEx('حلل سهم مايكروسوفت')">مايكروسوفت</span>
        </div>
        <textarea id="msg" rows="3" placeholder="اكتب اسم أي سهم: ارامكو، الراجحي، 1120، AAPL، تسلا، أو حتى 'شركة الاتصالات السعودية'"></textarea>
        <div style="margin-top:10px"><button onclick="send()">حلل السهم ⚡</button></div>
        <div id="answer">اكتب اسم أي سهم فوق (مثل ارامكو، الراجحي، سابك، 1120، AAPL، تسلا) وسيتم تحليله فوراً مع رسم بياني ورابط TradingView.</div>
    </div>
    </div>
    <script>
        const quick = ["ارامكو","الراجحي","سابك","STC","الاهلي","الانماء","تسلا","ابل"];
        async function loadAll(){
            const grid=document.getElementById('stocks'); grid.innerHTML='⏳...';
            try{
                const res=await fetch('/stocks?symbols='+encodeURIComponent(quick.join(','))); const data=await res.json();
                grid.innerHTML='';
                data.forEach(s=>{
                    if(s.error) return;
                    const cls=s.change>=0?'up':'down'; const arrow=s.change>=0?'▲':'▼';
                    grid.innerHTML+=`<div class="stock-card" onclick="document.getElementById('sym').value='${s.input}';fetchDeep()"><div style="font-size:11px;color:#666">${s.name}</div><div style="font-weight:bold">${s.symbol} (${s.input})</div><div class="price">${s.price} ${s.currency}</div><div class="${cls}">${arrow} ${s.change} (${s.change_pct}%)</div><div style="margin-top:6px"><a class="tv-link" href="${s.tradingview}" target="_blank">TV</a> <a class="tv-link" style="background:#302b63" href="/chart/${encodeURIComponent(s.input)}" target="_blank">Chart</a></div></div>`;
                });
            }catch(e){grid.innerHTML='❌ '+e.message;}
        }
        async function fetchChart(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب اسم السهم أولاً');
            const area=document.getElementById('chartArea');
            area.innerHTML=`<div class="chart-box">⏳ جاري رسم ${sym}...<br><img src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" onerror="this.parentElement.innerHTML='❌ ما لقيت السهم - جرب اسم ثاني'"><br><a class="tv-link" href="/tradingview/${encodeURIComponent(sym)}" target="_blank">TradingView ↗</a></div>`;
        }
        function openTV(){const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب اسم السهم'); window.open('/tradingview/'+encodeURIComponent(sym), '_blank');}
        async function fetchDeep(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب اسم السهم');
            const ans=document.getElementById('answer'); ans.innerText='🔍 أبحث عن رمز '+sym+' وأحلله بعمق...';
            const area=document.getElementById('chartArea');
            area.innerHTML=`<div class="chart-box">📈 الرسم البياني لـ ${sym}<br><img src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" style="max-width:100%" onerror="this.style.display='none'"><br><a class="tv-link" href="/tradingview/${encodeURIComponent(sym)}" target="_blank">TradingView ↗</a></div>`;
            try{
                const res=await fetch('/analyze/'+encodeURIComponent(sym)); const data=await res.json();
                if(data.error) ans.innerText='❌ '+data.error;
                else ans.innerText=`✅ تم العثور على: ${data.name} (${data.symbol}) من بحث '${data.input}'\n\n` + data.deep_analysis + "\n\n📈 الرسم: /chart/"+encodeURIComponent(sym)+"\n🔗 TradingView: "+data.tradingview;
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        function setEx(t){document.getElementById('msg').value=t; document.getElementById('sym').value=t; fetchDeep();}
        async function send(){
            const msg=document.getElementById('msg').value.trim(); if(!msg) return;
            const ans=document.getElementById('answer'); ans.innerText='🔍 أبحث وأحلل '+msg+'...';
            try{
                const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
                const data=await res.json(); ans.innerText=data.reply;
                if(data.chart_url){document.getElementById('chartArea').innerHTML=`<div class="chart-box"><img src="${data.chart_url}?t=${Date.now()}" style="max-width:100%"><br><a class="tv-link" href="${data.tradingview}" target="_blank">TradingView ↗</a></div>`;}
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        loadAll();
    </script></body></html>
    """
    html = html.replace("__STATUS__", status).replace("__WA__", wa_status).replace("__MODEL__", model_name).replace("__BASE_URL__", base_url)
    return HTMLResponse(content=html)

@app.get("/health")
def health():
    return {"status": "ok", "version": "8.0-universal", "models": WORKING_MODELS, "feature": "analyze any stock by name"}

@app.get("/search/{query}")
def search_symbol(query: str):
    sym = search_yahoo_symbol(query)
    if sym:
        return {"input": query, "symbol": sym, "tradingview": get_tradingview_link(sym), "chart_url": f"/chart/{sym}"}
    return {"error": f"ما لقيت رمز لـ '{query}'", "input": query}

@app.get("/stock/{symbol_or_name}")
def stock_one(symbol_or_name: str):
    data = get_stock_deep(symbol_or_name)
    if "error" in data:
        return JSONResponse(data, status_code=404)
    return {
        "input": data["input"],
        "symbol": data["symbol"],
        "name": data["name"],
        "price": data["price"],
        "change": data["change"],
        "change_pct": data["change_pct"],
        "currency": data["currency"],
        "time": data["time"],
        "tradingview": data["tradingview"],
        "chart_url": f"/chart/{data['input']}",
    }

@app.get("/stocks")
def stocks_many(symbols: str = Query(..., description="أسماء مفصولة بفاصلة: ارامكو,الراجحي,AAPL")):
    inputs = [s.strip() for s in symbols.split(",") if s.strip()][:8]
    results = []
    for inp in inputs:
        d = get_stock_deep(inp)
        if "error" not in d:
            results.append({
                "input": d["input"],
                "symbol": d["symbol"],
                "name": d["name"],
                "price": d["price"],
                "change": d["change"],
                "change_pct": d["change_pct"],
                "currency": d["currency"],
                "tradingview": d["tradingview"],
            })
        else:
            results.append(d)
    return results

@app.get("/chart/{symbol_or_name}")
def chart_png(symbol_or_name: str):
    data = get_stock_deep(symbol_or_name)
    if "error" in data:
        return JSONResponse({"error": data["error"]}, status_code=404)
    img_bytes = generate_chart_png(data)
    if not img_bytes:
        return JSONResponse({"error": "فشل الرسم"}, status_code=500)
    return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png", headers={"Cache-Control": "no-cache"})

@app.get("/tradingview/{symbol_or_name}")
def tradingview_redirect(symbol_or_name: str):
    deep = get_stock_deep(symbol_or_name)
    if "error" not in deep:
        link = deep["tradingview"]
    else:
        link = get_tradingview_link(symbol_or_name)
    return RedirectResponse(url=link)

@app.get("/analyze/{symbol_or_name}")
def analyze_deep(symbol_or_name: str):
    deep = get_stock_deep(symbol_or_name)
    if "error" in deep:
        return JSONResponse(deep, status_code=404)
    tech = deep["technical"]
    context = f"""
بيانات {deep['name']} ({deep['symbol']}) من بحث '{deep['input']}':
- السعر: {deep['price']} {deep['currency']} ({deep['change']} {deep['change_pct']}%)
- SMA20 {tech['sma20']} SMA50 {tech['sma50']} | RSI {tech['rsi14']}
- دعم {tech['recent_low_20d']} مقاومة {tech['recent_high_20d']} | أعلى/أدنى 3شهور {tech['high_3m']}/{tech['low_3m']}
- أداء: أسبوع {tech['perf_1w']}% شهر {tech['perf_1m']}% 3شهور {tech['perf_3m']}% | حجم نسبة {tech['vol_ratio']}x
حلل بعمق.
"""
    if not client:
        return {"error": "No GROQ_API_KEY", "technical": tech, "tradingview": deep["tradingview"], "chart_url": f"/chart/{deep['input']}", "symbol": deep["symbol"], "name": deep["name"], "input": deep["input"]}
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_DEEP},{"role": "user", "content": context}],
                temperature=0.5,
                max_tokens=4000
            )
            return {
                "input": deep["input"],
                "symbol": deep["symbol"],
                "name": deep["name"],
                "price": deep["price"],
                "change_pct": deep["change_pct"],
                "technical": tech,
                "deep_analysis": res.choices[0].message.content,
                "tradingview": deep["tradingview"],
                "chart_url": f"/chart/{deep['input']}",
                "model_used": current_model,
            }
        except Exception as e:
            if "model" in str(e).lower() or "404" in str(e) or "400" in str(e):
                continue
            break
    return {"error": "فشل التحليل", "technical": tech}

@app.post("/chat")
def chat_endpoint(req: ChatRequest, request: Request = None):
    if not client:
        return {"reply": "❌ GROQ_API_KEY غير موجود"}
    inputs = detect_stock_input(req.message)
    is_deep = any(k in req.message for k in ["عميق","تحليل","RSI","شامل","رسم","شارت","صورة","حلل"])
    base_url = get_base_url(request)
    if inputs:
        deep_result = get_stock_deep(inputs[0])
        if "error" not in deep_result:
            if is_deep or len(req.message.strip())<20:
                analysis = analyze_deep(inputs[0])
                if "deep_analysis" in analysis:
                    reply = f"✅ وجدت السهم: {analysis['name']} ({analysis['symbol']}) من بحث '{analysis['input']}'\n\n{analysis['deep_analysis']}\n\n📈 الرسم: {base_url}/chart/{analysis['input']}\n🔗 TradingView: {analysis['tradingview']}"
                    return {
                        "reply": reply,
                        "model_used": analysis.get("model_used"),
                        "chart_url": f"{base_url}/chart/{analysis['input']}",
                        "tradingview": analysis.get("tradingview"),
                        "symbol": analysis["symbol"],
                        "input": analysis["input"]
                    }
        stock_context = ""
        chart_url = tradingview = None
        symbol_for_chart = None
        for inp in inputs:
            data = get_stock_deep(inp)
            if "error" not in data:
                t = data["technical"]
                stock_context += f"- {data['name']} ({data['symbol']}) من '{data['input']}': {data['price']} ({data['change_pct']}%) RSI {t['rsi14']} SMA20 {t['sma20']}\n"
                symbol_for_chart = data["input"]
                chart_url = f"{base_url}/chart/{data['input']}"
                tradingview = data["tradingview"]
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
                reply = res.choices[0].message.content
                if chart_url:
                    reply += f"\n\n📈 الرسم: {chart_url}\n🔗 TradingView: {tradingview}"
                return {
                    "reply": reply,
                    "model_used": current_model,
                    "chart_url": chart_url,
                    "tradingview": tradingview,
                    "symbol": symbol_for_chart,
                    "input": inputs[0] if inputs else None
                }
            except Exception as e:
                if "model" in str(e).lower() or "404" in str(e) or "400" in str(e):
                    continue
                break
        return {"reply": f"❌ فشل"}
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_DEEP},
                    {"role": "user", "content": req.message}
                ],
                temperature=0.6,
                max_tokens=3500
            )
            return {"reply": res.choices[0].message.content, "model_used": current_model}
        except Exception as e:
            if "model" in str(e).lower() or "404" in str(e):
                continue
            break
    return {"reply": "❌ فشل الاتصال"}

@app.get("/models")
def list_models():
    if not client:
        return {"error": "No key"}
    try:
        models = client.models.list()
        return {"available": [m.id for m in models.data], "trying": WORKING_MODELS}
    except Exception as e:
        return {"error": str(e), "trying": WORKING_MODELS}

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
                    if not text:
                        continue
                    reply_data = chat_endpoint(ChatRequest(message=text), request)
                    if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID:
                        url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
                        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
                        payload = {"messaging_product": "whatsapp", "to": from_number, "type": "text", "text": {"body": reply_data.get("reply","")[:3800]}}
                        requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"Webhook error: {e}")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
