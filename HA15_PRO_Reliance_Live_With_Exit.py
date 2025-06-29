
import requests
import pandas as pd
import time
from datetime import datetime
import pytz

# === Configuration ===
TELEGRAM_TOKEN = '8087212112:AAGUH7XK76YMlu48IRxpuSwV50DDQKbdAsQ'
TELEGRAM_CHAT_ID = '5572777641'
STOCK_SYMBOL = 'RELIANCE.BO'  # Reliance on BSE
INTERVAL = 900  # 15 minutes
MARKET_START = datetime.strptime("09:30", "%H:%M").time()
MARKET_END = datetime.strptime("11:00", "%H:%M").time()

# === Telegram Message ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    requests.post(url, data=payload)

# === Heikin Ashi Calculation ===
def heikin_ashi(df):
    df_ha = df.copy()
    df_ha['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    df_ha['HA_Open'] = 0.0
    df_ha['HA_Open'].iloc[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    for i in range(1, len(df)):
        df_ha['HA_Open'].iloc[i] = (df_ha['HA_Open'].iloc[i - 1] + df_ha['HA_Close'].iloc[i - 1]) / 2
    df_ha['HA_High'] = df[['High', 'HA_Open', 'HA_Close']].max(axis=1)
    df_ha['HA_Low'] = df[['Low', 'HA_Open', 'HA_Close']].min(axis=1)
    return df_ha

# === Strategy Logic ===

# === Auto-Exit Alert Logic ===
def check_ha15_exit(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    condition = (
        (last['HA_Close'] < last['HA_Open']) and
        (prev['HA_Close'] < prev['HA_Open'])
    )
    if condition:
        send_telegram_message('📥 Entry Signal Triggered')
        msg = (
            f"🔻 HA-15 EXIT SIGNAL - RELIANCE\n"
            f"🕒 Time: {last.name.strftime('%Y-%m-%d %H:%M')}\n"
            f"📉 Price: ₹{last['HA_Close']:.2f}\n"
            f"🔄 2 Red Heikin Ashi candles → Exit trade."
        )
        send_telegram_message(msg)
    check_ha15_exit(df)

def check_ha15_entry():
    global df
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{STOCK_SYMBOL}?interval=15m&range=2d'
    response = requests.get(url)
    data = response.json()
    timestamps = data['chart']['result'][0]['timestamp']
    ohlc = data['chart']['result'][0]['indicators']['quote'][0]

    df = pd.DataFrame({
        'Timestamp': [datetime.fromtimestamp(ts, tz=pytz.timezone('Asia/Kolkata')) for ts in timestamps],
        'Open': ohlc['open'],
        'High': ohlc['high'],
        'Low': ohlc['low'],
        'Close': ohlc['close'],
        'Volume': ohlc['volume']
    }).dropna()

    df.set_index('Timestamp', inplace=True)
    df = heikin_ashi(df)
    df['Volume_SMA5'] = df['Volume'].rolling(window=5).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]
    now = last.name.time()

    condition = (
        (last['HA_Close'] > last['HA_Open']) and
        (prev['HA_Close'] > prev['HA_Open']) and
        (last['Volume'] > last['Volume_SMA5']) and
        (MARKET_START <= now <= MARKET_END)
    )

    if condition:
        send_telegram_message('📥 Entry Signal Triggered')
        msg = (
            f"🚨 HA-15 PRO ENTRY SIGNAL - RELIANCE\n"
            f"🕒 Time: {last.name.strftime('%Y-%m-%d %H:%M')}\n"
            f"📈 Price: ₹{last['HA_Close']:.2f}\n"
            f"📊 Volume: {int(last['Volume'])} (SMA5: {int(last['Volume_SMA5'])})\n"
            f"✅ 2 Green HA Candles with volume confirmation."
        )
        send_telegram_message(msg)
    check_ha15_exit(df)

# === Live Check Loop ===
while True:
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    if now.weekday() < 5:  # Mon–Fri only
        try:
            check_ha15_entry()
        except Exception as e:
            send_telegram_message(f"⚠️ Error in HA-15 PRO Script: {e}")
    time.sleep(INTERVAL)
