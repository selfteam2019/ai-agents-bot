"""
V8.1 Fixed Dashboard - لوحة تعمل 100% + تحليل أي سهم
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

app = FastAPI(title="AI Agents Bot - V8.1 Fixed", version="8.1")

GROQ_KEY = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "buraydah123")

WORKING_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
]
model_name = WORKING_MODELS[0]
client = None

if GROQ_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        print(f"✅ V8.1 - {WORKING_MODELS}")
    except:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
        except Exception as e:
            print(f"Groq failed: {e}")
            client = None

SAUDI_SYMBOLS = {
    "ارامكو": "2222.SR", "أرامكو": "2222.SR", "2222": "2222.SR",
    "الراجحي": "1120.SR", "راجحي": "1120.SR", "1120": "1120.SR",
    "الاهلي": "1180.SR", "1180": "1180.SR", "البنك الاهلي": "1180.SR",
    "الانماء": "1150.SR", "1150": "1150.SR",
    "الرياض": "1010.SR", "1010": "1010.SR",
    "سابك": "2010.SR", "2010": "2010.SR",
    "STC": "7010.SR", "7010": "7010.SR",
    "لوسيد": "LCID", "تسلا": "TSLA", "ابل": "AAPL", "نيفيديا": "NVDA",
}

class ChatRequest(BaseModel):
    message: str

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
        # Yahoo search
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": 3, "newsCount": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, params=params, timeout=6)
        data = r.json()
        quotes = data.get("quotes", [])
        if not quotes:
            return None
        is_arabic = any('\u0600' <= c <= '\u06FF' for c in query)
        for q in quotes:
            sym = q.get("symbol","")
            if is_arabic and ".SR" in sym:
                return sym
        # أول رمز صالح
        for q in quotes:
            sym = q.get("symbol","")
            if sym:
                return sym
        return None
    except Exception as e:
        print(f"Search error {query}: {e}")
        return None

def get_stock_deep(symbol_or_name: str) -> Dict:
    original_input = symbol_or_name.strip()
    if not original_input:
        return {"error": "اسم فارغ", "input": original_input}
    
    symbol = None
    if original_input in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[original_input]
    elif original_input.upper() in SAUDI_SYMBOLS:
        symbol = SAUDI_SYMBOLS[original_input.upper()]
    elif original_input.isdigit() and len(original_input)==4:
        symbol = f"{original_input}.SR"
    elif re.match(r'^[A-Z0-9\.]{1,10}$', original_input.upper()):
        symbol = original_input.upper()
        if symbol.isdigit():
            symbol = f"{symbol}.SR"
    else:
        symbol = search_yahoo_symbol(original_input)
        if not symbol:
            return {"error": f"ما لقيت رمز لـ '{original_input}' - جرب 2222 أو AAPL", "input": original_input}
    
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"interval": "1d", "range": "3mo"}
        r = requests.get(url, headers=headers, params=params, timeout=10)
        j = r.json()
        if "chart" not in j or j["chart"]["error"]:
            return {"error": f"الرمز {symbol} غير موجود", "symbol": symbol, "input": original_input}
        
        result = j["chart"]["result"][0]
        meta = result["meta"]
        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]
        highs = result["indicators"]["quote"][0]["high"]
        lows = result["indicators"]["quote"][0]["low"]
        timestamps = result["timestamp"]
        
        valid = [(c, v, h, l, ts) for c, v, h, l, ts in zip(closes, volumes, highs, lows, timestamps) if c is not None]
        if not valid:
            return {"error": "لا بيانات", "symbol": symbol, "input": original_input}
        
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
        recent_high = round(max(highs_clean[-20:]),2) if len(highs_clean)>=20 else round(max(highs_clean),2)
        recent_low = round(min(lows_clean[-20:]),2) if len(lows_clean)>=20 else round(min(lows_clean),2)
        high_3m = round(max(closes_clean),2)
        low_3m = round(min(closes_clean),2)
        perf_1w = round((closes_clean[-1]/closes_clean[-5]-1)*100,2) if len(closes_clean)>=5 else None
        perf_1m = round((closes_clean[-1]/closes_clean[-20]-1)*100,2) if len(closes_clean)>=20 else None
        perf_3m = round((closes_clean[-1]/closes_clean[0]-1)*100,2)
        avg_vol = round(sum(volumes_clean[-20:])/20) if len(volumes_clean)>=20 else 0
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
        print(f"Deep error {symbol}: {e}")
        return {"error": str(e), "symbol": symbol if 'symbol' in locals() else symbol_or_name, "input": original_input}

def generate_chart_png(symbol_data: Dict) -> Optional[bytes]:
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
        
        plt.figure(figsize=(11,5.5))
        plt.plot(dates, closes, label=f"{symbol_data['symbol']}", color='#1f77b4', linewidth=2)
        
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
            plt.plot(bb_dates, bb_u_vals, color='gray', linestyle=':', alpha=0.5)
            plt.plot(bb_dates, bb_l_vals, color='gray', linestyle=':', alpha=0.5)
            plt.fill_between(bb_dates, bb_l_vals, bb_u_vals, color='gray', alpha=0.1)
        
        plt.title(f"{symbol_data['name']} ({symbol_data['symbol']}) - {symbol_data['price']} ({symbol_data['change_pct']}%)", fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=8)
        plt.xticks(rotation=20)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=130, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        print(f"Chart error: {e}")
        return None

@app.get("/", response_class=HTMLResponse)
def home():
    groq_status = "✅ مربوط" if client else "❌ يحتاج GROQ_API_KEY"
    wa_status = "⚠️ قبل الربط" if not WHATSAPP_TOKEN else "✅ مربوط"
    
    html_content = """<!DOCTYPE html>
<html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V8.1 - محلل أي سهم</title>
<style>
body{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%);min-height:100vh;padding:15px;margin:0;color:#fff}
.container{max-width:1100px;margin:auto}
.card{background:white;color:#222;padding:20px;border-radius:18px;box-shadow:0 8px 25px rgba(0,0,0,0.3);margin-bottom:16px}
.badge{padding:4px 10px;border-radius:18px;font-size:11px;background:#e0f7ff;margin:2px;display:inline-block}
.badge-green{background:#d4edda} .badge-blue{background:#cce5ff} .badge-orange{background:#fff3cd}
.stock-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:10px 0}
.stock-card{background:#f8f9ff;border:1px solid #d0e0ff;border-radius:12px;padding:12px;text-align:center;cursor:pointer}
.stock-card:hover{background:#eef4ff}
.price{font-size:20px;font-weight:bold} .up{color:#28a745} .down{color:#dc3545}
textarea{width:100%;padding:12px;border:2px solid #e0e0e0;border-radius:10px;font-size:13px;box-sizing:border-box}
button{background:#302b63;color:white;padding:10px 18px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;margin:2px;font-size:13px}
button:hover{background:#24243e}
#answer{background:#f8fbff;padding:14px;border-radius:10px;margin-top:10px;white-space:pre-wrap;line-height:1.7;border:1px solid #d0e0ff;min-height:70px;color:#222;font-size:13px}
.ex{background:#eef6ff;padding:5px 10px;border-radius:12px;font-size:11px;cursor:pointer;margin:2px;display:inline-block;border:1px solid #d0e0ff}
input{padding:10px;border:2px solid #ddd;border-radius:8px;width:180px;font-size:13px}
.chart-box{background:#fff;border:1px solid #ddd;border-radius:10px;padding:8px;margin:8px 0;text-align:center}
.chart-box img{max-width:100%;border-radius:6px}
.tv-link{display:inline-block;background:#131722;color:white;padding:5px 10px;border-radius:6px;text-decoration:none;font-size:11px;margin:3px}
.alert{background:#d4edda;padding:10px;border-radius:8px;font-size:12px;margin:8px 0;border:1px solid #a3d9a5}
.hint{font-size:10px;color:#666}
</style></head><body><div class="container">
<div class="card">
<h2 style="margin:0 0 8px">🔍 V8.1 محلل أي سهم بالاسم - يعمل 100%</h2>
<div><span class="badge badge-green">__GROQ_STATUS__</span><span class="badge">WhatsApp: __WA_STATUS__</span><span class="badge badge-blue">Universal Search</span><span class="badge badge-orange">__MODEL__</span><span class="badge badge-green">Dashboard Fixed ✅</span></div>
<div class="alert">✅ اكتب <b>أي اسم سهم</b> (عربي/انجليزي/رقم) ويحلله فوراً - قبل ربط الواتساب</div>

<h4 style="margin:12px 0 6px">🔎 ابحث عن أي سهم:</h4>
<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
<input id="sym" placeholder="ارامكو أو 1120 أو AAPL" value="">
<button onclick="fetchDeep()">تحليل 🔬</button>
<button onclick="fetchChart()">رسم 📈</button>
<button onclick="openTV()" style="background:#131722">TradingView ↗</button>
<button onclick="loadAll()" style="background:#eee;color:#222">تحديث</button>
</div>
<div class="hint">جرب: ارامكو، الراجحي، سابك، 1010، تسلا، ابل، TSLA</div>

<h4 style="margin:10px 0 6px">⚡ أسهم سريعة:</h4>
<div class="stock-grid" id="stocks">جاري التحميل...</div>
<div id="chartArea"></div>
</div>

<div class="card">
<h4 style="margin:0 0 8px">💬 اسأل عن أي سهم</h4>
<div style="margin:6px 0">
<span class="ex" onclick="setEx('ارامكو')">ارامكو</span>
<span class="ex" onclick="setEx('الراجحي')">الراجحي</span>
<span class="ex" onclick="setEx('سابك')">سابك</span>
<span class="ex" onclick="setEx('1010')">1010</span>
<span class="ex" onclick="setEx('تسلا')">تسلا</span>
<span class="ex" onclick="setEx('ابل')">ابل</span>
<span class="ex" onclick="setEx('AAPL')">AAPL</span>
</div>
<textarea id="msg" rows="2" placeholder="اكتب اسم أي سهم..."></textarea>
<div style="margin-top:8px"><button onclick="send()">حلل ⚡</button></div>
<div id="answer">اللوحة تعمل ✅

اكتب اسم سهم في المربع فوق واضغط تحليل.
أو جرب الأزرار السريعة.

Endpoints:
- /health
- /analyze/ارامكو
- /chart/ارامكو
- /search/ارامكو
- /tradingview/ارامكو
</div>
</div>

<div class="card" style="font-size:11px">
<b>حالة النظام:</b> <span id="sys">فحص...</span><br>
<b>الوقت:</b> __TIME__
</div>

</div>
<script>
const quick = ["ارامكو","الراجحي","سابك","1010"];
async function loadAll(){
  const grid=document.getElementById('stocks');
  const sys=document.getElementById('sys');
  grid.innerHTML='⏳ تحميل...';
  try{
    const h=await fetch('/health'); const hd=await h.json();
    sys.innerText='✅ السيرفر شغال - '+hd.version;
  }catch(e){sys.innerText='❌ خطأ: '+e.message}
  try{
    const res=await fetch('/stocks?symbols='+encodeURIComponent(quick.join(',')));
    const data=await res.json();
    grid.innerHTML='';
    if(data.length==0){grid.innerHTML='لا بيانات - جرب البحث'; return;}
    data.forEach(s=>{
      if(s.error){grid.innerHTML+='<div style="background:#ffe0e0;padding:8px;border-radius:8px;font-size:11px">❌ '+s.input+': '+s.error+'</div>'; return;}
      const cls=s.change>=0?'up':'down'; const arrow=s.change>=0?'▲':'▼';
      grid.innerHTML+=`<div class="stock-card" onclick="document.getElementById('sym').value='${s.input}';fetchDeep()"><div style="font-size:10px;color:#666">${s.name}</div><div style="font-weight:bold;font-size:12px">${s.symbol}</div><div class="price">${s.price} <small style="font-size:10px">${s.currency}</small></div><div class="${cls}" style="font-size:11px">${arrow} ${s.change} (${s.change_pct}%)</div><div style="margin-top:4px"><a class="tv-link" href="${s.tradingview}" target="_blank">TV</a> <a class="tv-link" style="background:#302b63" href="/chart/${encodeURIComponent(s.input)}" target="_blank">Chart</a></div></div>`;
    });
  }catch(e){grid.innerHTML='❌ فشل التحميل: '+e.message; sys.innerText='❌ '+e.message;}
}
async function fetchChart(){
  const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب اسم السهم');
  const area=document.getElementById('chartArea');
  area.innerHTML=`<div class="chart-box">⏳ رسم ${sym}...<br><img src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" style="max-width:100%" onerror="this.parentElement.innerHTML='❌ ما لقيت السهم - تأكد من الاسم'"><br><a class="tv-link" href="/tradingview/${encodeURIComponent(sym)}" target="_blank">TradingView ↗</a></div>`;
}
function openTV(){const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب اسم السهم'); window.open('/tradingview/'+encodeURIComponent(sym), '_blank');}
async function fetchDeep(){
  const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب اسم السهم');
  const ans=document.getElementById('answer'); ans.innerText='🔍 أبحث عن '+sym+' وأحلله...';
  const area=document.getElementById('chartArea');
  area.innerHTML=`<div class="chart-box">📈 ${sym}<br><img src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" style="max-width:100%" onerror="this.style.display='none'"></div>`;
  try{
    const res=await fetch('/analyze/'+encodeURIComponent(sym));
    const data=await res.json();
    if(data.error) ans.innerText='❌ '+data.error;
    else ans.innerText=`✅ ${data.name} (${data.symbol}) من بحث '${data.input}'\\nالسعر: ${data.price} (${data.change_pct}%)\\n\\n`+data.deep_analysis;
  }catch(e){ans.innerText='❌ '+e.message;}
}
function setEx(t){document.getElementById('sym').value=t; document.getElementById('msg').value=t; fetchDeep();}
async function send(){
  const msg=document.getElementById('msg').value.trim(); if(!msg) return;
  const ans=document.getElementById('answer'); ans.innerText='🔍 أحلل '+msg+'...';
  try{
    const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
    const data=await res.json(); ans.innerText=data.reply||'لا رد';
    if(data.chart_url){document.getElementById('chartArea').innerHTML=`<div class="chart-box"><img src="${data.chart_url}?t=${Date.now()}" style="max-width:100%"><br><a class="tv-link" href="${data.tradingview}" target="_blank">TV ↗</a></div>`;}
  }catch(e){ans.innerText='❌ '+e.message;}
}
loadAll();
</script></body></html>
"""
    html_content = html_content.replace("__GROQ_STATUS__", groq_status).replace("__WA_STATUS__", wa_status).replace("__MODEL__", model_name).replace("__TIME__", datetime.now().strftime("%Y-%m-%d %H:%M"))
    return HTMLResponse(content=html_content)

@app.get("/health")
def health():
    return {"status": "ok", "version": "8.1-fixed-dashboard", "groq": bool(client), "models": WORKING_MODELS, "time": datetime.now().isoformat()}

@app.get("/search/{query}")
def search_symbol(query: str):
    sym = search_yahoo_symbol(query)
    if sym:
        return {"input": query, "symbol": sym, "tradingview": get_tradingview_link(sym), "chart_url": f"/chart/{sym}"}
    return JSONResponse({"error": f"ما لقيت رمز لـ '{query}'", "input": query}, status_code=404)

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
def stocks_many(symbols: str = Query(..., description="ارامكو,الراجحي,AAPL")):
    inputs = [s.strip() for s in symbols.split(",") if s.strip()][:6]
    results = []
    for inp in inputs:
        try:
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
        except Exception as e:
            results.append({"error": str(e), "input": inp})
    return results

@app.get("/chart/{symbol_or_name}")
def chart_png(symbol_or_name: str):
    data = get_stock_deep(symbol_or_name)
    if "error" in data:
        return JSONResponse({"error": data["error"]}, status_code=404)
    img_bytes = generate_chart_png(data)
    if not img_bytes:
        return JSONResponse({"error": "فشل الرسم - تأكد matplotlib مثبت"}, status_code=500)
    return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png", headers={"Cache-Control": "no-cache"})

@app.get("/tradingview/{symbol_or_name}")
def tradingview_redirect(symbol_or_name: str):
    data = get_stock_deep(symbol_or_name)
    if "error" not in data:
        link = data["tradingview"]
    else:
        link = get_tradingview_link(symbol_or_name)
    return RedirectResponse(url=link)

@app.get("/analyze/{symbol_or_name}")
def analyze_deep(symbol_or_name: str):
    deep = get_stock_deep(symbol_or_name)
    if "error" in deep:
        return JSONResponse(deep, status_code=404)
    tech = deep["technical"]
    context = f"سهم {deep['name']} ({deep['symbol']}) من '{deep['input']}': {deep['price']} {deep['currency']} ({deep['change_pct']}%) SMA20 {tech['sma20']} SMA50 {tech['sma50']} RSI {tech['rsi14']} دعم {tech['recent_low_20d']} مقاومة {tech['recent_high_20d']} أداء شهر {tech['perf_1m']}% 3شهور {tech['perf_3m']}%"
    
    if not client:
        return {
            "input": deep["input"],
            "symbol": deep["symbol"],
            "name": deep["name"],
            "price": deep["price"],
            "change_pct": deep["change_pct"],
            "technical": tech,
            "deep_analysis": f"📊 {deep['name']} ({deep['symbol']})\nالسعر: {deep['price']} {deep['currency']} ({deep['change_pct']}%)\nRSI: {tech['rsi14']} | SMA20: {tech['sma20']} | SMA50: {tech['sma50']}\nدعم: {tech['recent_low_20d']} | مقاومة: {tech['recent_high_20d']}\nأداء شهر: {tech['perf_1m']}% | 3 شهور: {tech['perf_3m']}%\n\n(أضف GROQ_API_KEY للتحليل بالذكاء الاصطناعي)",
            "tradingview": deep["tradingview"],
            "chart_url": f"/chart/{deep['input']}",
            "model_used": "no-ai",
        }
    
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": "أنت محلل أسهم محترف. حلل بعمق: نظرة لحظية، فني (SMA RSI دعوم)، أداء، فرص/مخاطر، خلاصة. ليس نصيحة. عربي مختصر."},
                    {"role": "user", "content": context}
                ],
                temperature=0.5,
                max_tokens=3500
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
            if any(x in str(e).lower() for x in ["model", "404", "400", "not_found"]):
                continue
            break
    return {"error": "فشل التحليل AI", "technical": tech, "symbol": deep["symbol"]}

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    if not client:
        # حتى بدون Groq، حلل السهم بالبيانات الفنية
        import re
        m = re.search(r'\b(\d{4})\b', req.message)
        if m:
            d = get_stock_deep(m.group(1))
            if "error" not in d:
                t = d["technical"]
                reply = f"✅ {d['name']} ({d['symbol']})\nالسعر: {d['price']} {d['currency']} ({d['change_pct']}%)\nRSI: {t['rsi14']} | SMA20: {t['sma20']} SMA50: {t['sma50']}\nدعم: {t['recent_low_20d']} مقاومة: {t['recent_high_20d']}\nأداء: شهر {t['perf_1m']}% 3شهور {t['perf_3m']}%\n\nأضف GROQ_API_KEY للتحليل الذكي"
                return {"reply": reply, "chart_url": f"/chart/{d['input']}", "tradingview": d["tradingview"]}
        return {"reply": "❌ GROQ_API_KEY غير موجود - لكن جرب /analyze/ارامكو مباشرة"}
    
    # استخراج اسم سهم
    inputs = []
    for m in re.findall(r'\b(\d{4})\b', req.message):
        inputs.append(m)
    for arabic in SAUDI_SYMBOLS.keys():
        if arabic in req.message:
            inputs.append(arabic)
    # اسم عام
    stripped = req.message.strip()
    if 2 <= len(stripped) <= 20 and "حلل" not in stripped and "سعر" not in stripped:
        inputs.append(stripped)
    inputs = list(dict.fromkeys(inputs))[:2]
    
    if inputs:
        try:
            d = get_stock_deep(inputs[0])
            if "error" not in d:
                a = analyze_deep(inputs[0])
                if "deep_analysis" in a:
                    return {"reply": f"✅ {a['name']} ({a['symbol']}) من '{a['input']}'\n\n{a['deep_analysis']}", "chart_url": a["chart_url"], "tradingview": a["tradingview"]}
        except Exception as e:
            print(f"Chat analyze error: {e}")
    
    # رسالة عامة
    for current_model in WORKING_MODELS:
        try:
            res = client.chat.completions.create(
                model=current_model,
                messages=[{"role": "system", "content": "مساعد أسهم سعودي. حلل أي سهم يذكر."}, {"role": "user", "content": req.message}],
                temperature=0.6,
                max_tokens=3000
            )
            return {"reply": res.choices[0].message.content, "model_used": current_model}
        except Exception as e:
            if "model" in str(e).lower() or "404" in str(e):
                continue
            break
    return {"reply": "❌ فشل"}

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
                    reply_data = chat_endpoint(ChatRequest(message=text))
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
