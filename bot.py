from telethon import TelegramClient, events
import firebase_admin
from firebase_admin import credentials, firestore
import openai
import os
import asyncio
import time

# Clés d’environnement depuis Render
api_id = int(os.environ.get("TELEGRAM_API_ID"))
api_hash = os.environ.get("TELEGRAM_API_HASH")
session_name = "giulia"
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Authentification Firebase
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

client = TelegramClient(session_name, api_id, api_hash)

@client.on(events.NewMessage(incoming=True))
async def handle_message(event):
    user_id = str(event.sender_id)
    user_input = event.raw_text

    # Récupérer l’historique de conversation
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        history = doc.to_dict().get("history", [])
    else:
        history = []

    history.append({"role": "user", "content": user_input})

    # Appel à OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history
    )
    reply = response["choices"][0]["message"]["content"]

    history.append({"role": "assistant", "content": reply})
    doc_ref.set({"history": history})

    # Délai simulé (comme un humain)
    await asyncio.sleep(min(len(reply) * 0.02, 3.5))
    await event.respond(reply)

print("Bot IA Telegram prêt.")
client.start()
client.run_until_disconnected()
