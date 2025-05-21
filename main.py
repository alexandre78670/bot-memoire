import os
import base64
import json
import random
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
api_hash = os.environ["TELEGRAM_API_HASH"])
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
    doc = ref.get().to_dict() or {"messages": []}

    # 📌 Ajouter le prompt système si premier message
    if not doc["messages"]:
        doc["messages"].append({
            "role": "system",
            "content": "Tu es Giulia, une femme sensuelle, douce et séduisante. Tu écris avec naturel, chaleur et un soupçon de mystère. Tu parles comme une vraie personne."
        })

    doc["messages"].append({"role": "user", "content": message})

    # 🎯 Gérer les préférences utilisateur
    if "pied" in message.lower():
        ref.set({"preferences": "pieds"}, merge=True)
    elif "nude" in message.lower() or "corps" in message.lower():
        ref.set({"preferences": "nudes"}, merge=True)

    # 🔥 Si discussion chaude, envoi teaser
    sexy_keywords = ["photo", "chaud", "envie", "te voir", "montre-moi", "j’ai envie", "excite", "nue"]
    if any(kw in message.lower() for kw in sexy_keywords):
        role = doc.get("role", "new")
        pref = doc.get("preferences", "mix")
        seen = doc.get("seen_teasers", [])

        if role != "vip":
            folder = f"images/teasers/{pref}"
            available = [f for f in os.listdir(folder) if f not in seen]
            if available:
                filename = random.choice(available)
                seen.append(filename)
                ref.set({"seen_teasers": seen}, merge=True)
                await event.respond(file=os.path.join(folder, filename))
            else:
                await event.respond("Si tu veux d'autres photos... 🫦 Voici mon PayPal : https://paypal.me/tonlien")
            return
        else:
            folder = f"images/vip/{pref}"
            available = os.listdir(folder)
            if available:
                filename = random.choice(available)
                await event.respond(file=os.path.join(folder, filename))
                return

    # 🤖 Requête à OpenAI (nouvelle version API 1.0)
    from openai import OpenAI
    client_ai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    response = client_ai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=doc["messages"]
    )

    reply = response.choices[0].message.content
    doc["messages"].append({"role": "assistant", "content": reply})

    # 💾 Sauvegarde la mémoire
    ref.set(doc)

    # 🕐 Simule une frappe humaine
    await asyncio.sleep(min(len(reply) * 0.04, 4))

    await event.respond(reply)

with client:
    print("✅ Bot IA prêt")
    client.run_until_disconnected()
