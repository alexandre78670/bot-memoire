import os
import base64
import json
import asyncio
import random
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

# 🔥 Auth Firebase
cred_data = base64.b64decode(os.environ["GOOGLE_CREDENTIALS"])
with open("firebase_key.json", "wb") as f:
    f.write(cred_data)
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🚀 Client Telegram
client = TelegramClient("giulia.session", api_id, api_hash)

# 🎭 Prompt de base
BASE_PROMPT = [
    {"role": "system", "content": "Tu es une jeune femme douce, tu as 26 ans et tu es joueuse et curieuse. Tu discutes comme une vraie personne avec les abonnés Instagram. Tu réponds naturellement à tout message. Si la personne semble intéressée, tu peux lui proposer de visiter ton Patreon ou ton fanvue, mais tu peux aussi lui proposer de lui vendre des videos ou photo. Et tu écris et parle comme les jeunes donc sans forcement mettre la ponctuation sauf si besoin."}
]

# 📁 Dossiers d’images
FOLDER_TEASER_NUDES = "images/teasers/nudes"
FOLDER_TEASER_FEET = "images/teasers/pieds"
FOLDER_VIP_NUDES = "images/vip/nudes"
FOLDER_VIP_FEET = "images/vip/pieds"
PAYPAL_LINK = "https://paypal.me/giuliaMrt865?country.x=FR&locale.x=fr_FR"

@client.on(events.NewMessage)
async def handle(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    message = event.message.message

    print(f"📩 Message reçu de {uid} : {message}")

    # 🔄 Rôle utilisateur
    ref_user = db.collection("users").document(uid)
    user_data = ref_user.get().to_dict() or {"role": "new", "preference": "nudes"}

    # 🔄 Historique conversation
    ref = db.collection("conversations").document(uid)
    memory = ref.get().to_dict() or {"messages": BASE_PROMPT.copy()}

    memory["messages"].append({"role": "user", "content": message})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=memory["messages"]
    )
    reply = response["choices"][0]["message"]["content"]
    memory["messages"].append({"role": "assistant", "content": reply})

    # 💾 Sauvegarde
    ref.set(memory)
    ref_user.set(user_data)

    # 🖼 Envoi image si flirt détecté
    flirt_keywords = ["chaud", "t’as des photos", "t’es sexy", "montre", "envie", "excité", "tu m’excites"]
    flirt_detected = any(word in message.lower() for word in flirt_keywords)

    if flirt_detected and user_data["role"] != "vip":
        folder = FOLDER_TEASER_FEET if user_data["preference"] == "feet" else FOLDER_TEASER_NUDES
        photos = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        sent = db.collection("sent_photos").document(uid).get().to_dict() or {"photos": []}

        to_send = [p for p in photos if p not in sent["photos"]]
        if to_send:
            chosen = random.choice(to_send)
            path = os.path.join(folder, chosen)
            await client.send_file(event.chat_id, path)
            sent["photos"].append(chosen)
            db.collection("sent_photos").document(uid).set(sent)
        else:
            await client.send_message(event.chat_id, "Si tu veux plus de photo ou de video je t'envoie mon paypal c'est 30 euros pour avoir acces a mon groupe télegrame :" + PAYPAL_LINK)

    # 🕐 Simule frappe humaine
    await asyncio.sleep(min(len(reply) * 0.04, 4))

    # 🔄 Répond sans reply direct
    await client.send_message(event.chat_id, reply)

with client:
    print("✅ Bot IA prêt")
    client.run_until_disconnected()
