import os
import base64
import json
import asyncio
from telethon import TelegramClient, events
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore

# 🔐 Recréer le fichier .session depuis l'environnement
session_data = os.environ.get("giulia.session")
if session_data:
    with open("giulia.session", "wb") as f:
        f.write(base64.b64decode(session_data))

# 🔑 Clés d’API
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
openai_api_key = os.environ["OPENAI_API_KEY"]

# 🔥 Authentification Firebase avec clé encodée en base64
cred_data = base64.b64decode(os.environ["GOOGLE_CREDENTIALS"])
with open("firebase_key.json", "wb") as f:
    f.write(cred_data)

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🤖 Client OpenAI
client_ai = OpenAI(api_key=openai_api_key)

# 🚀 Client Telegram
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

    try:
        response = client_ai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=memory["messages"]
        )
        reply = response.choices[0].message.content

        memory["messages"].append({"role": "assistant", "content": reply})

        # 💾 Sauvegarde en base
        ref.set(memory)

        # ⏳ Délai humain
        await asyncio.sleep(min(len(reply) * 0.04, 4))
        await event.reply(reply)

    except Exception as e:
        print("❌ Erreur OpenAI :", e)
        await event.reply("Erreur de traitement, réessaie plus tard.")

with client:
    print("✅ Bot IA Telegram prêt !")
    client.run_until_disconnected()
