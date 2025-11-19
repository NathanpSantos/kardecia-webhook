import requests

url = "https://graph.facebook.com/v19.0/847623808439866/messages"

headers = {
    "Authorization": "Bearer EAAV2Hie05ZCMBP3halr6AlXhwSUItg1uX07MnzKrI40mD6cshRHQVVQ4AQpqlfrjaHy6eLvs7em4EYlZCAuZC1Y6sYnqBAguHISGaWTBIZArsQZCUK8BI9DYGXiyHIiOzgW5FyDX9JXcwfa0HAo7dCCv0UjUoZBw9ZADjjH6SXQzTZBlPwK0KjIMWjh8XZCYd6KdGB1f1mNcy8nYmJOSrAP9TZCtXwymLDD1ngVkQyd66Rv1exApts6BZAp7l79g0rJfcYt8yEh9tSpKGgFzzKDZBHIumeRKv190EpDZAH7EoOQZDZD",
    "Content-Type": "application/json",
}

data = {
    "messaging_product": "whatsapp",
    "to": "5511998566270",  # seu número
    "text": {
        "body": "Olá! Sou a KARDECIA 😊"
    }
}

resp = requests.post(url, json=data, headers=headers)

print("Status code:", resp.status_code)
print("Resposta da API:")
print(resp.text)
