import os
import base64
import json
import asyncio
from telethon import TelegramClient, events
import openai
import firebase_admin
from firebase_admin import credentials, firestore

# 🔐 Recréer le fichier .session
session_data = os.environ.get("giulia.session")
if session_data:
    with open("giulia.session", "wb") as f:
        f.write(base64.b64decode(session_data))

# 🔑 Config API
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
openai.api_key = os.environ["OPENAI_API_KEY"]

# 🔥 Auth Firebase (version base64-safe)
cred_data = base64.b64decode(os.environ["GOOGLE_CREDENTIALS"])
with open("firebase_key.json", "wb") as f:
    f.write(cred_data)

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🚀 Client Telegram avec session locale
client = TelegramClient("giulia.session", api_id, api_hash)

@client.on(events.NewMessage)
async def handle(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    message = event.message.message

    print(f"📩 Message reçu de {uid} : {message}")

    # 🔄 Récupère la mémoire de l'utilisateur
    ref = db.collection("conversations").document(uid)
    memory = ref.get().to_dict() or {"messages": []}

    memory["messages"].append({"role": "user", "content": message})

    # 🤖 Requête à OpenAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=memory["messages"]
    )

    reply = response["choices"][0]["message"]["content"]
    memory["messages"].append({"role": "assistant", "content": reply})

    # 💾 Sauvegarde la mémoire
    ref.set(memory)

    # 🕐 Simule une frappe humaine
    await asyncio.sleep(min(len(reply) * 0.04, 4))

    await event.reply(reply)

with client:
    print("✅ Bot IA prêt")
    client.run_until_disconnected()
