import asyncio
from telegram import Bot

TOKEN = "8677134850:AAHUI8hTpuUguiiybxogpoJleD-urhHKNGI"
CHAT_ID = "445822060"

async def main():
    bot = Bot(token=TOKEN)

    await bot.send_message(
        chat_id=CHAT_ID,
        text="🚨 Ahora sí funciona 🚨"
    )

    print("Mensaje enviado correctamente")

asyncio.run(main())
