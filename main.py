import requests
from telegram import Bot

TOKEN = "8677134850:AAHUI8hTpuUguiiybxogpoJleD-urhHKNGI"
CHAT_ID = "445822060"

bot = Bot(token=TOKEN)

bot.send_message(
    chat_id=CHAT_ID,
    text="🚨 Bot conectado correctamente 🚨"
)

print("Mensaje enviado a Telegram")
text="🚨 Prueba final funcionando 🚨"
