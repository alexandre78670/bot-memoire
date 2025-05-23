import os
import base64
import asyncio
import random
from telethon import TelegramClient, events
import openai
import firebase_admin
from firebase_admin import credentials, firestore

# 🔐 Session Telegram
session_data = os.environ.get("giulia.session")
if session_data:
    with open("giulia.session", "wb") as f:
        f.write(base64.b64decode(session_data))

# 🔑 API keys
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
openai.api_key = os.environ["OPENAI_API_KEY"]
paypal_link = os.environ.get("PAYPAL_LINK", "https://www.paypal.me/giuliaVIP")
vip_channel_url = os.environ.get("TELEGRAM_VIP_CHANNEL_URL", "https://t.me/+vip-link-example")

# 🔥 Firebase
cred_data = base64.b64decode(os.environ["GOOGLE_CREDENTIALS"])
with open("firebase_key.json", "wb") as f:
    f.write(cred_data)
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

client = TelegramClient("giulia.session", api_id, api_hash)

# 👩 Personnalité
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Tu t'appelles Giulia Moretti, tu as 26 ans, tu es douce et joueuse, et tu habites à Paris dans le 6eme arrondissement "
        "Tu parles comme une vraie fille jeune, avec des abréviations, sans ponctuation parfaite, parfois avec quelques emojis. "
        "Tu es séductrice, naturelle, curieuse. Quand on te demande des photos osées, tu chauffes un peu pour ensuite donner une photo teaser. "
        "Tu mentionnes ton canal VIP réservé à ceux qui te soutiennent. "
        "Si tu sens que l'utilisateur est prêt, tu proposes le lien PayPal (30€). "
        "Après paiement (confirmé par admin), tu envoies le lien du canal Telegram et tu arrêtes de parler."
    )
}

user_sent_teasers = {}
NUDE_KEYWORDS = ["nude", "corps", "photo", "seins", "sexy"]
FOOT_KEYWORDS = ["pieds", "pied", "foot", "orteils"]
TRIGGER_KEYWORDS = NUDE_KEYWORDS + FOOT_KEYWORDS + ["lien", "abonnement", "payer", "pay", "VIP"]

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
    data["messages"].append({"role": "user", "content": msg})
    data["messages"] = data["messages"][-10:]

    # Envoi lien VIP
    if role == "vip" and not data.get("link_sent"):
        await event.respond(f"💋 Merci pour ton soutien ! Voilà le lien de mon canal VIP : {vip_channel_url}")
        data["link_sent"] = True
        ref.set(data)
        return

    if role == "vip" and data.get("link_sent"):
        return

    # Détection teaser
    sent = user_sent_teasers.get(uid, set())
    folder = None
    if any(k in msg for k in FOOT_KEYWORDS):
        folder = "images/teasers/pieds"
    elif any(k in msg for k in NUDE_KEYWORDS):
        folder = "images/teasers/nudes"

    if folder:
        try:
            files = [f for f in os.listdir(folder) if f not in sent]
            if files:
                chosen = random.choice(files)
                await event.respond(file=os.path.join(folder, chosen))
                sent.add(chosen)
                user_sent_teasers[uid] = sent
        except Exception as e:
            print("Erreur envoi teaser:", e)

    # Réponse IA
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[SYSTEM_PROMPT] + data["messages"]
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        reply = "jai pas compris haha tu peux m'expliquer ?"
        print("Erreur GPT:", e)

    # Logique vente : conditions
    if not data.get("paypal_sent"):
        if sum(1 for m in data["messages"] if m["role"] == "user" and any(k in m["content"] for k in TRIGGER_KEYWORDS)) >= 2:
            reply += f"

Si tu veux voir un peu plus... j’ai un espace VIP 💖 c’est 30€ pour y entrer
Voici le lien : {paypal_link}"
            data["paypal_sent"] = True

    data["messages"].append({"role": "assistant", "content": reply})
    ref.set(data)

    await asyncio.sleep(min(len(reply) * 0.04, 4))
    await event.respond(reply)

with client:
    print("✅ Bot Telegram prêt !")
    client.run_until_disconnected()
