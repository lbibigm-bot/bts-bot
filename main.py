import asyncio
import random
import requests

from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# =========================
# CONFIG
# =========================

TOKEN = "8677134850:AAF7ZQKmrkXkh0j7x2cSBVVc8EdS6UrE1cE"
CHAT_ID = "445822060"

URL = "https://www.ticketmaster.com.mx/api/quickpicks/1400642AA32C84D5/list?sort=price&offset=0&qty=2&primary=true&resale=false&defaultToOne=true&tids=000000000001%2C000001800001%2C000002000001&resaleProvider=INTL"

# =========================
# INTERVALOS
# =========================

CHECK_MIN = 30
CHECK_MAX = 45

TURBO_MIN = 10
TURBO_MAX = 15

# =========================
# ESTADO DINÁMICO
# =========================

estado = {
    "precio_max": 10000,
    "zonas": ["Cancha", "VIP", "General"]
}

# =========================
# HEADERS HUMANOS
# =========================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es-MX,es;q=0.9",
    "Referer": "https://www.ticketmaster.com.mx/"
}

# =========================
# STORAGE
# =========================

seen_ids = set()

last_count = 0
blocked_counter = 0

turbo_mode = False
turbo_cycles = 0

heartbeat_counter = 0

# =========================
# CLASIFICADOR
# =========================

def clasificar(price, section):

    section = section.lower()

    if price <= 3000:
        return "🔥 OPORTUNIDAD"

    if "cancha" in section:
        return "⚡ CANCHA"

    if "vip" in section:
        return "💎 VIP"

    if price <= 5000:
        return "✅ BUENO"

    return "ℹ️ DISPONIBLE"

# =========================
# FILTRO ZONAS
# =========================

def zona_valida(section):

    zonas = estado["zonas"]

    if not zonas:
        return True

    section = section.lower()

    return any(
        zona.lower() in section
        for zona in zonas
    )

# =========================
# ALERTA TELEGRAM
# =========================

async def enviar_alerta(bot, ticket, tipo, actividad=False):

    actividad_msg = ""

    if actividad:
        actividad_msg = "🔥 ACTIVIDAD DETECTADA\n"

    mensaje = f"""
{tipo}

{actividad_msg}
💰 ${ticket['price']}
📍 {ticket['section']}
🎟 Fila: {ticket['row']}

🔗 Comprar:
{ticket['link']}
"""

    await bot.send_message(
        chat_id=CHAT_ID,
        text=mensaje
    )

# =========================
# REVISAR TICKETS
# =========================

async def revisar_tickets(bot):

    global last_count
    global blocked_counter
    global turbo_mode
    global turbo_cycles

    try:

        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=15
        )

        # =========================
        # DETECTOR BLOQUEOS
        # =========================

        if response.status_code in [403, 429]:

            blocked_counter += 1

            espera = 180

            if blocked_counter >= 3:
                espera = 420

            print(f"⚠️ Bloqueo detectado. Esperando {espera}s")

            await asyncio.sleep(espera)

            return

        # =========================
        # JSON SEGURO
        # =========================

        try:

            data = response.json()

        except:

            print("⚠️ JSON inválido")

            await asyncio.sleep(120)

            return

        blocked_counter = 0

        picks = data.get("picks", [])

        # =========================
        # RESPUESTA VACÍA
        # =========================

        if not isinstance(picks, list):

            print("⚠️ Respuesta sospechosa")

            await asyncio.sleep(120)

            return

        current_count = len(picks)

        actividad = False

        # =========================
        # ACTIVIDAD DETECTADA
        # =========================

        if current_count > last_count + 5:

            actividad = True

            turbo_mode = True
            turbo_cycles = 20

            print("🔥 ACTIVIDAD DETECTADA")

            await bot.send_message(
                chat_id=CHAT_ID,
                text=(
                    "🔥 ACTIVIDAD DETECTADA EN TM 🔥\n"
                    "⚡ MODO TURBO ACTIVADO"
                )
            )

        last_count = current_count

        # =========================
        # LOOP TICKETS
        # =========================

        for p in picks:

            ticket_id = p.get("id")

            if ticket_id in seen_ids:
                continue

            price = p.get("price", 0)
            section = p.get("section", "")
            row = p.get("row", "")

            if price > estado["precio_max"]:
                continue

            if not zona_valida(section):
                continue

            seen_ids.add(ticket_id)

            tipo = clasificar(price, section)

            ticket = {
                "price": price,
                "section": section,
                "row": row,
                "link": (
                    "https://www.ticketmaster.com.mx/"
                    f"quickpicks/{ticket_id}"
                )
            }

            await enviar_alerta(
                bot,
                ticket,
                tipo,
                actividad
            )

            print("✅ ALERTA:", ticket_id)

    except Exception as e:

        print("❌ ERROR:", e)

        await asyncio.sleep(90)

# =========================
# COMANDO PRECIO
# =========================

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        nuevo = int(context.args[0])

        estado["precio_max"] = nuevo

        await update.message.reply_text(
            f"💰 Precio máximo actualizado: ${nuevo}"
        )

    except:

        await update.message.reply_text(
            "Uso: /precio 4000"
        )

# =========================
# COMANDO ZONAS
# =========================

async def zonas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        texto = " ".join(context.args)

        lista = [
            z.strip()
            for z in texto.split(",")
        ]

        estado["zonas"] = lista

        await update.message.reply_text(
            f"📍 Zonas actualizadas:\n{lista}"
        )

    except:

        await update.message.reply_text(
            "Uso: /zonas cancha,vip"
        )

# =========================
# STATUS
# =========================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = f"""
🤖 STATUS

💰 Precio máximo:
${estado['precio_max']}

📍 Zonas:
{estado['zonas']}

🛡 Anti-bloqueo:
ACTIVO

⚡ Turbo mode:
{"ACTIVO" if turbo_mode else "NORMAL"}
"""

    await update.message.reply_text(mensaje)

# =========================
# LOOP PRINCIPAL
# =========================

async def monitor(bot):

    global turbo_mode
    global turbo_cycles
    global heartbeat_counter

    while True:

        await revisar_tickets(bot)

        # =========================
        # HEARTBEAT
        # =========================

        heartbeat_counter += 1

        if heartbeat_counter >= 90:

            await bot.send_message(
                chat_id=CHAT_ID,
                text="""
🤖 BOT ACTIVO

🛡 Anti-bloqueo activo
⏳ Monitoreando Ticketmaster
⚡ Estado operativo
"""
            )

            heartbeat_counter = 0

        # =========================
        # MODO TURBO
        # =========================

        if turbo_mode:

            espera = random.randint(
                TURBO_MIN,
                TURBO_MAX
            )

            turbo_cycles -= 1

            print(f"⚡ TURBO MODE {espera}s")

            if turbo_cycles <= 0:

                turbo_mode = False

                print("🛡 Volviendo a modo seguro")

        else:

            espera = random.randint(
                CHECK_MIN,
                CHECK_MAX
            )

            print(f"⏳ Esperando {espera}s")

        await asyncio.sleep(espera)

# =========================
# MAIN
# =========================

async def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("precio", precio)
    )

    app.add_handler(
        CommandHandler("zonas", zonas)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    bot = Bot(token=TOKEN)

    print("🔥 BOT BTS PRO INICIADO 🔥")

    await bot.send_message(
        chat_id=CHAT_ID,
        text="🤖 BOT BTS PRO ACTIVO 🤖"
    )

    asyncio.create_task(
        monitor(bot)
    )

    print("🚀 Comandos activos")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
