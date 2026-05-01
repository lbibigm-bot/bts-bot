import asyncio
import requests
from telegram import Bot

TOKEN = "8677134850:AAHUI8hTpuUguiiybxogpoJleD-urhHKNGI"
CHAT_ID = "445822060"

URL = "https://www.ticketmaster.com.mx/api/quickpicks/1400642AA32C84D5/list?sort=price&offset=0&qty=2&primary=true&resale=false&defaultToOne=true&tids=000000000001%2C000001800001%2C000002000001&resaleProvider=INTL"

PRECIO_MAX = 5000  # ajusta si quieres
CHECK_INTERVAL = 20  # segundos

seen_ids = set()

async def check_tickets(bot):
    global seen_ids

    try:
        response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"})
        data = response.json()

        picks = data.get("picks", [])

        for p in picks:
            ticket_id = p.get("id")
            price = p.get("price", 0)
            section = p.get("section", "")
            row = p.get("row", "")

            if ticket_id not in seen_ids and price <= PRECIO_MAX:
                seen_ids.add(ticket_id)

                link = f"https://www.ticketmaster.com.mx/quickpicks/{ticket_id}"

                message = f"""
🚨 BOLETO DISPONIBLE 🚨

💰 ${price}
📍 {section}
🎟 Fila: {row}

🔗 Comprar:
{link}
"""

                await bot.send_message(chat_id=CHAT_ID, text=message)

                print("Alerta enviada:", ticket_id)

    except Exception as e:
        print("Error:", e)

async def main():
    bot = Bot(token=TOKEN)

    print("Bot cazador iniciado 🔥")

    while True:
        await check_tickets(bot)
        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(main())
