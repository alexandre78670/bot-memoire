from flask import Flask, request, jsonify
from openai import OpenAI
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
