import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from openai import OpenAI

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# 🔐 Tokens vindos do ambiente
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

if not TOKEN or not PHONE_ID or not VERIFY_TOKEN:
    raise RuntimeError("Configure as variáveis de ambiente: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, VERIFY_TOKEN")


@app.get("/")
async def root():
    return {"status": "ok", "msg": "Kardecia webhook rodando"}


# --------------------------------------
# 1️⃣ VERIFICAÇÃO DO WEBHOOK (GET)
# --------------------------------------
@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse("Erro de verificação", status_code=403)


# --------------------------------------
# 2️⃣ RECEBER MENSAGENS (POST)
# --------------------------------------
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    print("📩 WEBHOOK RECEBIDO:")
    print(data)

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]

        texto = text.lower().strip()
        saudacoes = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "ei", "hey", "eai", "e aí"]

        # 🟦 Mensagem inicial da Kardecia
        if texto in saudacoes:
            mensagem_inicial = (
                "✨ Olá! Eu sou a *KARDECIA IA*.\n"
                "Estou aqui para te ajudar com temas da *Doutrina Espírita*, reflexões, estudos e acolhimento.\n\n"
                "Como posso te ajudar hoje? 🙏💫"
            )
            enviar_whatsapp(sender, mensagem_inicial)
            return JSONResponse({"status": "ok"})

        # 🟩 Fluxo normal de resposta (ChatGPT)
        resposta = gerar_resposta_kardecia(text)
        enviar_whatsapp(sender, resposta)
        print(f"✅ Resposta enviada para {sender}")

        # 🟧 Se o usuário pedir áudio
        if "áudio" in texto or "audio" in texto:
            audio_path = gerar_audio_kardecia(resposta)
            if audio_path:
                enviar_audio_whatsapp(sender, audio_path)
                print("🔊 Áudio enviado com sucesso!")
            return JSONResponse({"status": "ok"})

    except Exception as e:
        print("⚠️ Erro ao processar mensagem:", e)

    return JSONResponse({"status": "ok"})


# --------------------------------------
# 🔮  IA — Resposta da Kardecia (ChatGPT)
# --------------------------------------
def gerar_resposta_kardecia(msg: str) -> str:
    try:
        prompt = f"""
        Você é a Kardecia IA, uma assistente espiritualista baseada na Doutrina Espírita.
        Responda de forma acolhedora, calma e esclarecedora.
        Evite previsões e adivinhações.
        Usuário perguntou: {msg}
        """

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é a Kardecia IA, guia espiritualista e acolhedora."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print("🚨 Erro no ChatGPT:", e)
        return "Desculpe, estou com dificuldades para responder no momento. Tente novamente mais tarde 🙏"


# --------------------------------------
# 🔊 Gerar ÁUDIO da Kardecia
# --------------------------------------
def gerar_audio_kardecia(texto: str):
    try:
        audio = openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=texto
        )

        audio_bytes = audio.read()
        audio_path = "/tmp/kardecia_audio.ogg"

        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        return audio_path

    except Exception as e:
        print("❌ Erro ao gerar áudio:", e)
        return None


# --------------------------------------
# 🎤 Enviar ÁUDIO pelo WhatsApp
# --------------------------------------
def enviar_audio_whatsapp(to: str, audio_path: str):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
    }

    with open(audio_path, "rb") as audio_file:
        files = {"audio": audio_file}
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "audio",
            "audio": {"filename": "kardecia.ogg"}
        }

        resp = requests.post(url, data=data, files=files, headers=headers)
        print("📤 Envio do áudio:", resp.status_code, resp.text)


# --------------------------------------
# 💬 Enviar TEXTO pelo WhatsApp
# --------------------------------------
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
    print("📤 Resposta enviada:", resp.status_code, resp.text)
