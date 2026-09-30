import os
import sqlite3
import telebot
from telebot import types

# 1. Telegram Bot Token load karna (Replit Secrets se)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN Secrets me nahi mila! Kripya ise add karein.")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# 2. SQLite Database Setup (Scores aur Users save karne ke liye)
def init_db():
    conn = sqlite3.connect('quiz_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            score INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 3. Quiz ke Sawal aur Jawab (Aap yahan aur sawal jod sakte hain)
QUIZ_QUESTIONS = [
    {
        "question": "Python me single-line comment ke liye kaun sa symbol use hota hai?",
        "options": ["//", "#", "/*", "<!--"],
        "correct": 1  # Index 1 yaani '#' sahi hai
    },
    {
        "question": "Telegram kis year me launch hua tha?",
        "options": ["2010", "2012", "2013", "2015"],
        "correct": 2  # Index 2 yaani '2013' sahi hai
    },
    {
        "question": "Inme se kaun sa ek Data Type nahi hai?",
        "options": ["String", "Integer", "Loop", "Boolean"],
        "correct": 2  # Index 2 yaani 'Loop' sahi hai
    }
]

# Temporary memory users ki current state track karne ke liye
user_current_quiz = {}

# 4. Commands Handling
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Welcome to the Quiz Bot!\n\n"
        "Aap niche diye gaye commands use kar sakte hain:\n"
        "🎲 /quiz - Quiz shuru karne ke liye\n"
        "📊 /score - Apna current score dekhne ke liye\n"
        "🏆 /leaderboard - Top scorers dekhne ke liye\n"
        "❓ /help - Help pane ke liye"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['score'])
def check_score(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('quiz_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    score = row[0] if row else 0
    bot.reply_to(message, f"📊 Aapka total score hai: *{score}* points!", parse_mode="Markdown")

@bot.message_handler(commands=['leaderboard'])
def show_leaderboard(message):
    conn = sqlite3.connect('quiz_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, score FROM users ORDER BY score DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        bot.reply_to(message, "🏆 Abhi leaderboard khali hai. Pehle quiz kheliye!")
        return
        
    leaderboard_text = "🏆 *Top 5 Players:*\n\n"
    for i, row in enumerate(rows, start=1):
        username = row[0] if row[0] else "Anonymous"
        leaderboard_text += f"{i}. @{username} — {row[1]} pts\n"
        
    bot.reply_to(message, leaderboard_text, parse_mode="Markdown")

@bot.message_handler(commands=['quiz'])
def start_quiz(message):
    user_id = message.from_user.id
    # User ko pehle sawal se shuru karwana
    user_current_quiz[user_id] = 0
    send_question(user_id, message.chat.id)

def send_question(user_id, chat_id):
    q_index = user_current_quiz.get(user_id, 0)
    
    if q_index >= len(QUIZ_QUESTIONS):
        bot.send_message(chat_id, "🎉 Badhai ho! Aapne quiz ke saare sawal poore kar liye hain. Naya score dekhne ke liye /score dabayein.")
        if user_id in user_current_quiz:
            del user_current_quiz[user_id]
        return

    q_data = QUIZ_QUESTIONS[q_index]
    
    # Buttons banana options ke liye
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, option in enumerate(q_data["options"]):
        callback_data = f"quiz_{q_index}_{idx}"
        button = types.InlineKeyboardButton(text=option, callback_data=callback_data)
        markup.add(button)
        
    bot.send_message(chat_id, f"❓ *Sawal {q_index + 1}:* {q_data['question']}", reply_markup=markup, parse_mode="Markdown")

# 5. Buttons ke Click/Answer ko handle karna
@bot.callback_query_handler(func=lambda call: call.data.startswith('quiz_'))
def handle_quiz_answer(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    username = call.from_user.username
    
    # Callback data se question index aur selected option nikalna
    _, q_index_str, selected_idx_str = call.data.split('_')
    q_index = int(q_index_str)
    selected_idx = int(selected_idx_str)
    
    # Chek karna ki user usi sawal par hai ya purana button daba raha hai
    if user_current_quiz.get(user_id) != q_index:
        bot.answer_callback_query(call.id, "Yeh purana sawal hai ya quiz khatam ho chuki hai!", show_alert=True)
        return

    q_data = QUIZ_QUESTIONS[q_index]
    correct_idx = q_data["correct"]
    
    if selected_idx == correct_idx:
        # Sahi jawab: Database me score 10 point badhana
        conn = sqlite3.connect('quiz_bot.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, username, score) VALUES (?, ?, 10) ON CONFLICT(user_id) DO UPDATE SET score = score + 10, username = ?", (user_id, username, username))
        conn.commit()
        conn.close()
        
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"✅ *Sahi Jawab!* (+10 Points)\n\nSawal: {q_data['question']}\n\nAapne chuna: {q_data['options'][selected_idx]}", parse_mode="Markdown")
    else:
        # Galat jawab
        sahi_option = q_data["options"][correct_idx]
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=f"❌ *Galat Jawab!*\n\nSawal: {q_data['question']}\n\nAapne chuna: {q_data['options'][selected_idx]}\nSahi jawab tha: {sahi_option}", parse_mode="Markdown")

    # Agle sawal par jana
    user_current_quiz[user_id] = q_index + 1
    send_question(user_id, chat_id)
    bot.answer_callback_query(call.id)

# Bot ko shuru karna
print("🤖 Bot successfully start ho gaya hai...")
bot.infinity_polling()
  
