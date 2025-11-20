import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI()

# 🔐 Pegando dados das variáveis de ambiente
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")   # ex: 847623808439866
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")    # ex: kardecia_token

if not TOKEN or not PHONE_ID or not VERIFY_TOKEN:
    raise RuntimeError("Configure as variáveis de ambiente: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, VERIFY_TOKEN")


@app.get("/")
async def root():
    return {"status": "ok", "msg": "KARDECIA webhook rodando"}


# 1️⃣ VERIFICAÇÃO DO WEBHOOK (GET)
@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse(content="Erro de verificação", status_code=403)


# 2️⃣ RECEBER MENSAGENS (POST)
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    print("📩 WEBHOOK RECEBIDO:")
    print(data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]

        # 🟦  NOVO: Detecta primeira mensagem e envia mensagem inicial
        texto = text.lower().strip()
        saudacoes = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "ei", "hey", "eai", "e aí"]

        if texto in saudacoes:
            mensagem_inicial = (
                "✨ Olá! Eu sou a *KARDECIA IA*.\n"
                "Estou aqui para te ajudar com temas da *Doutrina Espírita*, estudos, reflexões, acolhimento e respostas baseadas nas obras fundamentais do Espiritismo.\n\n"
                "Como posso te ajudar hoje? 🙏💫"
            )
            enviar_whatsapp(sender, mensagem_inicial)
            print("💬 Mensagem inicial enviada")
            return JSONResponse(content={"status": "ok"})

        # 🟩 Fluxo normal de resposta
        resposta = gerar_resposta_kardecia(text)
        enviar_whatsapp(sender, resposta)
        print(f"✅ Resposta enviada para {sender}")

    except Exception as e:
        print("⚠️ Erro ao processar mensagem:", e)

    return JSONResponse(content={"status": "ok"})


def gerar_resposta_kardecia(msg: str) -> str:
    return (
        "✨ Olá! Eu sou a KARDECIA, sua assistente sobre Doutrina Espírita.\n\n"
        f"Você me escreveu: *{msg}*\n\n"
        "Em breve responderei com base nas obras espíritas. 🙏💫"
    )


def enviar_whatsapp(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text},
    }

    resp = requests.post(url, json=data, headers=headers)
    print("📤 Resposta da API do WhatsApp:", resp.status_code, resp.text)
