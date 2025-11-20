import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from openai import OpenAI

# 🔐 Inicializa OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🎚️ Preferências dos usuários (modo de resposta)
user_preferences = {}

app = FastAPI()

# 🔐 Variáveis de Ambiente
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

if not TOKEN or not PHONE_ID or not VERIFY_TOKEN:
    raise RuntimeError("❌ Configure WHATSAPP_TOKEN, WHATSAPP_PHONE_ID e VERIFY_TOKEN.")

# 🧠 Memória por usuário
conversation_history = {}

# 📚 PDFs
PDF_LINKS = {
    "livro_dos_espiritos": {
        "name": "O Livro dos Espíritos – Allan Kardec",
        "url": "https://www.febnet.org.br/wp-content/uploads/2012/07/WEB-Livro-dos-Esp%C3%ADritos-Guillon-1.pdf"
    },
    "livro_dos_mediuns": {
        "name": "O Livro dos Médiuns – Allan Kardec",
        "url": "https://www.febnet.org.br/wp-content/uploads/2012/07/WEB-Livro-dos-Mediuns-Guillon-1.pdf"
    },
    "evangelho": {
        "name": "O Evangelho Segundo o Espiritismo",
        "url": "https://www.febnet.org.br/wp-content/uploads/2012/07/WEB-O-Evangelho-segundo-o-Espiritismo-Guillon.pdf"
    },
    "genese": {
        "name": "A Gênese",
        "url": "https://www.febnet.org.br/wp-content/uploads/2012/07/WEB-A-Genese-Guillon.pdf"
    },
    "ceu_inferno": {
        "name": "O Céu e o Inferno",
        "url": "https://www.febnet.org.br/wp-content/uploads/2012/07/WEB-O-Ceu-e-o-inferno-Guillon.pdf"
    },
}

@app.get("/")
async def root():
    return {"status": "ok", "msg": "IA Kardecia rodando!"}


# -------------------------------
# 1️⃣ VERIFICAÇÃO WEBHOOK
# -------------------------------
@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge)

    return PlainTextResponse(content="Erro", status_code=403)


# -------------------------------
# 2️⃣ RECEBER MENSAGENS
# -------------------------------
@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    print("📩 WEBHOOK RECEBIDO:", data)

    try:
        entry = data.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})

        # Ignorar eventos de status
        if "statuses" in value:
            print("🔎 Evento de status ignorado.")
            return {"status": "ignored"}

        messages = value.get("messages", [])
        if not messages:
            print("⚠️ Nenhuma mensagem.")
            return {"status": "ignored"}

        message = messages[0]
        sender = message["from"]
        text = message["text"]["body"]
        texto = text.lower().strip()

        # 🎚️ Modos de resposta
        if texto in ["/curta", "curto", "resposta curta"]:
            user_preferences[sender] = {"modo": "curta"}
            enviar_whatsapp(sender, "✔️ Modo *curto* ativado!")
            return {"status": "ok"}

        if texto in ["/media", "média", "resposta média"]:
            user_preferences[sender] = {"modo": "media"}
            enviar_whatsapp(sender, "✔️ Modo *médio* ativado!")
            return {"status": "ok"}

        if texto in ["/longa", "resposta longa", "detalhada"]:
            user_preferences[sender] = {"modo": "longa"}
            enviar_whatsapp(sender, "✔️ Modo *longo* ativado!")
            return {"status": "ok"}

        # 🟦 Saudações
        saudacoes = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "eai", "ei"]
        if texto in saudacoes:
            enviar_whatsapp(sender,
                "✨ Olá! Eu sou a *KARDECIA IA*, sua assistente espiritual.\n"
                "Como posso te ajudar hoje? 💫"
            )
            return {"status": "ok"}

        # PDFs
        if "pdf" in texto or "livro" in texto:
            if "espirit" in texto:
                send_pdf(sender, PDF_LINKS["livro_dos_espiritos"]); return {"status": "ok"}
            if "mediun" in texto:
                send_pdf(sender, PDF_LINKS["livro_dos_mediuns"]); return {"status": "ok"}
            if "evangelho" in texto:
                send_pdf(sender, PDF_LINKS["evangelho"]); return {"status": "ok"}
            if "genese" in texto:
                send_pdf(sender, PDF_LINKS["genese"]); return {"status": "ok"}
            if "inferno" in texto or "ceu" in texto:
                send_pdf(sender, PDF_LINKS["ceu_inferno"]); return {"status": "ok"}

            enviar_whatsapp(sender,
                "📚 Qual livro deseja em PDF?\n"
                "- O Livro dos Espíritos\n"
                "- O Livro dos Médiuns\n"
                "- O Evangelho Segundo o Espiritismo\n"
                "- A Gênese\n"
                "- O Céu e o Inferno"
            )
            return {"status": "ok"}

        # IA NORMAL
        resposta = gerar_resposta_kardecia(sender, text)

        # Pedido de áudio
        if any(p in texto for p in ["audio", "áudio", "voz"]):
            enviar_whatsapp(sender, "🎤 Gerando áudio...")
            audio_path = gerar_audio_kardecia(resposta)
            enviar_audio_whatsapp(sender, audio_path)
            return {"status": "ok"}

        enviar_whatsapp(sender, resposta)
        return {"status": "ok"}

    except Exception as e:
        print("⚠️ Erro:", e)
        return {"status": "error"}


# -------------------------------
# 🤖 IA COM MEMÓRIA
# -------------------------------
def gerar_resposta_kardecia(user_id: str, msg: str):
    try:
        history = conversation_history.get(user_id, [])
        modo = user_preferences.get(user_id, {}).get("modo", "media")

        estilo = {
            "curta": "Responda em até 2 frases, simples e acolhedoras.",
            "media": "Responda com equilíbrio, acolhimento e calma.",
            "longa": "Responda com profundidade, espiritualidade e serenidade."
        }

        messages = [
            {
                "role": "system",
                "content":
                    "Você é a *KARDECIA IA*, uma assistente espiritual amorosa, "
                    "acolhedora e baseada na Doutrina Espírita. "
                    "Nunca faça previsões espirituais. \n\n"
                    f"{estilo[modo]}"
            }
        ]

        messages.extend(history)
        messages.append({"role": "user", "content": msg})

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        resposta = response.choices[0].message.content

        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": resposta})
        conversation_history[user_id] = history[-10:]

        return resposta

    except Exception:
        return "Desculpe, estou com instabilidade no momento 🙏"


# -------------------------------
# 🎤 ÁUDIO
# -------------------------------
def gerar_audio_kardecia(texto: str):
    try:
        audio = openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=texto
        )
        audio_bytes = audio.read()
        path = "/tmp/kardecia.ogg"
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return path
    except:
        return None


# -------------------------------
# 📚 PDF
# -------------------------------
def send_pdf(to: str, pdf_info: dict):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {
            "link": pdf_info["url"],
            "filename": pdf_info["name"]
        }
    }
    requests.post(url, json=data, headers=headers)


# -------------------------------
# 🎧 ÁUDIO
# -------------------------------
def enviar_audio_whatsapp(to: str, audio_path: str):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    with open(audio_path, "rb") as f:
        files = {"audio": f}
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "audio",
            "audio": {"filename": "kardecia.ogg"}
        }
        requests.post(url, data=data, files=files,
                      headers={"Authorization": f"Bearer {TOKEN}"})


# -------------------------------
# 💬 TEXTO
# -------------------------------
def enviar_whatsapp(to: str, text: str):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    requests.post(url, json=data, headers=headers)
