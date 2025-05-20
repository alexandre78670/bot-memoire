import os
import json
import time
import openai
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Firebase setup
cred = credentials.Certificate(json.loads(os.getenv("GOOGLE_CREDENTIALS")))
firebase_admin.initialize_app(cred)
db = firestore.client()

# OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Fonction de réponse IA
async def respond(user_id: str, message: str) -> str:
    doc_ref = db.collection("conversations").document(user_id)
    doc = doc_ref.get()
    history = doc.to_dict()["history"] if doc.exists else ""

    prompt = f"""
Tu es une fille réelle qui discute naturellement avec la personne.
Historique :
{history}

Nouveau message : {message}
Réponds de façon humaine et naturelle.
"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response.choices[0].message.content.strip()
    doc_ref.set({"history": history + f"\n👤: {message}\n🤖: {reply}"})
    return reply

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salut ! Tu peux m’écrire ici quand tu veux 😘")

# Réponses normales
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    message = update.message.text
    reply = await respond(user_id, message)

    # Simule un temps d’écriture
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    time.sleep(2)  # tu peux augmenter jusqu'à 5 secondes

    await update.message.reply_text(reply)

# Lancer le bot
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot started polling…")
app.run_polling()
