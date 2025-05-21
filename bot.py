import os
import base64
import asyncio
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

# 🌩 Connexion Firebase
cred = credentials.Certificate(eval(os.environ["GOOGLE_CREDENTIALS"]))
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🚀 Client Telegram
client = TelegramClient("giulia.session", api_id, api_hash)

@client.on(events.NewMessage)
async def handle_message(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    text = event.message.message

    print(f"📨 Message de {uid}: {text}")

    # 💾 Mémoire
    ref = db.collection("conversations").document(uid)
    history = ref.get().to_dict() or {"messages": []}
    history["messages"].append({"role": "user", "content": text})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history["messages"]
    )

    reply = response["choices"][0]["message"]["content"]
    history["messages"].append({"role": "assistant", "content": reply})
    ref.set(history)

    await asyncio.sleep(min(len(reply) * 0.04, 5))
    await event.reply(reply)

# ✅ Démarrage sécurisé
async def main():
    connected = await client.connect()
    if not connected:
        print("❌ Connexion échouée.")
        return

    if not await client.is_user_authorized():
        print("❌ Session Telegram invalide ou absente. Vérifie ton fichier `.session`.")
        return

    print("✅ Bot connecté. En attente de messages...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
