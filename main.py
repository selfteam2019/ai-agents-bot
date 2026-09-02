"""
V9.0 WhatsApp Full - ربط واتساب مع إرسال صورة الشارت
- يرسل صورة الشارت كصورة في الواتساب + تحليل نصي
- معالجة JSON robust
- جاهز للربط
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

app = FastAPI(title="AI Agents Bot - V9 WhatsApp Image", version="9.0")

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
]
model_name = WORKING_MODELS[0]
client = None

if GROQ_KEY:
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        print(f"✅ V9 WhatsApp Image - {WORKING_MODELS}")
    except:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=GROQ_KEY, base_url="https://api.groq.com/openai/v1")
        except:
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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"❌ Global error at {request.url}: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(status_code=200, content={"error": str(exc), "path": str(request.url)})

def calc_rsi(prices, period=14):
    try:
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
    except:
        return None

def get_tradingview_link(symbol: str) -> str:
    try:
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
    except:
        return "https://www.tradingview.com/"

def search_yahoo_symbol(query: str) -> Optional[str]:
    try:
        query = query.strip()
        if not query:
            return None
        if query.isdigit() and len(query)==4:
            return f"{query}.SR"
        if query in SAUDI_SYMBOLS:
            return SAUDI_SYMBOLS[query]
        if query.upper() in SAUDI_SYMBOLS:
            return SAUDI_SYMBOLS[query.upper()]
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": 3, "newsCount": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, params=params, timeout=6)
        if "text/html" in r.headers.get("Content-Type",""):
            return None
        try:
            data = r.json()
        except:
            return None
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
            if sym:
                return sym
        return None
    except Exception as e:
        print(f"Search error {query}: {e}")
        return None

def get_stock_deep(symbol_or_name: str) -> Dict:
    try:
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
            if "text/html" in r.headers.get("Content-Type",""):
                return {"error": f"Yahoo حجب الطلب لـ {symbol}", "symbol": symbol, "input": original_input}
            try:
                data = r.json()
            except:
                return {"error": f"فشل قراءة بيانات {symbol}", "symbol": symbol, "input": original_input}
            if "chart" not in data or data["chart"].get("error"):
                err = data.get("chart",{}).get("error",{}) if "chart" in data else {}
                desc = err.get("description","") if err else "غير موجود"
                return {"error": f"الرمز {symbol} غير موجود ({desc})", "symbol": symbol, "input": original_input}
            result = data["chart"]["result"][0]
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
                    "sma20": sma20, "sma50": sma50, "rsi14": rsi,
                    "recent_high_20d": recent_high, "recent_low_20d": recent_low,
                    "high_3m": high_3m, "low_3m": low_3m,
                    "perf_1w": perf_1w, "perf_1m": perf_1m, "perf_3m": perf_3m,
                    "avg_vol_20": avg_vol, "last_vol": volumes_clean[-1], "vol_ratio": vol_ratio,
                }
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"خطأ جلب بيانات {symbol}: {str(e)}", "symbol": symbol if 'symbol' in locals() else symbol_or_name, "input": original_input}
    except Exception as e:
        return {"error": f"خطأ عام: {str(e)}", "input": symbol_or_name}

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
        plt.figure(figsize=(11,5.5))
        plt.plot(dates, closes, label=f"{symbol_data['symbol']}", color='#1f77b4', linewidth=2)
        sma20_dates = [d for d, v in zip(dates, sma20_list) if v is not None]
        sma20_vals = [v for v in sma20_list if v is not None]
        if sma20_vals:
            plt.plot(sma20_dates, sma20_vals, label='SMA 20', color='orange', linestyle='--', alpha=0.8)
        plt.title(f"{symbol_data['name']} ({symbol_data['symbol']}) - {symbol_data['price']} ({symbol_data['change_pct']}%)", fontsize=11)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=8)
        plt.xticks(rotation=15)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        print(f"Chart error: {e}")
        return None

# ========== WhatsApp Functions - إرسال صورة + نص ==========
def get_base_url(request: Request = None) -> str:
    if BASE_URL:
        return BASE_URL.rstrip('/')
    if request:
        scheme = request.url.scheme
        host = request.headers.get('host','')
        if host:
            return f"{scheme}://{host}"
    return os.getenv("RENDER_EXTERNAL_URL", "").rstrip('/')

def upload_whatsapp_media(image_bytes: bytes) -> Optional[str]:
    """يرفع الصورة لواتساب ويرجع media_id"""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        return None
    try:
        url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/media"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        files = {'file': ('chart.png', image_bytes, 'image/png')}
        data = {'type': 'image/png', 'messaging_product': 'whatsapp'}
        print(f"📤 Uploading {len(image_bytes)} bytes to WhatsApp...")
        r = requests.post(url, headers=headers, files=files, data=data, timeout=20)
        print(f"Upload response: {r.status_code} {r.text[:300]}")
        if r.status_code == 200:
            return r.json().get('id')
        return None
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def send_whatsapp_image_by_id(to: str, media_id: str, caption: str = "") -> bool:
    try:
        url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"id": media_id, "caption": caption[:1000]}
        }
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"Send image by ID: {r.status_code} {r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        print(f"Send image ID error: {e}")
        return False

def send_whatsapp_image_by_link(to: str, image_url: str, caption: str = "") -> bool:
    try:
        url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"link": image_url, "caption": caption[:1000]}
        }
        print(f"📤 Sending image by link: {image_url}")
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"Send image link: {r.status_code} {r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        print(f"Send link error: {e}")
        return False

def send_whatsapp_text(to: str, text: str):
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        print("❌ No WhatsApp creds")
        return False
    try:
        url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:3800]}}
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"Send text: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"Send text error: {e}")
        return False

# ========== Endpoints ==========
@app.get("/", response_class=HTMLResponse)
def home():
    groq_status = "✅ مربوط" if client else "❌ يحتاج GROQ_API_KEY"
    wa_status = "✅ مربوط" if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID else "⚠️ لم يربط بعد"
    html_content = """<!DOCTYPE html>
<html dir="rtl" lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>V9 WhatsApp - ربط واتساب</title>
<style>
body{font-family:'Segoe UI',Tahoma;background:linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%);min-height:100vh;padding:12px;margin:0;color:#fff}
.container{max-width:1100px;margin:auto}
.card{background:white;color:#222;padding:18px;border-radius:16px;box-shadow:0 6px 20px rgba(0,0,0,0.3);margin-bottom:14px}
.badge{padding:4px 9px;border-radius:14px;font-size:10px;background:#e0f7ff;margin:2px;display:inline-block}
.badge-green{background:#d4edda} .badge-blue{background:#cce5ff} .badge-orange{background:#fff3cd}
.step{background:#f8f9ff;border:1px solid #d0e0ff;border-radius:10px;padding:12px;margin:8px 0}
.step h4{margin:0 0 6px;color:#302b63}
.code{background:#1a1a2e;color:#00ff88;padding:8px 12px;border-radius:6px;font-family:monospace;font-size:11px;margin:6px 0;direction:ltr;text-align:left;overflow-x:auto}
input{padding:8px;border:2px solid #ddd;border-radius:6px;width:200px;font-size:12px}
button{background:#302b63;color:white;padding:8px 14px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;margin:2px;font-size:12px}
#answer{background:#f8fbff;padding:12px;border-radius:8px;margin-top:8px;white-space:pre-wrap;line-height:1.6;border:1px solid #d0e0ff;min-height:60px;color:#222;font-size:12px}
.ex{background:#eef6ff;padding:4px 8px;border-radius:10px;font-size:10px;cursor:pointer;margin:2px;display:inline-block;border:1px solid #d0e0ff}
.stock-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin:8px 0}
.stock-card{background:#f8f9ff;border:1px solid #d0e0ff;border-radius:10px;padding:10px;text-align:center;cursor:pointer;font-size:11px}
.price{font-size:16px;font-weight:bold} .up{color:#28a745} .down{color:#dc3545}
.chart-box{background:#fff;border:1px solid #ddd;border-radius:8px;padding:6px;margin:6px 0;text-align:center}
.tv-link{display:inline-block;background:#131722;color:white;padding:4px 8px;border-radius:5px;text-decoration:none;font-size:10px;margin:2px}
</style></head><body><div class="container">

<div class="card">
<h2 style="margin:0 0 8px">📱 V9.0 ربط الواتساب - خطوة خطوة</h2>
<div><span class="badge badge-green">__GROQ_STATUS__</span><span class="badge">__WA_STATUS__</span><span class="badge badge-blue">WhatsApp Image Ready</span><span class="badge badge-green">V9 ✅</span></div>
</div>

<div class="card">
<h3>📋 خطوات الربط (10 دقائق):</h3>

<div class="step">
<h4>الخطوة 1: أنشئ تطبيق في Meta Developers</h4>
<ol style="font-size:12px">
<li>ادخل <a href="https://developers.facebook.com/" target="_blank">developers.facebook.com</a> وسجل دخول</li>
<li>اضغط <b>My Apps</b> → <b>Create App</b></li>
<li>اختر <b>Business</b> → اسم التطبيق: <b>AI Agents Bot</b> → Create</li>
</ol>
</div>

<div class="step">
<h4>الخطوة 2: أضف منتج WhatsApp</h4>
<ol style="font-size:12px">
<li>من لوحة التطبيق → <b>Add Product</b> → اختر <b>WhatsApp</b> → Set Up</li>
<li>سيعطيك رقم تجريبي و Phone Number ID و Access Token</li>
</ol>
</div>

<div class="step">
<h4>الخطوة 3: احصل على المعلومات المطلوبة</h4>
<p style="font-size:12px">من صفحة WhatsApp → API Setup ستجد:</p>
<ul style="font-size:11px">
<li><b>Phone Number ID</b>: رقم طويل مثل 123456789... انسخه</li>
<li><b>WhatsApp Business Account ID</b>: ليس مطلوب</li>
<li><b>Access Token</b>: اضغط Generate أو استخدم المؤقت - يبدأ بـ EAA...</li>
<li><b>رقم الهاتف التجريبي</b>: مثل +1 555...</li>
</ul>
</div>

<div class="step">
<h4>الخطوة 4: اربط الـ Webhook</h4>
<p style="font-size:12px">في نفس صفحة WhatsApp → <b>Configuration</b> → <b>Webhook</b> → Edit:</p>
<div class="code">Callback URL: https://YOUR-APP.onrender.com/webhook
Verify Token: buraydah123</div>
<p style="font-size:11px">⚠️ غيّر YOUR-APP برابط تطبيقك في Render (مثل https://ai-agents-bot-xyz.onrender.com/webhook)</p>
<p style="font-size:11px">اضغط Verify and Save - لازم يرجع ✅</p>
<p style="font-size:11px">بعدها في <b>Webhook fields</b> اضغط Manage واشترك في <b>messages</b></p>
</div>

<div class="step">
<h4>الخطوة 5: أضف المتغيرات في Render</h4>
<p style="font-size:12px">روح Render → تطبيقك → Environment → Add Variable:</p>
<div class="code">GROQ_API_KEY = gsk_... (من groq.com)
WHATSAPP_TOKEN = EAA... (من Meta)
WHATSAPP_PHONE_ID = 123456789... (Phone Number ID)
VERIFY_TOKEN = buraydah123
BASE_URL = https://YOUR-APP.onrender.com
</div>
<p style="font-size:11px">اضغط Save Changes - Render بيعيد التشغيل تلقائياً</p>
</div>

<div class="step">
<h4>الخطوة 6: أضف رقمك كـ Test Number</h4>
<p style="font-size:12px">في Meta → WhatsApp → API Setup → <b>To</b> → Manage phone number list → Add → أدخل رقمك السعودي مع 966 (مثل 9665xxxxxxxx)</p>
<p style="font-size:11px">سيصلك كود واتساب، أدخله للتأكيد</p>
</div>

<div class="step">
<h4>الخطوة 7: جرب!</h4>
<p style="font-size:12px">أرسل من رقمك التجريبي رسالة واتساب لأي رقم اختبرته:</p>
<div class="code">ارامكو
الراجحي
1120
تسلا
حلل ارامكو مع صورة
</div>
<p style="font-size:11px">البوت بيرسل:<br>
1. 📸 صورة الشارت كصورة<br>
2. 💬 تحليل نصي عميق<br>
3. 🔗 رابط TradingView</p>
</div>

<div class="step">
<h4>الخطوة 8: للنشر العام (اختياري)</h4>
<p style="font-size:11px">إذا تبغى أي شخص يراسل البوت، لازم تطلب موافقة Meta وتضيف طريقة دفع. للتجربة، الـ Test Numbers كافية.</p>
</div>
</div>

<div class="card">
<h4>🧪 اختبار سريع بدون واتساب:</h4>
<div style="display:flex;gap:6px;flex-wrap:wrap">
<input id="sym" placeholder="ارامكو أو 1120" value="">
<button onclick="fetchDeep()">تحليل 🔬</button>
<button onclick="fetchChart()">رسم 📈</button>
<button onclick="openTV()" style="background:#131722">TV ↗</button>
</div>
<div class="stock-grid" id="stocks">جاري التحميل...</div>
<div id="chartArea"></div>
<div id="answer" style="margin-top:8px">جرب الأزرار فوق...</div>
</div>

<div class="card" style="font-size:11px">
<b>Endpoints للواتساب:</b><br>
• Webhook Verify: GET /webhook?hub.mode=subscribe&hub.verify_token=buraydah123&hub.challenge=123<br>
• Webhook Receive: POST /webhook<br>
• Health: /health<br>
• تحليل: /analyze/ارامكو<br>
• رسم: /chart/ارامكو<br>
<br>
<b>حالة:</b> Groq: __GROQ_STATUS__ | WhatsApp: __WA_STATUS__ | Model: __MODEL__
</div>

</div>
<script>
const quick=["ارامكو","الراجحي","1120","AAPL"];
async function safeFetchJson(url){
  const res=await fetch(url); const text=await res.text();
  try{return JSON.parse(text);}catch(e){throw new Error('Not JSON: '+text.substring(0,200));}
}
async function loadAll(){
  const grid=document.getElementById('stocks'); grid.innerHTML='⏳...';
  try{
    const data=await safeFetchJson('/stocks?symbols='+encodeURIComponent(quick.join(',')));
    grid.innerHTML='';
    data.forEach(s=>{
      if(s.error){grid.innerHTML+=`<div class="stock-card" style="background:#ffe0e0">❌ ${s.input}</div>`; return;}
      const cls=s.change>=0?'up':'down'; const arrow=s.change>=0?'▲':'▼';
      grid.innerHTML+=`<div class="stock-card" onclick="document.getElementById('sym').value='${s.input}';fetchDeep()"><div style="font-size:9px">${s.name}</div><div style="font-weight:bold">${s.symbol}</div><div class="price">${s.price}</div><div class="${cls}">${arrow} ${s.change_pct}%</div></div>`;
    });
  }catch(e){grid.innerHTML='❌ '+e.message;}
}
async function fetchChart(){
  const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب اسم السهم');
  document.getElementById('chartArea').innerHTML=`<div class="chart-box"><img src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" style="max-width:100%"></div>`;
}
function openTV(){const s=document.getElementById('sym').value.trim(); if(!s) return alert('اكتب'); window.open('/tradingview/'+encodeURIComponent(s),'_blank');}
async function fetchDeep(){
  const sym=document.getElementById('sym').value.trim(); if(!sym) return alert('اكتب');
  const ans=document.getElementById('answer'); ans.innerText='🔍 أحلل '+sym+'...';
  document.getElementById('chartArea').innerHTML=`<div class="chart-box"><img src="/chart/${encodeURIComponent(sym)}?t=${Date.now()}" style="max-width:100%"></div>`;
  try{
    const data=await safeFetchJson('/analyze/'+encodeURIComponent(sym));
    if(data.error) ans.innerText='❌ '+data.error;
    else ans.innerText=`✅ ${data.name} (${data.symbol})\\n` + data.deep_analysis;
  }catch(e){ans.innerText='❌ '+e.message;}
}
loadAll();
</script></body></html>
"""
    html_content = html_content.replace("__GROQ_STATUS__", "✅ Groq مربوط" if client else "❌ يحتاج GROQ_API_KEY").replace("__WA_STATUS__", "✅ مربوط" if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID else "⚠️ لم يربط").replace("__MODEL__", model_name)
    return HTMLResponse(content=html_content)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "9.0-whatsapp-image",
        "groq": bool(client),
        "whatsapp": bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID),
        "base_url": BASE_URL or "not set",
        "webhook_url": f"{BASE_URL}/webhook" if BASE_URL else "set BASE_URL env var",
        "verify_token": VERIFY_TOKEN
    }

@app.get("/search/{query}")
def search_symbol(query: str):
    try:
        sym = search_yahoo_symbol(query)
        if sym:
            return {"input": query, "symbol": sym, "tradingview": get_tradingview_link(sym)}
        return JSONResponse({"error": f"ما لقيت رمز لـ '{query}'", "input": query}, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=200)

@app.get("/stock/{symbol_or_name}")
def stock_one(symbol_or_name: str):
    try:
        data = get_stock_deep(symbol_or_name)
        if "error" in data:
            return JSONResponse(data, status_code=200)
        return {"input": data["input"], "symbol": data["symbol"], "name": data["name"], "price": data["price"], "change_pct": data["change_pct"], "tradingview": data["tradingview"]}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=200)

@app.get("/stocks")
def stocks_many(symbols: str = Query(...)):
    try:
        inputs = [s.strip() for s in symbols.split(",") if s.strip()][:6]
        results = []
        for inp in inputs:
            try:
                d = get_stock_deep(inp)
                if "error" not in d:
                    results.append({"input": d["input"], "symbol": d["symbol"], "name": d["name"], "price": d["price"], "change": d["change"], "change_pct": d["change_pct"], "currency": d["currency"], "tradingview": d["tradingview"]})
                else:
                    results.append(d)
            except Exception as e:
                results.append({"error": str(e), "input": inp})
        return results
    except Exception as e:
        return JSONResponse([{"error": str(e)}], status_code=200)

@app.get("/chart/{symbol_or_name}")
def chart_png(symbol_or_name: str):
    try:
        data = get_stock_deep(symbol_or_name)
        if "error" in data:
            return JSONResponse(data, status_code=200)
        img = generate_chart_png(data)
        if not img:
            return JSONResponse({"error": "فشل الرسم"}, status_code=200)
        return StreamingResponse(io.BytesIO(img), media_type="image/png", headers={"Cache-Control": "no-cache"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=200)

@app.get("/tradingview/{symbol_or_name}")
def tv_redirect(symbol_or_name: str):
    try:
        data = get_stock_deep(symbol_or_name)
        link = data["tradingview"] if "error" not in data else get_tradingview_link(symbol_or_name)
        return RedirectResponse(url=link)
    except:
        return RedirectResponse(url=get_tradingview_link(symbol_or_name))

@app.get("/analyze/{symbol_or_name}")
def analyze_deep(symbol_or_name: str):
    try:
        deep = get_stock_deep(symbol_or_name)
        if "error" in deep:
            return JSONResponse(deep, status_code=200)
        tech = deep["technical"]
        if not client:
            return {
                "input": deep["input"], "symbol": deep["symbol"], "name": deep["name"],
                "price": deep["price"], "change_pct": deep["change_pct"], "technical": tech,
                "deep_analysis": f"📊 {deep['name']} ({deep['symbol']})\nالسعر: {deep['price']} ({deep['change_pct']}%)\nRSI: {tech['rsi14']} SMA20: {tech['sma20']}\nدعم: {tech['recent_low_20d']} مقاومة: {tech['recent_high_20d']}",
                "tradingview": deep["tradingview"], "chart_url": f"/chart/{deep['input']}"
            }
        context = f"سهم {deep['name']} ({deep['symbol']}): {deep['price']} ({deep['change_pct']}%) SMA20 {tech['sma20']} SMA50 {tech['sma50']} RSI {tech['rsi14']}"
        for current_model in WORKING_MODELS:
            try:
                res = client.chat.completions.create(
                    model=current_model,
                    messages=[{"role": "system", "content": "محلل أسهم محترف. حلل بعمق مختصر."}, {"role": "user", "content": context}],
                    temperature=0.5, max_tokens=3500
                )
                return {
                    "input": deep["input"], "symbol": deep["symbol"], "name": deep["name"],
                    "price": deep["price"], "change_pct": deep["change_pct"], "technical": tech,
                    "deep_analysis": res.choices[0].message.content,
                    "tradingview": deep["tradingview"], "chart_url": f"/chart/{deep['input']}", "model_used": current_model
                }
            except Exception as e:
                if any(x in str(e).lower() for x in ["model", "404", "400"]):
                    continue
                break
        return {"error": "فشل التحليل AI", "symbol": deep["symbol"]}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=200)

@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    try:
        # محاولة استخراج سهم
        inputs = []
        for mm in re.findall(r'\b(\d{4})\b', req.message):
            inputs.append(mm)
        for arabic in SAUDI_SYMBOLS.keys():
            if arabic in req.message:
                inputs.append(arabic)
        stripped = req.message.strip()
        if 2 <= len(stripped) <= 20 and "حلل" not in stripped and len(inputs)==0:
            inputs.append(stripped)
        inputs = list(dict.fromkeys(inputs))[:1]
        
        if inputs:
            try:
                d = get_stock_deep(inputs[0])
                if "error" not in d:
                    a = analyze_deep(inputs[0])
                    if "deep_analysis" in a:
                        return {"reply": f"✅ {a['name']} ({a['symbol']})\n\n{a['deep_analysis']}\n\n🔗 {a['tradingview']}", "chart_url": a["chart_url"], "tradingview": a["tradingview"], "symbol": a["symbol"], "input": a["input"]}
            except:
                pass
        
        if not client:
            return {"reply": "❌ GROQ_API_KEY غير موجود - جرب /analyze/ارامكو"}
        
        for current_model in WORKING_MODELS:
            try:
                res = client.chat.completions.create(
                    model=current_model,
                    messages=[{"role": "system", "content": "مساعد أسهم سعودي."}, {"role": "user", "content": req.message}],
                    temperature=0.6, max_tokens=3000
                )
                return {"reply": res.choices[0].message.content, "model_used": current_model}
            except Exception as e:
                if "model" in str(e).lower() or "404" in str(e):
                    continue
                break
        return {"reply": "❌ فشل"}
    except Exception as e:
        return JSONResponse({"reply": f"❌ خطأ: {str(e)}"}, status_code=200)

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    print(f"🔍 Webhook verify: mode={mode} token={token} challenge={challenge}")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print(f"✅ Webhook verified!")
        return int(challenge) if challenge and challenge.isdigit() else HTMLResponse(content=challenge or "ok")
    print(f"❌ Webhook verify failed: expected {VERIFY_TOKEN}, got {token}")
    return JSONResponse({"error": "verification failed"}, status_code=403)

@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        body = await request.json()
        print(f"📩 Webhook received: {body}")
        base_url = BASE_URL or str(request.base_url).rstrip('/')
        
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    from_number = msg.get("from")
                    text = msg.get("text", {}).get("body", "") if msg.get("type") == "text" else ""
                    if not text:
                        continue
                    print(f"📩 Message from {from_number}: {text}")
                    
                    # هل يطلب سهم؟
                    is_stock_request = any(k in text for k in ["ارامكو","الراجحي","سابك","سهم","2222","1120","2010","1010","تسلا","ابل","رسم","شارت","صورة","حلل","STC","AAPL","TSLA"])
                    
                    if is_stock_request:
                        # استخراج أول سهم
                        detected = []
                        for mm in re.findall(r'\b(\d{4})\b', text):
                            detected.append(mm)
                        for arabic in SAUDI_SYMBOLS.keys():
                            if arabic in text:
                                detected.append(arabic)
                        if not detected:
                            detected.append("2222")
                        symbol_input = detected[0]
                        
                        # جلب بيانات + رسم
                        stock_data = get_stock_deep(symbol_input)
                        if "error" not in stock_data:
                            img_bytes = generate_chart_png(stock_data)
                            caption = f"📊 {stock_data['name']} ({stock_data['symbol']})\nالسعر: {stock_data['price']} {stock_data['currency']} ({stock_data['change_pct']}%)\nRSI: {stock_data['technical']['rsi14']} | SMA20: {stock_data['technical']['sma20']}\n🔗 {stock_data['tradingview']}"
                            
                            if img_bytes:
                                # حاول رفع الصورة
                                media_id = upload_whatsapp_media(img_bytes)
                                if media_id:
                                    send_whatsapp_image_by_id(from_number, media_id, caption)
                                else:
                                    # fallback: رابط
                                    chart_url = f"{base_url}/chart/{stock_data['input']}" if base_url else f"/chart/{stock_data['input']}"
                                    # إذا BASE_URL موجود، أرسل بالرابط
                                    if BASE_URL:
                                        send_whatsapp_image_by_link(from_number, f"{base_url}/chart/{stock_data['input']}", caption)
                                    else:
                                        # بدون BASE_URL، أرسل نص + رابط
                                        send_whatsapp_text(from_number, caption + f"\n📈 الرسم: {chart_url}")
                            else:
                                send_whatsapp_text(from_number, caption)
                        
                        # تحليل نصي
                        reply_data = chat_endpoint(ChatRequest(message=text))
                        reply_text = reply_data.get("reply","")
                        if isinstance(reply_data, dict) and "reply" in reply_data:
                            send_whatsapp_text(from_number, reply_text[:3800])
                    else:
                        # رسالة عامة
                        reply_data = chat_endpoint(ChatRequest(message=text))
                        if isinstance(reply_data, dict):
                            text_reply = reply_data.get("reply","عذراً")
                        else:
                            text_reply = str(reply_data)
                        send_whatsapp_text(from_number, text_reply[:3800])
    except Exception as e:
        print(f"Webhook error: {e}")
        import traceback
        traceback.print_exc()
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
