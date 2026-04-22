import ccxt
import pandas as pd
import ta
import time
import requests
import os
from datetime import datetime

# Settings

BITGET_API_KEY = os.environ.get("BITGET_API_KEY", "")
BITGET_API_SECRET = os.environ.get("BITGET_API_SECRET", "")
BITGET_PASSPHRASE = os.environ.get("BITGET_PASSPHRASE", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SYMBOLS = [
    "BTC/USDT:USDT", "ETH/USDT:USDT", "XRP/USDT:USDT",
    "SOL/USDT:USDT", "DOGE/USDT:USDT", "PEPE/USDT:USDT",
    "TAO/USDT:USDT", "TRX/USDT:USDT", "INJ/USDT:USDT",
    "ZEC/USDT:USDT", "ASTER/USDT:USDT", "ADA/USDT:USDT",
    "HYPER/USDT:USDT", "HBAR/USDT:USDT", "ETC/USDT:USDT",
    "APT/USDT:USDT", "RIVER/USDT:USDT", "SHIB/USDT:USDT",
    "BNB/USDT:USDT", "AVAX/USDT:USDT", "LINK/USDT:USDT",
    "SUI/USDT:USDT", "XLM/USDT:USDT", "AAVE/USDT:USDT",
    "BCH/USDT:USDT",
]

ACCOUNT_SIZE = 24
RISK_PCT = 0.02
TIMEFRAME = "1h"
CHECK_INTERVAL = 300
ATR_PERIOD = 14
ATR_SL_MULT = 1.5
ATR_TP_MULT = 3.0
MAX_LEVERAGE = 20
LIQ_BUFFER = 0.025

exchange = ccxt.bitget({
    'apiKey': BITGET_API_KEY,
    'secret': BITGET_API_SECRET,
    'password': BITGET_PASSPHRASE,
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}
})

bot_active = True
last_update_id = 0
signals_today = 0


def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")


def check_commands():
    global bot_active, last_update_id, signals_today
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=1&offset={last_update_id+1}"
        r = requests.get(url, timeout=5).json()
        for update in r.get('result', []):
            last_update_id = update['update_id']
            msg = update.get('message', {}).get('text', '').lower()
            if '/stop' in msg:
                bot_active = False
                send_telegram("Bot stopped. Send /start to resume.")
            elif '/start' in msg:
                bot_active = True
                send_telegram("Bot is active!")
            elif '/status' in msg:
                send_telegram(
                    f"Status: {'Active' if bot_active else 'Stopped'}\n"
                    f"Signals today: {signals_today}\n"
                    f"Account: ${ACCOUNT_SIZE}\n"
                    f"Coins: {len(SYMBOLS)}"
                )
    except:
        pass


def get_data(symbol):
    try:
        candles = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        print(f"Error {symbol.split('/')[0]}: {e}")
        return None


def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['ma_fast'] = df['close'].rolling(window=9).mean()
    df['ma_slow'] = df['close'].rolling(window=21).mean()
    macd = ta.trend.MACD(df['close'])
    df['macd_diff'] = macd.macd_diff()
    df['atr'] = ta.volatility.AverageTrueRange(
        df['high'], df['low'], df['close'], window=ATR_PERIOD
    ).average_true_range()
    return df


def analyze_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    score = 0
    reasons = []

    rsi = last['rsi']
    if rsi < 30:
        score += 2
        reasons.append(f"RSI {rsi:.1f} oversold")
    elif rsi > 70:
        score -= 2
        reasons.append(f"RSI {rsi:.1f} overbought")
    else:
        reasons.append(f"RSI {rsi:.1f} neutral")

    if last['ma_fast'] > last['ma_slow'] and prev['ma_fast'] <= prev['ma_slow']:
        score += 2
        reasons.append("MA crossed up")
    elif last['ma_fast'] < last['ma_slow'] and prev['ma_fast'] >= prev['ma_slow']:
        score -= 2
        reasons.append("MA crossed down")
    elif last['ma_fast'] > last['ma_slow']:
        score += 1
        reasons.append("MA uptrend")
    else:
        score -= 1
        reasons.append("MA downtrend")

    if last['macd_diff'] > 0 and prev['macd_diff'] <= 0:
        score += 1
        reasons.append("MACD positive cross")
    elif last['macd_diff'] < 0 and prev['macd_diff'] >= 0:
        score -= 1
        reasons.append("MACD negative cross")

    if score >= 3:
        signal = "BUY"
    elif score <= -3:
        signal = "SELL"
    else:
        signal = "HOLD"

    return signal, score, reasons, last['close'], rsi, last['atr']


def calculate_params(price, atr, side):
    sl_dist = atr * ATR_SL_MULT
    tp_dist = atr * ATR_TP_MULT

    if side == "BUY":
        sl = price - sl_dist
        tp = price + tp_dist
        liq_target = sl * (1 - LIQ_BUFFER)
        leverage = int(price / (price - liq_target))
        liq = price / (1 + 1 / max(leverage, 1))
    else:
        sl = price + sl_dist
        tp = price - tp_dist
        liq_target = sl * (1 + LIQ_BUFFER)
        leverage = int(price / (liq_target - price))
        liq = price / (1 - 1 / max(leverage, 1))

    leverage = max(1, min(leverage, MAX_LEVERAGE))
    risk_amount = ACCOUNT_SIZE * RISK_PCT
    qty = risk_amount / sl_dist
    position_usdt = qty * price
    margin = position_usdt / leverage
    profit = tp_dist * qty
    loss = sl_dist * qty

    return {
        'sl': sl, 'tp': tp, 'liq': liq,
        'leverage': leverage, 'margin': margin,
        'position': position_usdt, 'qty': qty,
        'profit': profit, 'loss': loss
    }


def process_symbol(symbol):
    global signals_today

    df = get_data(symbol)
    if df is None:
        return

    df = calculate_indicators(df)
    signal, score, reasons, price, rsi, atr = analyze_signal(df)

    coin = symbol.split('/')[0]
    now = datetime.now().strftime("%H:%M")
    emoji = {"BUY": "BUY", "SELL": "SELL", "HOLD": "HOLD"}[signal]

    print(f"[{now}] {coin:<10} ${price:>12,.4f} | RSI:{rsi:5.1f} | {emoji} ({score:+d})")

    if not bot_active or signal == "HOLD":
        return

    p = calculate_params(price, atr, signal)
    reasons_text = "\n".join([f"  - {r}" for r in reasons])

    msg = (
        f"{'BUY' if signal == 'BUY' else 'SELL'} Signal! {coin}\n"
        f"{'=' * 20}\n"
        f"Entry:        ${price:,.4f}\n"
        f"Stop Loss:    ${p['sl']:,.4f}\n"
        f"Take Profit:  ${p['tp']:,.4f}\n"
        f"Liquidation:  ${p['liq']:,.4f}\n"
        f"{'=' * 20}\n"
        f"Leverage:     x{p['leverage']}\n"
        f"Margin:       ${p['margin']:.2f}\n"
        f"Position:     ${p['position']:.2f}\n"
        f"{'=' * 20}\n"
        f"If win:  +${p['profit']:.2f}\n"
        f"If lose: -${p['loss']:.2f}\n"
        f"{'=' * 20}\n"
        f"Reasons:\n{reasons_text}"
    )

    send_telegram(msg)
    signals_today += 1
    print(f"  Signal sent! Profit: +${p['profit']:.2f} | Loss: -${p['loss']:.2f}")


def main():
    print("Bot starting...")
    print(f"Account: ${ACCOUNT_SIZE} | Coins: {len(SYMBOLS)}")

    send_telegram(
        "Bot started!\n\n"
        f"Account: ${ACCOUNT_SIZE}\n"
        f"Coins: {len(SYMBOLS)}\n"
        f"Timeframe: {TIMEFRAME}\n"
        f"Risk per trade: ${ACCOUNT_SIZE * RISK_PCT:.2f}\n\n"
        "Commands: /stop /start /status"
    )

    while True:
        try:
            check_commands()
            print(f"\nScanning... {datetime.now().strftime('%H:%M:%S')}")

            for symbol in SYMBOLS:
                process_symbol(symbol)
                time.sleep(0.5)

            print(f"Next scan in {CHECK_INTERVAL // 60} minutes...")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("Bot stopped.")
            send_telegram("Bot stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
