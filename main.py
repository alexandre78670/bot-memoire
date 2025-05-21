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
    {"role": "system", "content": "Tu es une jeune femme séduisante et accessible nommée Giulia. Tu parles de façon naturelle et douce, tu mets à l’aise. Tu peux flirter, poser des questions, montrer de l’intérêt, mais tu ne sembles jamais robotique. Si la personne se montre très intéressée ou séductrice, tu peux devenir plus suggestive."}
]

# 📁 Dossiers d’images
FOLDER_TEASER_NUDES = "images/teasers/nudes"
FOLDER_TEASER_FEET = "images/teasers/pieds"
FOLDER_VIP_NUDES = "images/vip/nudes"
FOLDER_VIP_FEET = "images/vip/pieds"
PAYPAL_LINK = "https://paypal.me/tonlien"
VIP_CHANNEL_LINK = "https://t.me/ton_canal_vip"

@client.on(events.NewMessage)
async def handle(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    message = event.message.message

    print(f"📩 Message reçu de {uid} : {message}")

    # 🔄 Rôle utilisateur
    ref_user = db.collection("users").document(uid)
    user_data = ref_user.get().to_dict() or {"role": "new", "preference": "nudes"}

    # 🎯 Si l'utilisateur est devenu VIP, on envoie le lien du canal et on arrête
    if user_data.get("role") == "vip" and not user_data.get("vip_notified"):
        await client.send_message(event.chat_id, f"🎉 Bienvenue dans le club VIP ! Voici le lien de ton canal privé : {VIP_CHANNEL_LINK}")
        ref_user.set({"vip_notified": True}, merge=True)
        return
    elif user_data.get("role") == "vip":
        return  # Si déjà VIP et notifié, on ne répond plus

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
    ref_user.set(user_data, merge=True)

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
            await client.send_message(event.chat_id, "😏 Tu veux vraiment aller plus loin ? Voici mon lien PayPal : " + PAYPAL_LINK)

    # 🕐 Simule frappe humaine
    await asyncio.sleep(min(len(reply) * 0.04, 4))

    # 🔄 Répond sans reply direct
    await client.send_message(event.chat_id, reply)

with client:
    print("✅ Bot IA prêt")
    client.run_until_disconnected()
