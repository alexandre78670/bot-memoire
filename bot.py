
import os
import base64
import json
import asyncio
import random
from telethon import TelegramClient, events
import openai
import firebase_admin
from firebase_admin import credentials, firestore

# 🔐 Recrée le fichier .session depuis la variable encodée
session_data = os.environ.get("giulia.session")
if session_data:
    with open("giulia.session", "wb") as f:
        f.write(base64.b64decode(session_data))

# 🔑 Clés d'API
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
openai.api_key = os.environ["OPENAI_API_KEY"]
vip_channel_url = os.environ.get("TELEGRAM_VIP_CHANNEL_URL", "https://t.me/+buh2GaGjwXIwMTRk")

# 🔥 Firebase
cred_data = base64.b64decode(os.environ["GOOGLE_CREDENTIALS"])
with open("firebase_key.json", "wb") as f:
    f.write(cred_data)
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🤖 Clients
client = TelegramClient("giulia.session", api_id, api_hash)

# 🧠 Prompt IA
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Tu es une jeune femme de 26 ans, douce, séduisante, joueuse et curieuse. "
        "Tu habites à Paris, dans le 6ème arrondissement. "
        "Tu parles comme une vraie personne, pas comme un robot : langage naturel, sans ponctuation rigide, avec un style jeune et détendu. "
        "Tu peux glisser quelques emojis légers si c’est naturel 😊 mais pas trop. "
        "Quand on te drague ou qu'on te demande des photos osées, tu ne donnes rien tout de suite. "
        "Tu chauffes subtilement, tu joues la malice : tu parles de ton canal privé réservé à tes abonnés VIP. "
        "Tu restes mystérieuse et séduisante. "
        "Si la discussion devient chaude, tu peux envoyer UNE seule photo teasing, choisie discrètement. "
        "Ton but : séduire, garder la personne intriguée, et surtout paraître réelle, humaine, attachante. "
        "Tu évites les réponses automatiques ou trop parfaites. Réponds avec fluidité, comme si tu écrivais depuis ton téléphone."
    )
}

# 📁 Mots-clés et images déjà envoyées
user_sent_teasers = {}
NUDE_KEYWORDS = ["corps", "nue", "nudes", "seins", "torse", "sexy"]
FOOT_KEYWORDS = ["pied", "pieds", "orteils", "foot", "toes"]

# 📩 Gestion des messages
@client.on(events.NewMessage)
async def handle(event):
    sender = await event.get_sender()
    uid = str(sender.id)
    msg = event.message.message.strip().lower()

    if not msg:
        return

    ref = db.collection("conversations").document(uid)
    data = ref.get().to_dict() or {"messages": [], "role": "user"}
    role = data.get("role", "user")

    # 💎 VIP : envoie du lien une seule fois puis stop
    if role == "vip" and not data.get("link_sent"):
        await asyncio.sleep(1)
        await event.respond(f"💋 Merci pour ton soutien ! Voici le lien vers mon canal privé : {vip_channel_url}")
        data["link_sent"] = True
        ref.set(data)
        return

    if role == "vip" and data.get("link_sent"):
        return

    # 💬 Historique (on limite à 10 derniers échanges pour éviter surcharge)
    data["messages"].append({"role": "user", "content": msg})
    data["messages"] = data["messages"][-10:]

    # 📸 Teasing image
    sent_images = user_sent_teasers.get(uid, set())
    teaser_folder = None
    if any(k in msg for k in FOOT_KEYWORDS):
        teaser_folder = "images/teasers/pieds"
    elif any(k in msg for k in NUDE_KEYWORDS):
        teaser_folder = "images/teasers/nudes"

    if teaser_folder:
        try:
            files = [f for f in os.listdir(teaser_folder) if f not in sent_images]
            if files:
                chosen = random.choice(files)
                await event.respond(file=os.path.join(teaser_folder, chosen))
                sent_images.add(chosen)
                user_sent_teasers[uid] = sent_images
        except Exception as e:
            print("Erreur envoi image teaser:", e)

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[SYSTEM_PROMPT] + data["messages"]
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        reply = " j'ai pas comrpis ce que tu as dit"
        print("Erreur GPT:", e)

    data["messages"].append({"role": "assistant", "content": reply})
    ref.set(data)

    await asyncio.sleep(min(len(reply) * 0.04, 4))
    await event.respond(reply)

# ✅ Lancement du bot
with client:
    print("✅ Bot Telegram prêt !")
    client.run_until_disconnected()
