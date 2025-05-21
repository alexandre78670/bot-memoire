import os
import base64
from telethon import TelegramClient, events
import openai
import firebase_admin
from firebase_admin import credentials, firestore

# 🔐 Recréer le fichier session
session_data = os.environ.get("giulia.session")
if session_data:
    with open("giulia.session", "wb") as f:
        f.write(base64.b64decode(session_data))

# 📲 Config API
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
openai.api_key = os.environ["OPENAI_API_KEY"]

# 🌩 Connexion Firestore
cred = credentials.Certificate(eval(os.environ["GOOGLE_CREDENTIALS"]))
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🚀 Lancer le client Telegram
client = TelegramClient("giulia.session", api_id, api_hash)

# ✍️ Ajouter un délai pour simuler un humain
import asyncio

@client.on(events.NewMessage)
async def handle_message(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    text = event.message.message

    print(f"📨 Nouveau message de {uid}: {text}")

    # 🔁 Récupère mémoire existante
    ref = db.collection("conversations").document(uid)
    history = ref.get().to_dict() or {"messages": []}

    history["messages"].append({"role": "user", "content": text})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history["messages"]
    )

    reply = response["choices"][0]["message"]["content"]
    history["messages"].append({"role": "assistant", "content": reply})

    # 💾 Sauvegarde mémoire
    ref.set(history)

    # 🕐 Simule une frappe humaine
    await asyncio.sleep(min(len(reply) * 0.04, 5))

    await event.reply(reply)

with client:
    print("✅ Bot IA Telegram prêt !")
    client.run_until_disconnected()
