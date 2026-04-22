# “””
🤖 בוט איתותי מסחר — Bitget Futures

✅ 25 מטבעות
✅ איתותים לטלגרם — אתה נכנס ידנית
✅ מינוף אוטומטי — ליקווידציה 2-2.5% מתחת לסטופ
✅ סטופ ויעד לפי ATR
✅ כמה תרוויח / כמה תפסיד — מחושב לפי $24
✅ /stop /start /status

━━━━━━━━━━━━━━━━━━━━━━━━
התקנה:
pip install ccxt pandas ta requests

━━━━━━━━━━━━━━━━━━━━━━━━
איך להשיג API Key מ-Bitget:

1. Bitget → פרופיל → API Management
1. Create API → סמן Read בלבד (לא צריך Trade!)
1. שמור: API Key + Secret + Passphrase

━━━━━━━━━━━━━━━━━━━━━━━━
איך ליצור בוט טלגרם:

1. טלגרם → @BotFather → /newbot
1. קבל TOKEN
1. שלח הודעה לבוט שלך
1. היכנס: https://api.telegram.org/bot<TOKEN>/getUpdates
1. קח את “id” מתוך “chat” = CHAT_ID

━━━━━━━━━━━━━━━━━━━━━━━━
פקודות טלגרם:
/stop   — עוצר איתותים
/start  — מפעיל מחדש
/status — מצב הבוט
“””

import ccxt
import pandas as pd
import ta
import time
import requests
from datetime import datetime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ⚙️ הגדרות — חובה למלא!

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BITGET_API_KEY     = “הכנס_API_KEY”
BITGET_API_SECRET  = “הכנס_SECRET_KEY”
BITGET_PASSPHRASE  = “הכנס_PASSPHRASE”

TELEGRAM_BOT_TOKEN = “הכנס_BOT_TOKEN”
TELEGRAM_CHAT_ID   = “הכנס_CHAT_ID”

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 📋 25 מטבעות

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYMBOLS = [
“BTC/USDT:USDT”,
“ETH/USDT:USDT”,
“XRP/USDT:USDT”,
“SOL/USDT:USDT”,
“DOGE/USDT:USDT”,
“PEPE/USDT:USDT”,
“TAO/USDT:USDT”,
“TRX/USDT:USDT”,
“INJ/USDT:USDT”,
“ZEC/USDT:USDT”,
“ASTER/USDT:USDT”,
“ADA/USDT:USDT”,
“HYPER/USDT:USDT”,
“HBAR/USDT:USDT”,
“ETC/USDT:USDT”,
“APT/USDT:USDT”,
“RIVER/USDT:USDT”,
“1000SHIB/USDT:USDT”,
“BNB/USDT:USDT”,
“AVAX/USDT:USDT”,
“LINK/USDT:USDT”,
“SUI/USDT:USDT”,
“XLM/USDT:USDT”,
“AAVE/USDT:USDT”,
“BCH/USDT:USDT”,
# להוסיף מטבע חדש — הוסף שורה כאן:
# “DOT/USDT:USDT”,
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ⚙️ הגדרות

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACCOUNT_SIZE     = 24       # גודל חשבון USDT
RISK_PCT         = 0.02     # 2% סיכון לעסקה
TIMEFRAME        = “1h”     # טיים פריים
CHECK_INTERVAL   = 300      # בדיקה כל 5 דקות
ATR_PERIOD       = 14
ATR_SL_MULT      = 1.5      # סטופ = ATR × 1.5
ATR_TP_MULT      = 3.0      # יעד = ATR × 3.0
MAX_LEVERAGE     = 20       # מינוף מקסימלי
LIQ_BUFFER       = 0.025    # ליקווידציה 2.5% מתחת לסטופ

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 🔌 חיבור ל-Bitget (קריאה בלבד)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

exchange = ccxt.bitget({
‘apiKey’: BITGET_API_KEY,
‘secret’: BITGET_API_SECRET,
‘password’: BITGET_PASSPHRASE,
‘enableRateLimit’: True,
‘options’: {‘defaultType’: ‘swap’}
})

# מצב בוט

bot_active     = True
last_update_id = 0
signals_today  = 0

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 📱 טלגרם

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def send_telegram(message):
try:
url = f”https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage”
requests.post(url, data={
“chat_id”: TELEGRAM_CHAT_ID,
“text”: message,
“parse_mode”: “HTML”
}, timeout=10)
except Exception as e:
print(f”⚠️ טלגרם: {e}”)

def check_commands():
global bot_active, last_update_id, signals_today
try:
url = f”https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=1&offset={last_update_id+1}”
r = requests.get(url, timeout=5).json()
for update in r.get(‘result’, []):
last_update_id = update[‘update_id’]
msg = update.get(‘message’, {}).get(‘text’, ‘’).lower()

```
        if '/stop' in msg:
            bot_active = False
            send_telegram("⏹️ <b>בוט עצר.</b>\nלא ישלח איתותים.\nשלח /start להפעלה.")

        elif '/start' in msg:
            bot_active = True
            send_telegram("▶️ <b>בוט פעיל!</b> שולח איתותים.")

        elif '/status' in msg:
            send_telegram(
                f"📊 <b>סטטוס</b>\n"
                f"מצב: {'✅ פעיל' if bot_active else '⏹️ עצור'}\n"
                f"איתותים היום: {signals_today}\n"
                f"חשבון: ${ACCOUNT_SIZE}\n"
                f"מטבעות: {len(SYMBOLS)}"
            )
except:
    pass
```

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 📊 נתונים ואינדיקטורים

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_data(symbol):
try:
candles = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
df = pd.DataFrame(candles, columns=[‘timestamp’,‘open’,‘high’,‘low’,‘close’,‘volume’])
df[‘timestamp’] = pd.to_datetime(df[‘timestamp’], unit=‘ms’)
return df
except Exception as e:
print(f”❌ {symbol.split(’/’)[0]}: {e}”)
return None

def calculate_indicators(df):
df[‘rsi’]       = ta.momentum.RSIIndicator(df[‘close’], window=14).rsi()
df[‘ma_fast’]   = df[‘close’].rolling(window=9).mean()
df[‘ma_slow’]   = df[‘close’].rolling(window=21).mean()
macd            = ta.trend.MACD(df[‘close’])
df[‘macd_diff’] = macd.macd_diff()
df[‘atr’]       = ta.volatility.AverageTrueRange(
df[‘high’], df[‘low’], df[‘close’], window=ATR_PERIOD
).average_true_range()
return df

def analyze_signal(df):
last  = df.iloc[-1]
prev  = df.iloc[-2]
score = 0
reasons = []

```
rsi = last['rsi']
if rsi < 30:
    score += 2
    reasons.append(f"RSI {rsi:.1f} — מכור יתר ✅")
elif rsi > 70:
    score -= 2
    reasons.append(f"RSI {rsi:.1f} — קנוי יתר ❌")
else:
    reasons.append(f"RSI {rsi:.1f} — נטרלי")

if last['ma_fast'] > last['ma_slow'] and prev['ma_fast'] <= prev['ma_slow']:
    score += 2
    reasons.append("MA חצה מעלה ✅")
elif last['ma_fast'] < last['ma_slow'] and prev['ma_fast'] >= prev['ma_slow']:
    score -= 2
    reasons.append("MA חצה מטה ❌")
elif last['ma_fast'] > last['ma_slow']:
    score += 1
    reasons.append("MA מגמה עולה ↗")
else:
    score -= 1
    reasons.append("MA מגמה יורדת ↘")

if last['macd_diff'] > 0 and prev['macd_diff'] <= 0:
    score += 1
    reasons.append("MACD חצה חיובי ✅")
elif last['macd_diff'] < 0 and prev['macd_diff'] >= 0:
    score -= 1
    reasons.append("MACD חצה שלילי ❌")

if score >= 3:
    signal = "BUY"
elif score <= -3:
    signal = "SELL"
else:
    signal = "HOLD"

return signal, score, reasons, last['close'], rsi, last['atr']
```

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 💰 חישוב פרמטרי עסקה

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calculate_params(price, atr, side):
sl_dist = atr * ATR_SL_MULT
tp_dist = atr * ATR_TP_MULT

```
if side == "BUY":
    sl = price - sl_dist
    tp = price + tp_dist
    # ליקווידציה 2.5% מתחת לסטופ
    liq_target = sl * (1 - LIQ_BUFFER)
    leverage   = int(price / (price - liq_target))
    liq        = price / (1 + 1/max(leverage,1))
else:
    sl = price + sl_dist
    tp = price - tp_dist
    liq_target = sl * (1 + LIQ_BUFFER)
    leverage   = int(price / (liq_target - price))
    liq        = price / (1 - 1/max(leverage,1))

leverage = max(1, min(leverage, MAX_LEVERAGE))

# גודל פוזיציה
risk_amount   = ACCOUNT_SIZE * RISK_PCT   # $0.48
qty           = risk_amount / sl_dist
position_usdt = qty * price
margin        = position_usdt / leverage

profit = tp_dist * qty
loss   = sl_dist * qty

return {
    'sl': sl, 'tp': tp, 'liq': liq,
    'leverage': leverage, 'margin': margin,
    'position': position_usdt, 'qty': qty,
    'profit': profit, 'loss': loss
}
```

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 🔄 עיבוד מטבע

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def process_symbol(symbol):
global signals_today

```
df = get_data(symbol)
if df is None:
    return

df = calculate_indicators(df)
signal, score, reasons, price, rsi, atr = analyze_signal(df)

coin  = symbol.split('/')[0]
now   = datetime.now().strftime("%H:%M")
emoji = {"BUY":"🟢","SELL":"🔴","HOLD":"⏳"}[signal]

print(f"[{now}] {coin:<10} ${price:>12,.4f} | RSI:{rsi:5.1f} | {emoji} {signal} ({score:+d})")

if not bot_active or signal == "HOLD":
    return

# חשב פרמטרים
p = calculate_params(price, atr, signal)
reasons_text = "\n".join([f"  • {r}" for r in reasons])

msg = (
    f"{'🟢' if signal == 'BUY' else '🔴'} <b>איתות {signal}! {coin}</b>\n"
    f"━━━━━━━━━━━━━━━━━━━\n"
    f"💵 כניסה:        ${price:,.4f}\n"
    f"🛑 שים סטופ ב:   ${p['sl']:,.4f}\n"
    f"🎯 שים יעד ב:    ${p['tp']:,.4f}\n"
    f"💀 ליקווידציה:   ${p['liq']:,.4f}\n"
    f"━━━━━━━━━━━━━━━━━━━\n"
    f"⚡ מינוף:        x{p['leverage']}\n"
    f"💰 מרג'ין:       ${p['margin']:.2f}\n"
    f"📦 פוזיציה:      ${p['position']:.2f}\n"
    f"━━━━━━━━━━━━━━━━━━━\n"
    f"✅ אם מנצח:     +${p['profit']:.2f}\n"
    f"❌ אם מפסיד:    -${p['loss']:.2f}\n"
    f"━━━━━━━━━━━━━━━━━━━\n"
    f"📋 סיבות:\n{reasons_text}"
)

send_telegram(msg)
signals_today += 1
print(f"  📱 איתות נשלח! רווח פוטנציאלי: +${p['profit']:.2f} | הפסד: -${p['loss']:.2f}")
```

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 🚀 לולאה ראשית

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
print(”\n” + “━”*50)
print(”  🤖 בוט איתותי Bitget”)
print(“━”*50)
print(f”  חשבון: ${ACCOUNT_SIZE} | מטבעות: {len(SYMBOLS)}”)
print(f”  סיכון לעסקה: {RISK_PCT*100:.0f}% = ${ACCOUNT_SIZE*RISK_PCT:.2f}”)
print(“━”*50 + “\n”)

```
send_telegram(
    "🤖 <b>בוט האיתותים התחיל!</b>\n\n"
    f"💰 חשבון: ${ACCOUNT_SIZE}\n"
    f"📋 מטבעות: {len(SYMBOLS)}\n"
    f"⏱ טיים פריים: {TIMEFRAME}\n"
    f"⚠️ סיכון לעסקה: ${ACCOUNT_SIZE*RISK_PCT:.2f}\n\n"
    "אני אשלח לך איתותים עם:\n"
    "✅ כניסה, סטופ, יעד\n"
    "✅ מינוף מומלץ\n"
    "✅ כמה תרוויח / תפסיד\n\n"
    "פקודות: /stop /start /status"
)

while True:
    try:
        check_commands()

        print(f"\n{'━'*50}")
        print(f"  🔍 סריקה | {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'━'*50}")

        for symbol in SYMBOLS:
            process_symbol(symbol)
            time.sleep(0.5)

        print(f"\n⏳ בדיקה הבאה בעוד {CHECK_INTERVAL//60} דקות...")
        time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n👋 הבוט נעצר.")
        send_telegram("⏹️ הבוט נעצר.")
        break
    except Exception as e:
        print(f"\n❌ שגיאה: {e}")
        time.sleep(60)
```

if **name** == “**main**”:
main()
