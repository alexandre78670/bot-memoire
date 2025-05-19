from flask import Flask, request, jsonify
import openai
import firebase_admin
from firebase_admin import credentials, firestore
import os

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/message', methods=['POST'])
def chat():
    data = request.get_json()
    user_id = data.get("user_id")
    message = data.get("message")

    doc_ref = db.collection("conversations").document(user_id)
    doc = doc_ref.get()
    doc_data = doc.to_dict() if doc.exists else {}
    history = doc_data.get("history", "")

    prompt = f"""Voici la conversation jusqu'à présent avec {user_id} :

{history}

Nouveau message de l'utilisateur : {message}

Réponds naturellement, en continuant cette discussion comme une personne réelle."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"error": "Erreur lors de l'appel à OpenAI", "details": str(e)}), 500

    new_history = history + f"\nUtilisateur : {message}\nBot : {reply}"
    doc_ref.set({"history": new_history})

    return jsonify({"reply": reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
