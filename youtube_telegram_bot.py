from telegram import Update
import yt_dlp
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import os
import asyncio
import subprocess
import logging
from dotenv import load_dotenv

load_dotenv()  

TOKEN = os.getenv("MY_TOKEN")
#print(f"TOKEN: {TOKEN}")

raw_users = os.getenv("AUTHORIZED_USERS", "")
AUTHORIZED_USERS = set(map(int, filter(None, raw_users.split(","))))

DESCARGAS_PATH = "downloads"
FAILED_PATH = "failed_audios"

# Definir estados de la conversación
ESPERANDO_URL, ESPERANDO_FORMATO = range(2)

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

for path in (DESCARGAS_PATH, FAILED_PATH):
    if not os.path.exists(path):
        os.makedirs(path)


async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("🚫 Acceso denegado. No eres un usuario con acceso a este bot.")
        return

    message = (
        "👋 ¡Hola! Soy un bot para descargar audios de YouTube creado por Daniel Álvarez Conde.\n\n"
        "📌 Envíame el enlace de un video de YouTube y lo convertiré en un archivo MP3.\n"
        "⚠️ El tamaño del archivo se mantendrá por debajo de 50 MB.\n\n"
        "🚀 Simplemente envía un enlace para comenzar."
    )
    await update.message.reply_text(message)


async def process_url(update: Update, context):
    user_id = update.message.from_user.id

    if user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("🚫 Acceso denegado. No eres un usuario con acceso a este bot.")
        return
    
    url = update.message.text.strip()
    logging.info(f"Recibida URL: {url}")

    # Validate the URL is from YouTube
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Enlace no válido. Por favor, envíame un enlace de YouTube.")
        logging.warning(f"URL inválida: {url}")
        return

    # Inform the user that download is starting
    await update.message.reply_text("⏳ Iniciando descarga del audio...")
    
    # Download output template
    output_template = os.path.join(DESCARGAS_PATH, "%(title)s.%(ext)s")

    # yt-dlp options to download best audio and extract MP3 at 192 kbps
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        logging.info(f"Iniciando descarga para URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            archivo_descargado = ydl.prepare_filename(info)
            # Adjust extension if necessary.
            archivo_descargado = archivo_descargado.replace(".webm", ".mp3").replace(".m4a", ".mp3")
        logging.info(f"Archivo descargado: {archivo_descargado}")
        await update.message.reply_text("✅ Descarga completada.")

        archivo_final = archivo_descargado
        file_size_mb = os.path.getsize(archivo_final) / (1024 * 1024)
        logging.info(f"Tamaño del archivo descargado: {file_size_mb:.2f} MB")
        await update.message.reply_text(f"El tamaño del archivo es: {file_size_mb:.2f} MB.")

        # If file is larger than 50 MB, compress it
        if file_size_mb > 50:
            await update.message.reply_text("⚠️ El archivo es demasiado grande. Iniciando compresión...")
            logging.info("Iniciando compresión del archivo...")
            archivo_comprimido = archivo_final.replace(".mp3", "_compressed.mp3")
            # Try lowering bitrate progressively
            for bitrate in ["128k", "96k", "64k"]:
                subprocess.run(
                    ["ffmpeg", "-i", archivo_final, "-b:a", bitrate, archivo_comprimido, "-y"],
                    check=True
                )
                new_size = os.path.getsize(archivo_comprimido) / (1024 * 1024)
                logging.info(f"Compresión a {bitrate}: {new_size:.2f} MB")
                await update.message.reply_text(f"Compresión a {bitrate}: {new_size:.2f} MB")
                if new_size < 50:
                    archivo_final = archivo_comprimido
                    break
            # Remove original uncompressed file
            if os.path.exists(archivo_descargado):
                os.remove(archivo_descargado)
                logging.info("Archivo original eliminado tras compresión.")
            await update.message.reply_text("✅ Compresión completada.")

        await asyncio.sleep(2)  # Small delay before sending
        logging.info(f"Archivo listo para enviar: {archivo_final}")
        await update.message.reply_text("📤 Enviando el audio...")

        # Send the MP3 file to the user
        with open(archivo_final, "rb") as file:
            await update.message.reply_audio(audio=file, caption="🎵 Aquí tienes tu audio en MP3.")
        logging.info(f"Archivo enviado: {archivo_final}")
        await update.message.reply_text("✅ Audio enviado correctamente.")

        # Delete the sent file
        os.remove(archivo_final)
        logging.info(f"Archivo eliminado después de enviar: {archivo_final}")

    except Exception as e:
        error_msg = f"❌ Error al procesar el audio: {str(e)}"
        await update.message.reply_text(error_msg)
        logging.error(error_msg, exc_info=True)
        # If the file exists, move it to FAILED_PATH for later inspection
        try:
            if 'archivo_final' in locals() and os.path.exists(archivo_final):
                destino = os.path.join(FAILED_PATH, os.path.basename(archivo_final))
                os.rename(archivo_final, destino)
                logging.info(f"Archivo movido a carpeta de fallidos: {destino}")
        except Exception as move_err:
            logging.error(f"No se pudo mover el archivo fallido: {str(move_err)}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_url))
    app.add_handler(CommandHandler("start", start))
    logging.info("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()