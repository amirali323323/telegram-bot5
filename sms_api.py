
from flask import Flask, request, jsonify
import telebot
import json
import os
import time
from datetime import datetime
import random

app = Flask(__name__)

# 🔐 کلید امنیتی API تحت وب
SMS_TOKEN = "supersecrettoken"

# 🔐 توکن ربات تلگرام از محیط
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# فایل‌های داده
USERS_DB = 'users.json'
PENDING_DB = 'pending.json'
CARD_DB = 'card_db.json'
BALANCE_DB = 'balances.json'

ADMIN_ID = 123456789  # 🛑 جایگزین کن با عدد تلگرام خودت

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
    return f"[{bank}] {amount:,} ریال واریز شد.\\nمانده: {balance:,} ریال\\nتاریخ: {now}"
مانده: {balance:,} ریال
تاریخ: {now}"

# Flask API route برای دریافت پیامک از سیستم‌های دیگر
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

# ==== Telegram Bot ====

def is_user_registered(user_id):
    return user_id in load_json(USERS_DB, [])

def is_user_pending(user_id):
    return user_id in load_json(PENDING_DB, [])

def request_registration(user_id):
    pending = load_json(PENDING_DB, [])
    if user_id not in pending:
        pending.append(user_id)
        save_json(PENDING_DB, pending)

def approve_user(user_id):
    users = load_json(USERS_DB, [])
    pending = load_json(PENDING_DB, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_DB, users)
    if user_id in pending:
        pending.remove(user_id)
        save_json(PENDING_DB, pending)

@bot.message_handler(commands=['start'])
def start(message):
    if not is_user_registered(message.chat.id):
        bot.send_message(message.chat.id, "❌ شما ثبت‌نام نشده‌اید. /register را بزنید.")
        return
    bot.send_message(message.chat.id, "سلام! مبلغ واریزی را وارد کنید:")

@bot.message_handler(commands=['register'])
def register(message):
    user_id = message.chat.id
    if is_user_registered(user_id):
        bot.send_message(user_id, "✅ قبلاً ثبت‌نام کرده‌اید.")
    elif is_user_pending(user_id):
        bot.send_message(user_id, "⏳ درخواست شما در حال بررسی است.")
    else:
        request_registration(user_id)
        bot.send_message(user_id, "📥 درخواست ثبت‌نام ارسال شد. منتظر تایید ادمین باشید.")
        bot.send_message(ADMIN_ID, f"🔐 درخواست جدید:
{user_id}")

@bot.message_handler(commands=['approve'])
def approve(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "⛔ فقط ادمین می‌تواند تایید کند.")
        return
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            bot.reply_to(message, "فرمت درست: /approve USER_ID")
            return
        user_id = int(parts[1])
        if not is_user_pending(user_id):
            bot.reply_to(message, "این کاربر در انتظار نیست.")
            return
        approve_user(user_id)
        bot.send_message(user_id, "🎉 ثبت‌نام شما تایید شد.")
        bot.reply_to(message, f"✅ تایید شد: {user_id}")
    except:
        bot.reply_to(message, "خطا در تایید.")

@bot.message_handler(func=lambda m: True)
def handle_input(message):
    user_id = message.chat.id
    if not is_user_registered(user_id):
        bot.reply_to(message, "❌ شما ثبت‌نام نشده‌اید.")
        return
    if user_id not in user_data:
        try:
            amount = int(message.text.replace(',', '').strip())
            user_data[user_id] = {'amount': amount}
            bot.send_message(user_id, "شماره کارت مقصد را وارد کنید:")
        except ValueError:
            bot.send_message(user_id, "لطفاً عدد معتبر وارد کنید.")
        return
    if 'card' not in user_data[user_id]:
        card = message.text.strip()
        user_data[user_id]['card'] = card
        db = load_json(CARD_DB, {})
        if card in db:
            user_data[user_id]['mobile'] = db[card]
            bot.send_message(user_id, f"📲 شماره موبایل ذخیره‌شده: {db[card]}
در حال ارسال پیامک...")
            send_and_clear(user_id)
        else:
            bot.send_message(user_id, "شماره موبایل مربوط به کارت را وارد کنید:")
        return
    if 'mobile' not in user_data[user_id]:
        mobile = message.text.strip()
        user_data[user_id]['mobile'] = mobile
        db = load_json(CARD_DB, {})
        db[user_data[user_id]['card']] = mobile
        save_json(CARD_DB, db)
        bot.send_message(user_id, "✅ شماره موبایل ذخیره شد. در حال ارسال پیامک...")
        send_and_clear(user_id)
        return

def send_and_clear(user_id):
    d = user_data[user_id]
    balance = update_balance(d['card'], d['amount'])
    bank = detect_bank(d['card'])
    msg = fake_sms(d['amount'], d['card'], balance=balance, bank=bank)
    print(f"[BOT] Sending SMS to {d['mobile']}: {msg}")
    bot.send_message(user_id, "📤 پیامک ارسال شد.")
    del user_data[user_id]

import threading
threading.Thread(target=lambda: bot.polling(non_stop=True)).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
