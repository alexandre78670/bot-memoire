from flask import Flask, request, jsonify
from openai import OpenAI
from flask import Flask, request
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Initialiser Flask
app = Flask(__name__)

# Clé API OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialiser Firebase
cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/message', methods=['POST'])
def chat():
    data = request.get_json()
    user_id = data.get("user_id")
    message = data.get("message")

    if not user_id or not message:
        return jsonify({"error": "Champs manquants"}), 400

    # Récupérer l'historique utilisateur
    doc_ref = db.collection("conversations").document(user_id)
    doc = doc_ref.get()
    history = doc.to_dict()["history"] if doc.exists else ""

    prompt = f"""
Voici la conversation jusqu'à présent avec {user_id} :

{history}

Nouveau message de l'utilisateur : {message}

Réponds naturellement, en continuant cette discussion comme une personne réelle.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"error": "Erreur lors de l'appel à OpenAI", "details": str(e)}), 500

    # Sauvegarder l'historique mis à jour
    new_history = history + f"\nUtilisateur : {message}\nBot : {reply}"
    doc_ref.set({"history": new_history})

    return jsonify({"reply": reply})


# Lancer le serveur
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)

@app.route('/users', methods=['GET'])
def get_users():
    docs = db.collection("conversations").stream()
    users = []
    for doc in docs:
        data = doc.to_dict()
        users.append({"id": doc.id, "history": data.get("history", "")})
    return jsonify({"users": users})


app = Flask(__name__)

VERIFY_TOKEN = "mon_token_secret_instagram"

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook vérifié !")
        return challenge, 200
    else:
        return "Erreur de vérification", 403

@app.route("/webhook", methods=["POST"])
def handle_message():
    data = request.get_json()
    print("Données reçues :", data)
    # (Ici, tu peux ajouter une réponse automatique si besoin)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
