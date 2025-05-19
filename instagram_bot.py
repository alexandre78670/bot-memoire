import requests
import os

# Ton token d’accès longue durée ici
ACCESS_TOKEN = "EAAPN5Kov7ZAoBO5lyP2gSP5KUx3u3IOrb2A241ZCLeInLTWJhZBDeXwLk1M0zhEZCWNZCog7Et7tHBxVTZACqr0nJu6wPZCoREUeQTg9MnwfBZBZBUtOaCG4zvgNZCPmI500W9qkKVwnPWjJwZBK0Ek7lMdj1iTDJyT5qt5kmqXrFLD5aZBYdaNwxaDBf9ZCLRARQTK5a"

# ID de ta page Facebook liée à ton compte Instagram
PAGE_ID = "670196569506465"  # à adapter avec ton propre ID si besoin

# Fonction pour envoyer une réponse en DM
def envoyer_dm(recipient_id, message):
    url = f"https://graph.facebook.com/v17.0/{PAGE_ID}/messages"
    params = {
        "access_token": ACCESS_TOKEN
    }
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE"
    }

    response = requests.post(url, params=params, json=data)
    print("Réponse de Meta :", response.status_code, response.text)
