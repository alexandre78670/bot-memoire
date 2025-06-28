
import os
import base64
import asyncio
import random
from telethon import TelegramClient, events, functions, types
import openai
import firebase_admin
from firebase_admin import credentials, firestore

# Initialisation session Telegram
session_data = os.environ.get("giulia.session")
if session_data:
    with open("giulia.session", "wb") as f:
        f.write(base64.b64decode(session_data))

# API keys et config
api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
openai.api_key = os.environ["OPENAI_API_KEY"]
paypal_link = os.environ.get("PAYPAL_LINK", "https://www.paypal.me/giuliaVIP")
vip_channel_url = os.environ.get("TELEGRAM_VIP_CHANNEL_URL", "https://t.me/+vip-link-example")

# Firebase
cred_data = base64.b64decode(os.environ["GOOGLE_CREDENTIALS"])
with open("firebase_key.json", "wb") as f:
    f.write(cred_data)
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Teasing
NUDE_KEYWORDS = ["nude", "corps", "photo", "seins", "sexy"]
FOOT_KEYWORDS = ["pieds", "pied", "foot", "orteils"]
TRIGGER_KEYWORDS = NUDE_KEYWORDS + FOOT_KEYWORDS + ["lien", "abonnement", "payer", "pay", "vip"]
user_sent_teasers = {}

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Tu t'appelles Giulia Moretti, t'as 26 ans, t’es douce et joueuse et tu vis à Paris dans le 6eme 😘 "
        "Tu parles comme une vraie meuf, style jeune, genre insta ou snap, sans ponctuation rigide et t’utilises quelques emojis de temps en temps. "
        "T’es séduisante mais naturelle. Quand on te chauffe ou qu’on veut des photos, tu réponds avec malice, tu chauffes un peu, "
        "et si la discussion devient chaude, tu peux lâcher UNE seule photo teasing. "
        "Tu parles d’un canal privé réservé à tes VIP. Quand tu sens que l’utilisateur est bien chaud, tu proposes le lien PayPal à 30€. "
        "Une fois payé (rôle VIP), tu donnes le lien du canal Telegram et tu parles plus après ça."
    )
}

client = TelegramClient("giulia.session", api_id, api_hash)

@client.on(events.NewMessage)
async def handle(event):
    try:
        sender = await event.get_sender()
        uid = str(sender.id)
        msg = event.message.message.strip().lower()
        if not msg:
            return

        ref = db.collection("conversations").document(uid)
        data = ref.get().to_dict() or {"messages": [], "role": "user"}
        role = data.get("role", "user")

        if role == "vip" and not data.get("link_sent"):
            await event.respond(f"💋 Merci pour ton soutien ! Voilà le lien de mon canal VIP : {vip_channel_url}")
            data["link_sent"] = True
            ref.set(data)
            return
        if role == "vip":
            return

        data["messages"].append({"role": "user", "content": msg})
        data["messages"] = data["messages"][-10:]

        await client(functions.messages.SetTypingRequest(
            peer=event.chat_id,
            action=types.SendMessageTypingAction()
        ))

        folder = None
        if any(k in msg for k in FOOT_KEYWORDS):
            folder = "images/teasers/pieds"
        elif any(k in msg for k in NUDE_KEYWORDS):
            folder = "images/teasers/nudes"

        sent = user_sent_teasers.get(uid, set())
        if folder:
            try:
                files = [f for f in os.listdir(folder) if f not in sent]
                if files:
                    chosen = random.choice(files)
                    await event.respond(file=os.path.join(folder, chosen))
                    sent.add(chosen)
                    user_sent_teasers[uid] = sent
            except Exception as e:
                print("Erreur teaser:", e)

        reply = None
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[SYSTEM_PROMPT] + data["messages"],
                temperature=0.8
            )
            reply = response["choices"][0]["message"]["content"].strip()
            if any(x in reply.lower() for x in ["je suis désolée", "je suis un modèle", "je suis une intelligence"]):
                reply = None
        except Exception as e:
            print("GPT error:", e)
            reply = None

        if not reply or len(reply.strip()) < 2:
            reply = "t’es chelou mdr j’ai pas compris ce que tu voulais dire 😂"

        if not data.get("paypal_sent"):
            triggers = sum(1 for m in data["messages"] if m["role"] == "user" and any(k in m["content"] for k in TRIGGER_KEYWORDS))
            if triggers >= 2:
                reply += reply += f"\n\nTu me plais toi 😏 Si tu veux voir un peu plus… j’ai un espace VIP 💖 C’est 30€ pour y entrer. Tu veux le lien ?\n💸 {paypal_link}"
                data["paypal_sent"] = True

        data["messages"].append({"role": "assistant", "content": reply})
        ref.set(data)

        await asyncio.sleep(min(len(reply) * 0.05, 6))
        await event.respond(reply)

    except Exception as e:
        print("Erreur générale:", e)

with client:
    print("✅ Bot prêt !")
    client.run_until_disconnected()
