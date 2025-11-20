import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from openai import OpenAI

# 🔐 Inicializa o cliente OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# 🔐 Pegando dados das variáveis de ambiente
TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

if not TOKEN or not PHONE_ID or not VERIFY_TOKEN:
    raise RuntimeError("❌ Configure as variáveis WHATSAPP_TOKEN, WHATSAPP_PHONE_ID e VERIFY_TOKEN no ambiente!")

# 🧠 Memória simples por usuário (últimas 5 mensagens)
conversation_history = {}

# 📚 Links dos PDFs (TROQUE pelos links reais depois)
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
    return {"status": "ok", "msg": "Webhook da IA Kardecia rodando 🚀"}


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

    return PlainTextResponse(content="Erro de verificação", status_code=403)


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

        # 🟦 SAUDAÇÕES – MENSAGEM INICIAL
        saudacoes = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "eai", "e aí", "hey", "ei"]
        if texto in saudacoes:
            mensagem_inicial = (
                "✨ Olá! Eu sou a *KARDECIA IA*.\n"
                "Estou aqui para te ajudar com temas da *Doutrina Espírita*, reflexões, estudos e acolhimento.\n\n"
                "Você pode pedir, por exemplo:\n"
                "- Uma explicação sobre algum tema espiritual\n"
                "- Uma orientação para um momento difícil\n"
                "- Um trecho comentado do Evangelho\n"
                "- Um PDF de alguma obra de Allan Kardec\n\n"
                "Como posso te ajudar hoje? 🙏💫"
            )
            enviar_whatsapp(sender, mensagem_inicial)
            return JSONResponse(content={"status": "ok"})

        # 🟨 PEDIDOS DE PDF
        if "pdf" in texto or "livro" in texto or "obra" in texto:
            # checa cada livro específico
            if "espiritos" in texto or "espíritos" in texto:
                send_pdf(sender, PDF_LINKS["livro_dos_espiritos"])
                return JSONResponse(content={"status": "ok"})

            if "mediuns" in texto or "médiuns" in texto:
                send_pdf(sender, PDF_LINKS["livro_dos_mediuns"])
                return JSONResponse(content={"status": "ok"})

            if "evangelho" in texto:
                send_pdf(sender, PDF_LINKS["evangelho"])
                return JSONResponse(content={"status": "ok"})

            if "genese" in texto or "gênese" in texto:
                send_pdf(sender, PDF_LINKS["genese"])
                return JSONResponse(content={"status": "ok"})

            if "ceu" in texto or "céu" in texto:
                send_pdf(sender, PDF_LINKS["ceu_inferno"])
                return JSONResponse(content={"status": "ok"})

            # se só falou "pdf" genérico:
            msg_pdf = (
                "📚 Posso te enviar os seguintes livros em PDF:\n"
                "• O Livro dos Espíritos\n"
                "• O Livro dos Médiuns\n"
                "• O Evangelho Segundo o Espiritismo\n"
                "• A Gênese\n"
                "• O Céu e o Inferno\n\n"
                "Digite o nome do livro (por exemplo: *Evangelho Segundo o Espiritismo*)."
            )
            enviar_whatsapp(sender, msg_pdf)
            return JSONResponse(content={"status": "ok"})

        # 🟩 RESPOSTA NORMAL COM IA + MEMÓRIA
        resposta = gerar_resposta_kardecia(sender, text)

        # 🔊 Se o usuário pedir áudio explicitamente
        pedido_audio = ["audio", "áudio", "manda áudio", "mande áudio", "voz", "quero ouvir", "em áudio"]
        if any(p in texto for p in pedido_audio):
            enviar_whatsapp(sender, "🎤 Vou te enviar essa resposta em áudio também, só um instante...")
            audio_path = gerar_audio_kardecia(resposta)
            if audio_path:
                enviar_audio_whatsapp(sender, audio_path)
            return JSONResponse(content={"status": "ok"})

        # 📝 Caso normal: envia apenas texto
        enviar_whatsapp(sender, resposta)
        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        print("⚠️ Erro ao processar mensagem:", e)
        return JSONResponse(content={"status": "error"})


# --------------------------------------
# 🤖 IA COM MEMÓRIA — RESPOSTA DA KARDECIA
# --------------------------------------
def gerar_resposta_kardecia(user_id: str, msg: str) -> str:
    try:
        # pega histórico do usuário (se existir)
        history = conversation_history.get(user_id, [])

        messages = [
            {
                "role": "system",
                "content": (
                    "Você é a Kardecia IA, uma assistente espiritualista baseada na Doutrina Espírita. "
                    "Responda sempre de forma acolhedora, calma, respeitosa e esclarecedora. "
                    "Evite previsões, adivinhações e qualquer promessa de resultados. "
                    "Use referências às obras de Allan Kardec quando fizer sentido."
                ),
            }
        ]

        # adiciona histórico ao contexto
        messages.extend(history)

        # adiciona a nova pergunta do usuário
        messages.append({"role": "user", "content": msg})

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        resposta = response.choices[0].message.content

        # atualiza memória: acrescenta user e assistant
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": resposta})

        # limita para últimas 5 interações (10 mensagens: 5 user + 5 assistant)
        if len(history) > 10:
            history = history[-10:]

        conversation_history[user_id] = history

        return resposta

    except Exception as e:
        print("🚨 Erro no ChatGPT:", e)
        return "Peço desculpas, estou com dificuldades temporárias para responder agora. Tente novamente em alguns instantes 🙏"


# --------------------------------------
# 🎤 GERAR ÁUDIO DA RESPOSTA
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
# 📚 ENVIAR PDF (DOCUMENTO) PELO WHATSAPP
# --------------------------------------
def send_pdf(to: str, pdf_info: dict):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
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

    resp = requests.post(url, json=data, headers=headers)
    print(f"📤 Envio de PDF ({pdf_info['name']}):", resp.status_code, resp.text)


# --------------------------------------
# 🎧 ENVIAR ÁUDIO PELO WHATSAPP
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
# 💬 ENVIAR TEXTO PELO WHATSAPP
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
    print("📤 Envio de texto:", resp.status_code, resp.text)
