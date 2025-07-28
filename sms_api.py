
from flask import Flask, request, jsonify
import telebot
import json
import os
import time
from datetime import datetime
import random

app = Flask(__name__)

SMS_TOKEN = "supersecrettoken"
BOT_TOKEN = os.environ.get("BOT_TOKEN")

USERS_DB = 'users.json'
PENDING_DB = 'pending.json'
CARD_DB = 'card_db.json'
BALANCE_DB = 'balances.json'

ADMIN_ID = 123456789

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

def load_json(file, default):
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump(default, f)
    with open(file, 'r') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def get_balance(card):
    balances = load_json(BALANCE_DB, {})
    return balances.get(card, random.randint(10_000_000, 50_000_000))

def update_balance(card, amount):
    balances = load_json(BALANCE_DB, {})
    current = balances.get(card, random.randint(10_000_000, 50_000_000))
    new_balance = max(0, current - amount)
    balances[card] = new_balance
    save_json(BALANCE_DB, balances)
    return new_balance

def detect_bank(card):
    prefixes = {
        "603799": "ملی",
        "610433": "ملت",
        "627353": "تجارت",
        "622106": "پارسیان",
        "589463": "رفاه",
        "627760": "پاسارگاد",
        "603770": "کشاورزی",
        "505801": "مهر ایران",
        "628023": "مسکن",
        "636214": "بلو"
    }
    return prefixes.get(card[:6], "ملت")

def fake_sms(amount, card, balance=None, bank=None):
    if bank is None:
        bank = detect_bank(card)
    if balance is None:
        balance = get_balance(card)
    now = datetime.now().strftime("%Y/%m/%d - %H:%M")
    return f"[{bank}] {amount:,} ریال واریز شد.\nمانده: {balance:,} ریال\nتاریخ: {now}"

@app.route('/send-sms', methods=['POST'])
def send_sms_api():
    data = request.json
    if not data or data.get('token') != SMS_TOKEN:
        return jsonify({'status': 'unauthorized'}), 403

    number = data.get('number')
    message = data.get('message')

    if not number or not message:
        return jsonify({'status': 'error', 'message': 'Missing number or message'}), 400

    print(f"[API] Sending SMS to {number}: {message}")
    time.sleep(1)
    return jsonify({'status': 'sent', 'to': number})

# Telegram Bot handlers remain unchanged...

import threading
threading.Thread(target=lambda: bot.polling(non_stop=True)).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
