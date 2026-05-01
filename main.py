import asyncio
import json
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

URL = "https://www.ticketmaster.com.mx/api/quickpicks/1400642AA32C84D5/list?sort=price&offset=0&qty=2&primary=true&resale=false&defaultToOne=true&tids=000000000001%2C000001800001%2C000002000001&resaleProvider=INTL"

CHECK_MIN = 30
CHECK_MAX = 45

TURBO_MIN = 10
TURBO_MAX = 15

# =========================
# HEADERS
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
# JSON USUARIOS
# =========================

USUARIOS_FILE = "usuarios.json"

# =========================
# LOAD USERS
# =========================

def cargar_usuarios():

    try:

        with open(USUARIOS_FILE, "r") as f:
            return json.load(f)

    except:
        return {}

# =========================
# SAVE USERS
# =========================

def guardar_usuarios(data):

    with open(USUARIOS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =========================
# USERS
# =========================

usuarios = cargar_usuarios()

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
# ALERTAS
# =========================

async def enviar_alertas(bot, ticket, tipo, actividad=False):

    actividad_msg = ""

    if actividad:
        actividad_msg = "🔥 ACTIVIDAD DETECTADA\n"

    for chat_id, config in usuarios.items():

        try:

            precio_max = config["precio_max"]
            zonas = config["zonas"]

            if ticket["price"] > precio_max:
                continue

            section = ticket["section"].lower()

            if zonas:

                if not any(
                    zona.lower() in section
                    for zona in zonas
                ):
                    continue

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
                chat_id=chat_id,
                text=mensaje
            )

            print(f"✅ ALERTA enviada a {chat_id}")

        except Exception as e:

            print("❌ Error usuario:", e)

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
        # BLOQUEOS
        # =========================

        if response.status_code in [403, 429]:

            blocked_counter += 1

            espera = 180

            if blocked_counter >= 3:
                espera = 420

            print(f"⚠️ Bloqueo detectado. Esperando {espera}s")

            await asyncio.sleep(espera)

            return

        try:

            data = response.json()

        except:

            print("⚠️ JSON inválido")

            await asyncio.sleep(120)

            return

        blocked_counter = 0

        picks = data.get("picks", [])

        if not isinstance(picks, list):

            print("⚠️ Respuesta sospechosa")

            await asyncio.sleep(120)

            return

        current_count = len(picks)

        actividad = False

        # =========================
        # ACTIVIDAD
        # =========================

        if current_count > last_count + 5:

            actividad = True

            turbo_mode = True
            turbo_cycles = 20

            print("🔥 ACTIVIDAD DETECTADA")

            for chat_id in usuarios:

                try:

                    await bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "🔥 ACTIVIDAD DETECTADA EN TM 🔥\n"
                            "⚡ MODO TURBO ACTIVADO"
                        )
                    )

                except:
                    pass

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

            await enviar_alertas(
                bot,
                ticket,
                tipo,
                actividad
            )

            print("✅ ALERTA GLOBAL:", ticket_id)

    except Exception as e:

        print("❌ ERROR:", e)

        await asyncio.sleep(90)

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = str(update.effective_chat.id)

    if chat_id not in usuarios:

        usuarios[chat_id] = {
            "precio_max": 10000,
            "zonas": ["Cancha", "VIP", "General"]
        }

        guardar_usuarios(usuarios)

    mensaje = """
🤖 BTS BOT ACTIVADO

Comandos:

/precio 4000
/zonas cancha,vip
/status
/stop
"""

    await update.message.reply_text(mensaje)

# =========================
# STOP
# =========================

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = str(update.effective_chat.id)

    if chat_id in usuarios:

        del usuarios[chat_id]

        guardar_usuarios(usuarios)

    await update.message.reply_text(
        "🛑 Alertas desactivadas"
    )

# =========================
# PRECIO
# =========================

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        chat_id = str(update.effective_chat.id)

        nuevo = int(context.args[0])

        usuarios[chat_id]["precio_max"] = nuevo

        guardar_usuarios(usuarios)

        await update.message.reply_text(
            f"💰 Precio máximo actualizado: ${nuevo}"
        )

    except:

        await update.message.reply_text(
            "Uso: /precio 4000"
        )

# =========================
# ZONAS
# =========================

async def zonas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        chat_id = str(update.effective_chat.id)

        texto = " ".join(context.args)

        lista = [
            z.strip()
            for z in texto.split(",")
        ]

        usuarios[chat_id]["zonas"] = lista

        guardar_usuarios(usuarios)

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

    chat_id = str(update.effective_chat.id)

    if chat_id not in usuarios:

        await update.message.reply_text(
            "Usa /start primero"
        )

        return

    data = usuarios[chat_id]

    mensaje = f"""
🤖 STATUS

💰 Precio máximo:
${data['precio_max']}

📍 Zonas:
{data['zonas']}

🛡 Anti-bloqueo:
ACTIVO

⚡ Turbo:
{"ACTIVO" if turbo_mode else "NORMAL"}
"""

    await update.message.reply_text(mensaje)

# =========================
# MONITOR
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

            for chat_id in usuarios:

                try:

                    await bot.send_message(
                        chat_id=chat_id,
                        text="""
🤖 BOT ACTIVO

🛡 Anti-bloqueo activo
⏳ Monitoreando Ticketmaster
⚡ Estado operativo
"""
                    )

                except:
                    pass

            heartbeat_counter = 0

        # =========================
        # TURBO
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
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("stop", stop)
    )

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

    print("🔥 BTS MULTIUSUARIO INICIADO 🔥")

    asyncio.create_task(
        monitor(bot)
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
