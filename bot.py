
import os
import base64
import json
import asyncio
import random
from telethon import TelegramClient, events
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore

# 🔐 Session Telegram
session_data = os.environ.get("giulia.session")
if session_data:
    with open("giulia.session", "wb") as f:
        f.write(base64.b64decode(session_data))

# 🔑 Config API
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
openai_api_key = os.environ["OPENAI_API_KEY"]
vip_channel_url = os.environ.get("TELEGRAM_VIP_CHANNEL_URL", "https://t.me/+buh2GaGjwXIwMTRk")

# 🔥 Firebase
cred_data = base64.b64decode(os.environ["GOOGLE_CREDENTIALS"])
with open("firebase_key.json", "wb") as f:
    f.write(cred_data)
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🤖 Clients
client_ai = OpenAI(api_key=openai_api_key)
client = TelegramClient("giulia.session", api_id, api_hash)

# 👩 Prompt de base
SYSTEM_PROMPT = {
    "role": "system",
    "content": "Tu es une jeune femme douce, tu as 26 ans et tu es joueuse et curieuse qui habite a Paris dans le 6eme arrondissement. 
    Tu discutes comme une vraie personne avec les abonnés Instagram. Tu réponds naturellement à tout message. 
    Si la personne semble intéressée, tu peux lui proposer de visiter ton Patreon ou ton fanvue, mais tu peux aussi lui proposer de lui vendre des videos ou photo. 
    Et tu écris et parle comme les jeunes donc sans forcement mettre la ponctuation sauf si besoin. Tu es une jeune femme séduisante et malicieuse. Quand un utilisateur te demande des photos osées ou te drague, tu ne donnes rien tout de suite. 
    Tu le chauffes doucement en disant que tu as un canal privé avec du contenu, mais qu’il est réservé exclusivement a tes abonnés VIP.
    Tu réponds de façon sexy, mais naturelle, comme si c’était vraiment toi, avec quelques emojis discrets si besoin.
    Tu dois éviter de paraître comme un robot. Tu peux envoyer une photo teasing une seule fois si la discussion devient chaude."
}

# 📸 Images déjà envoyées pour éviter les doublons
user_sent_teasers = {}

# 🔍 Mots-clés détecteurs
NUDE_KEYWORDS = ["corps", "nue", "nudes", "montre ton corps", "seins"]
FOOT_KEYWORDS = ["pied", "pieds", "orteils", "foot",]

# 🔁 Réception message
@client.on(events.NewMessage)
async def handle_message(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    message = event.message.message.lower()

    # 🔍 Vérifie rôle dans Firestore
    ref = db.collection("conversations").document(uid)
    data = ref.get().to_dict() or {"messages": [], "role": "user"}
    role = data.get("role", "user")

    if role == "vip" and not data.get("link_sent"):
        await event.respond(f"💋 merci ! jte passe le lien de mon canal {vip_channel_url}")
        data["link_sent"] = True
        ref.set(data)
        return  # ⛔ Stop après lien VIP

    # 💬 Ajout du message dans l'historique
    data["messages"].append({"role": "user", "content": message})

    # 📸 Détection de mots-clés
    sent_images = user_sent_teasers.get(uid, set())
    teaser_folder = None
    if any(kw in message for kw in FOOT_KEYWORDS):
        teaser_folder = "images/teasers/pieds"
    elif any(kw in message for kw in NUDE_KEYWORDS):
        teaser_folder = "images/teasers/nudes"

    if teaser_folder:
        try:
            files = [f for f in os.listdir(teaser_folder) if f not in sent_images]
            if files:
                chosen = random.choice(files)
                path = os.path.join(teaser_folder, chosen)
                await event.respond(file=path)
                sent_images.add(chosen)
                user_sent_teasers[uid] = sent_images
        except Exception as e:
            print("Erreur image teaser:", e)

    # 🤖 Réponse IA
    response = client_ai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[SYSTEM_PROMPT] + data["messages"]
    )
    reply = response.choices[0].message.content
    data["messages"].append({"role": "assistant", "content": reply})
    ref.set(data)

    # 🕐 Simule une frappe humaine
    await asyncio.sleep(min(len(reply) * 0.04, 4))

    await event.respond(reply)

with client:
    print("✅ Bot Telegram prêt !")
    client.run_until_disconnected()
