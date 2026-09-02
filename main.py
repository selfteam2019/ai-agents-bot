"""
AI Agents Bot - V6.0 Charts + TradingView
- رسم بياني كصورة PNG مع SMA20/50 + Bollinger
- رابط مباشر TradingView
- تحليل عميق
"""
import os
import re
import math
import io
from datetime import datetime
from typing import List, Dict
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Agents Bot - V6 Charts", version="6.0")

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
        print(f"✅ Groq V6 Charts - Models: {WORKING_MODELS}")
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
    "الانماء": "1150.SR", "1150": "1150.SR",
    "لوسيد": "LCID", "تسلا": "TSLA", "ابل": "AAPL", "نيفيديا": "NVDA",
}

class ChatRequest(BaseModel):
    message: str

SYSTEM_PROMPT_DEEP = """
أنت محلل أسهم سعودي محترف. حلل بعمق مع بيانات فنية: SMA20/50, RSI, Bollinger, دعوم/مقاومات، أداء زمني.
أعط تحليل منظم: نظرة لحظية، تحليل فني، أداء، مخاطر/فرص، خلاصة. ليس نصيحة استثمارية. لهجة سعودية خفيفة.
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

def calc_sma(prices, period):
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)

def get_tradingview_link(symbol: str) -> str:
    """رابط TradingView"""
    sym = symbol.strip().upper()
    if sym in SAUDI_SYMBOLS:
        sym = SAUDI_SYMBOLS[sym]
    if sym.isdigit():
        sym = f"{sym}.SR"
    # سعودي
    if ".SR" in sym:
        code = sym.replace(".SR","")
        return f"https://www.tradingview.com/symbols/TADAWUL-{code}/"
    # أمريكي
    else:
        return f"https://www.tradingview.com/symbols/{sym}/"

def get_stock_deep(symbol: str) -> Dict:
    symbol = symbol.strip().upper()
    if symbol in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[symbol]
    if symbol.isdigit() and len(symbol) == 4:
        symbol = f"{symbol}.SR"
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"interval": "1d", "range": "3mo"}
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()
        if "chart" not in data or data["chart"]["error"]:
            return {"error": f"الرمز {symbol} غير موجود", "symbol": symbol}
        result = data["chart"]["result"][0]
        meta = result["meta"]
        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]
        highs = result["indicators"]["quote"][0]["high"]
        lows = result["indicators"]["quote"][0]["low"]
        timestamps = result["timestamp"]
        
        valid = [(c, v, h, l, ts) for c, v, h, l, ts in zip(closes, volumes, highs, lows, timestamps) if c is not None]
        if not valid:
            return {"error": "لا توجد بيانات", "symbol": symbol}
        
        closes_clean = [x[0] for x in valid]
        volumes_clean = [x[1] or 0 for x in valid]
        highs_clean = [x[2] or 0 for x in valid]
        lows_clean = [x[3] or 0 for x in valid]
        ts_clean = [x[4] for x in valid]
        
        price = closes_clean[-1]
        prev_close = meta.get("previousClose") or closes_clean[-2]
        change = price - prev_close
        change_pct = (change/prev_close*100) if prev_close else 0
        
        sma20 = calc_sma(closes_clean, 20)
        sma50 = calc_sma(closes_clean, 50)
        rsi = calc_rsi(closes_clean, 14)
        
        bb_upper = bb_lower = None
        sma20_list = []
        bb_upper_list = []
        bb_lower_list = []
        # حساب SMA20 لكل نقطة و Bollinger
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
        
        if len(closes_clean) >= 20:
            bb_upper = bb_upper_list[-1]
            bb_lower = bb_lower_list[-1]
        
        recent_high = round(max(highs_clean[-20:]),2) if len(highs_clean)>=20 else round(max(highs_clean),2)
        recent_low = round(min(lows_clean[-20:]),2) if len(lows_clean)>=20 else round(min(lows_clean),2)
        high_3m = round(max(closes_clean),2)
        low_3m = round(min(closes_clean),2)
        perf_1w = round((closes_clean[-1]/closes_clean[-5]-1)*100,2) if len(closes_clean)>=5 else None
        perf_1m = round((closes_clean[-1]/closes_clean[-20]-1)*100,2) if len(closes_clean)>=20 else None
        perf_3m = round((closes_clean[-1]/closes_clean[0]-1)*100,2)
        avg_vol = round(sum(volumes_clean[-20:])/20) if len(volumes_clean)>=20 else None
        vol_ratio = round(volumes_clean[-1]/avg_vol,2) if avg_vol else None
        
        return {
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
                "sma50": calc_sma(closes_clean,50),
                "rsi14": rsi,
                "bb_upper": round(bb_upper,2) if bb_upper else None,
                "bb_lower": round(bb_lower,2) if bb_lower else None,
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
        return {"error": str(e), "symbol": symbol}

def generate_chart_png(symbol_data: Dict) -> bytes:
    """يرسم الرسم البياني مع SMA و Bollinger ويرجع PNG bytes"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime as dt
        
        closes = symbol_data["closes"]
        timestamps = symbol_data["timestamps"]
        dates = [dt.fromtimestamp(ts) for ts in timestamps]
        sma20_list = symbol_data["sma20_list"]
        bb_upper = symbol_data["bb_upper_list"]
        bb_lower = symbol_data["bb_lower_list"]
        
        # SMA50
        sma50_list = []
        for i in range(len(closes)):
            if i+1 >= 50:
                sma50_list.append(sum(closes[i+1-50:i+1])/50)
            else:
                sma50_list.append(None)
        
        plt.figure(figsize=(12,6))
        plt.plot(dates, closes, label=f"{symbol_data['symbol']} Close", color='#1f77b4', linewidth=2)
        
        # SMA20
        sma20_dates = [d for d, v in zip(dates, sma20_list) if v is not None]
        sma20_vals = [v for v in sma20_list if v is not None]
        if sma20_vals:
            plt.plot(sma20_dates, sma20_vals, label='SMA 20', color='orange', linestyle='--', alpha=0.8)
        
        # SMA50
        sma50_dates = [d for d, v in zip(dates, sma50_list) if v is not None]
        sma50_vals = [v for v in sma50_list if v is not None]
        if sma50_vals:
            plt.plot(sma50_dates, sma50_vals, label='SMA 50', color='green', linestyle='--', alpha=0.8)
        
        # Bollinger
        bb_dates = [d for d, u, l in zip(dates, bb_upper, bb_lower) if u is not None]
        bb_u_vals = [u for u in bb_upper if u is not None]
        bb_l_vals = [l for l in bb_lower if l is not None]
        if bb_u_vals:
            plt.plot(bb_dates, bb_u_vals, color='gray', linestyle=':', alpha=0.5, label='Bollinger Upper/Lower')
            plt.plot(bb_dates, bb_l_vals, color='gray', linestyle=':', alpha=0.5)
            plt.fill_between(bb_dates, bb_l_vals, bb_u_vals, color='gray', alpha=0.1)
        
        plt.title(f"{symbol_data['name']} ({symbol_data['symbol']}) - {symbol_data['price']} {symbol_data['currency']} ({symbol_data['change_pct']}%)", fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel(f"Price ({symbol_data['currency']})")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.xticks(rotation=30)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        print(f"Chart error: {e}")
        return None

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
    if any(k in text for k in ["سهم","حللي","تحليل","سعر","تداول"]):
        if not found:
            found.append("2222")
    return list(set(found))[:2]

@app.get("/", response_class=HTMLResponse)
def home():
    status = "✅ Groq" if client else "❌"
    wa_status = "✅" if WHATSAPP_TOKEN else "⚠️"
    html = """
    <html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>V6 Charts + TradingView</title>
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
        input{padding:10px;border:1px solid #ddd;border-radius:8px;width:140px}
        .chart-box{background:#fff;border:1px solid #ddd;border-radius:12px;padding:10px;margin:10px 0;text-align:center}
        .chart-box img{max-width:100%;border-radius:8px}
        .tv-link{display:inline-block;background:#131722;color:white;padding:6px 12px;border-radius:8px;text-decoration:none;font-size:12px;margin:4px}
        .tv-link:hover{background:#000}
    </style></head><body><div class="container">
    <div class="card">
        <h2>📊 V6.0 رسم بياني + TradingView + تحليل عميق</h2>
        <div><span class="badge badge-green">__STATUS__</span><span class="badge">WhatsApp: __WA__</span><span class="badge badge-blue">Charts PNG Live</span><span class="badge badge-purple">TradingView Links</span><span class="badge badge-orange">__MODEL__</span></div>
        <div style="background:#f3f0ff;padding:10px;border-radius:10px;margin:10px 0;font-size:12px">
        ✨ الجديد: رسم بياني كصورة مع SMA20/50 + Bollinger + رابط مباشر لفتح السهم في TradingView للتحليل المتقدم.
        </div>
        <h4 style="margin:12px 0 8px">⚡ أسهم جاهزة:</h4>
        <div class="stock-grid" id="stocks"></div>
        <div style="margin:10px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <input id="sym" placeholder="2222 أو AAPL" value="2222">
            <button onclick="fetchDeep()">تحليل عميق 🔬</button>
            <button onclick="fetchChart()">رسم بياني 📈</button>
            <button onclick="openTV()" style="background:#131722">TradingView ↗</button>
            <button onclick="loadAll()" style="background:#eee;color:#222">تحديث</button>
        </div>
        <div id="chartArea"></div>
    </div>
    <div class="card">
        <h4>💬 اسأل البوت</h4>
        <div style="margin:8px 0">
            <span class="ex" onclick="setEx('حلل لي سهم ارامكو 2222 تحليل عميق مع رسم')">🔬 ارامكو + رسم</span>
            <span class="ex" onclick="setEx('ارسم لي شارت الراجحي 1120 مع التحليل')">📈 الراجحي شارت</span>
            <span class="ex" onclick="setEx('تحليل سابك 2010 مع رابط تريدنج فيو')">🔍 سابك TradingView</span>
        </div>
        <textarea id="msg" rows="3" placeholder="مثال: حلل ارامكو مع رسم بياني ورابط تريدنج فيو"></textarea>
        <div style="margin-top:10px"><button onclick="send()">تحليل + رسم ⚡</button></div>
        <div id="answer">التحليل سيظهر هنا...
        
Endpoints:
- /chart/2222 → صورة الرسم البياني PNG
- /analyze/2222 → تحليل عميق + AI
- /tradingview/2222 → يفتح TradingView مباشرة
- /stock/2222 → سعر سريع
</div>
    </div>
    </div>
    <script>
        const quick = ["2222","1120","2010","7010","1180","AAPL","TSLA","NVDA"];
        async function loadAll(){
            const grid=document.getElementById('stocks'); grid.innerHTML='⏳...';
            try{
                const res=await fetch('/stocks?symbols='+quick.join(',')); const data=await res.json();
                grid.innerHTML='';
                data.forEach(s=>{
                    if(s.error) return;
                    const cls=s.change>=0?'up':'down'; const arrow=s.change>=0?'▲':'▼';
                    grid.innerHTML+=`<div class="stock-card" onclick="document.getElementById('sym').value='${s.symbol}';fetchDeep()"><div style="font-size:11px;color:#666">${s.name}</div><div style="font-weight:bold">${s.symbol}</div><div class="price">${s.price} ${s.currency}</div><div class="${cls}">${arrow} ${s.change} (${s.change_pct}%)</div><div style="margin-top:6px"><a class="tv-link" href="${s.tradingview}" target="_blank">TradingView</a> <a class="tv-link" style="background:#302b63" href="/chart/${s.symbol}" target="_blank">Chart PNG</a></div></div>`;
                });
            }catch(e){grid.innerHTML='❌ '+e.message;}
        }
        async function fetchChart(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return;
            const area=document.getElementById('chartArea');
            area.innerHTML=`<div class="chart-box">⏳ جاري رسم ${sym}...<br><img id="chartImg" src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" style="margin-top:10px" onerror="this.parentElement.innerHTML='❌ فشل الرسم'"><br><a class="tv-link" href="/tradingview/${encodeURIComponent(sym)}" target="_blank">فتح في TradingView ↗</a> <a class="tv-link" style="background:#302b63" href="/chart/${encodeURIComponent(sym)}" target="_blank">فتح الصورة</a></div>`;
        }
        function openTV(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return;
            window.open('/tradingview/'+encodeURIComponent(sym), '_blank');
        }
        async function fetchDeep(){
            const sym=document.getElementById('sym').value.trim(); if(!sym) return;
            const ans=document.getElementById('answer'); 
            ans.innerText='🔬 تحليل عميق لـ '+sym+'...';
            const area=document.getElementById('chartArea');
            area.innerHTML=`<div class="chart-box">📈 الرسم البياني لـ ${sym}<br><img src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" style="max-width:100%"><br><a class="tv-link" href="/tradingview/${encodeURIComponent(sym)}" target="_blank">TradingView ↗</a></div>`;
            try{
                const res=await fetch('/analyze/'+encodeURIComponent(sym)); const data=await res.json();
                if(data.error) ans.innerText='❌ '+data.error;
                else ans.innerText=data.deep_analysis + "\\n\\n📊 رابط TradingView: " + data.tradingview + "\\n📈 رابط الصورة: /chart/" + data.symbol;
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        function setEx(t){document.getElementById('msg').value=t;}
        async function send(){
            const msg=document.getElementById('msg').value.trim(); if(!msg) return;
            const ans=document.getElementById('answer'); ans.innerText='🔬 يحلل مع رسم...';
            try{
                const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
                const data=await res.json(); 
                let txt=data.reply;
                if(data.chart_url) txt+="\\n\\n📈 الرسم: "+data.chart_url;
                if(data.tradingview) txt+="\\n🔗 TradingView: "+data.tradingview;
                ans.innerText=txt;
                if(data.chart_url){
                    document.getElementById('chartArea').innerHTML=`<div class="chart-box"><img src="${data.chart_url}?t=${Date.now()}" style="max-width:100%"><br><a class="tv-link" href="${data.tradingview}" target="_blank">TradingView ↗</a></div>`;
                }
            }catch(e){ans.innerText='❌ '+e.message;}
        }
        loadAll();
    </script></body></html>
    """
    html = html.replace("__STATUS__", status).replace("__WA__", wa_status).replace("__MODEL__", model_name)
    return HTMLResponse(content=html)

@app.get("/health")
def health():
    return {"status": "ok", "version": "6.0-charts-tv", "models": WORKING_MODELS}

@app.get("/stock/{symbol}")
def stock_one(symbol: str):
    data = get_stock_deep(symbol)
    if "error" in data:
        return data
    return {
        "symbol": data["symbol"],
        "name": data["name"],
        "price": data["price"],
        "change": data["change"],
        "change_pct": data["change_pct"],
        "currency": data["currency"],
        "time": data["time"],
        "tradingview": data["tradingview"],
        "chart_url": f"/chart/{data['symbol']}",
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
                "tradingview": d["tradingview"],
            })
        else:
            results.append(d)
    return results

@app.get("/chart/{symbol}")
def chart_png(symbol: str):
    data = get_stock_deep(symbol)
    if "error" in data:
        return JSONResponse({"error": data["error"]}, status_code=404)
    img_bytes = generate_chart_png(data)
    if not img_bytes:
        return JSONResponse({"error": "فشل الرسم"}, status_code=500)
    return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png", headers={"Cache-Control": "no-cache"})

@app.get("/tradingview/{symbol}")
def tradingview_redirect(symbol: str):
    link = get_tradingview_link(symbol)
    return RedirectResponse(url=link)

@app.get("/analyze/{symbol}")
def analyze_deep(symbol: str):
    deep = get_stock_deep(symbol)
    if "error" in deep:
        return deep
    tech = deep["technical"]
    context = f"""
بيانات {deep['name']} ({deep['symbol']}):
- السعر: {deep['price']} {deep['currency']} ({deep['change']} {deep['change_pct']}%)
- SMA20 {tech['sma20']} SMA50 {tech['sma50']} | RSI {tech['rsi14']} | Bollinger {tech['bb_upper']}/{tech['bb_lower']}
- دعم {tech['recent_low_20d']} مقاومة {tech['recent_high_20d']} | أعلى/أدنى 3شهور {tech['high_3m']}/{tech['low_3m']}
- أداء: أسبوع {tech['perf_1w']}% شهر {tech['perf_1m']}% 3شهور {tech['perf_3m']}%
- حجم: {tech['last_vol']} vs متوسط {tech['avg_vol_20']} نسبة {tech['vol_ratio']}x
حلل بعمق.
"""
    if not client:
        return {"error": "No GROQ_API_KEY", "technical": tech, "tradingview": deep["tradingview"], "chart_url": f"/chart/{deep['symbol']}"}
    
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT_DEEP},{"role": "user", "content": context}],
                temperature=0.5,
                max_tokens=4000
            )
            return {
                "symbol": deep["symbol"],
                "name": deep["name"],
                "price": deep["price"],
                "change_pct": deep["change_pct"],
                "technical": tech,
                "deep_analysis": res.choices[0].message.content,
                "tradingview": deep["tradingview"],
                "chart_url": f"/chart/{deep['symbol']}",
                "model_used": current_model,
                "time": deep["time"]
            }
        except Exception as e:
            if "model" in str(e).lower() or "404" in str(e):
                continue
            break
    return {"error": "فشل التحليل", "technical": tech}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        return {"reply": "❌ GROQ_API_KEY غير موجود"}
    is_deep = any(k in req.message for k in ["عميق","تحليل","RSI","شامل","رسم","شارت","TradingView","تريدنج"])
    detected = []
    import re as re2
    for m in re2.findall(r'\b(\d{4})\b', req.message):
        detected.append(m)
    for arabic in SAUDI_SYMBOLS.keys():
        if arabic in req.message:
            detected.append(arabic)
    if not detected and any(k in req.message for k in ["سهم","سعر","تداول"]):
        detected.append("2222")
    detected = list(set(detected))[:2]
    
    if detected and is_deep:
        deep_result = analyze_deep(detected[0])
        if "deep_analysis" in deep_result:
            reply = deep_result["deep_analysis"]
            reply += f"\n\n📈 الرسم البياني: /chart/{deep_result['symbol']}\n🔗 TradingView: {deep_result['tradingview']}"
            return {"reply": reply, "model_used": deep_result.get("model_used"), "chart_url": deep_result.get("chart_url"), "tradingview": deep_result.get("tradingview")}
    
    stock_context = ""
    chart_url = tradingview = None
    if detected:
        for sym in detected:
            data = get_stock_deep(sym)
            if "error" not in data:
                t = data["technical"]
                stock_context += f"- {data['name']} ({data['symbol']}): {data['price']} ({data['change_pct']}%) RSI {t['rsi14']} SMA20 {t['sma20']}\n"
                chart_url = f"/chart/{data['symbol']}"
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
            return {"reply": reply, "model_used": current_model, "chart_url": chart_url, "tradingview": tradingview}
        except Exception as e:
            if "model" in str(e).lower() or "404" in str(e):
                continue
            break
    return {"reply": f"❌ فشل"}

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
