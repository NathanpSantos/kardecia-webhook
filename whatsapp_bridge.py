import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI()

# 🔐 Tokens vindos das variáveis de ambiente
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# Segurança: se faltar algum dado, o servidor não sobe
if not TOKEN or not PHONE_ID or not VERIFY_TOKEN:
    raise Exception("❌ Configure WHATSAPP_TOKEN, WHATSAPP_PHONE_ID e VERIFY_TOKEN no ambiente!")


@app.get("/")
async def root():
    return {"status": "running", "msg": "Webhook da IA Kardecia funcionando"}


# 1️⃣ VERIFICAÇÃO (GET)
@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse("Erro de verificação", status_code=403)


# 2️⃣ RECEBER MENSAGEM (POST)
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    print("📩 WEBHOOK RECEBIDO:", data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]

        resposta = gerar_resposta_kardecia(text)
        enviar_whatsapp(sender, resposta)

    except Exception as e:
        print("⚠️ Erro ao processar webhook:", e)

    return JSONResponse({"status": "ok"})


def gerar_resposta_kardecia(msg: str):
    return (
        "✨ Olá! Eu sou a KARDECIA, sua assistente sobre Doutrina Espírita.\n\n"
        f"Você escreveu: *{msg}*\n\n"
        "Em breve responderei com base nas obras e princípios espíritas. 🙏💫"
    )


def enviar_whatsapp(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text},
    }

    r = requests.post(url, json=payload, headers=headers)
    print("📤 Envio WhatsApp:", r.status_code, r.text)
