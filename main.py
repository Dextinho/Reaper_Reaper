import os
import json
import random
import logging
import asyncio
from datetime import datetime
import pytz
from config import config
from telebot.async_telebot import AsyncTeleBot
from telethon import events
from jinja2 import Environment, FileSystemLoader
from html2image import Html2Image


class BotBase:
    def __init__(self):
        self.bot = AsyncTeleBot(config.BOT_TOKEN)
        self.client = config.client
        self.templates_path = os.path.join(os.getcwd(), 'templates')
        self.env = Environment(loader=FileSystemLoader(self.templates_path))
        self.hti = Html2Image()
        self.zona_argentina = pytz.timezone('America/Argentina/Buenos_Aires')

        # Configuración de logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logging.info(f"Ruta absoluta de la carpeta templates: {self.templates_path}")

    async def run(self):
        await self.client.start()
        await self.bot.polling()


class BienvenidaBot(BotBase):
    def __init__(self):
        super().__init__()
        # Registro de eventos
        self.client.on(events.ChatAction)(self.handler)

        # Comandos del bot
        self.bot.add_message_handler({'function': self.comando_start, 'filters': {'commands': ['start']}})
        self.bot.add_message_handler({'function': self.comando_help, 'filters': {'commands': ['help']}})
        self.bot.add_message_handler({'function': self.comando_info, 'filters': {'commands': ['info']}})
        self.bot.add_message_handler({'function': self.comando_staff, 'filters': {'commands': ['staff']}})

    def obtener_emoji_por_disciplina(self, disciplina):
        emojis = {
            "física": "🔬",
            "programación": "💻",
            "matemáticas": "📐",
            "química": "⚗️",
            "biología": "🧬"
        }
        return emojis.get(disciplina, "📘")

    def obtener_frase_aleatoria(self):
        with open('frases.json', 'r', encoding='utf-8') as file:
            frases = json.load(file)
        frase_aleatoria = random.choice(frases)
        emoji = self.obtener_emoji_por_disciplina(frase_aleatoria['disciplina'])
        return f"{emoji} {frase_aleatoria['frase']} \n— {frase_aleatoria['autor']}"

    async def obtener_datos_usuario(self, event):
        try:
            user = await self.client.get_entity(event.user_id)
            user_photo_path = await self.client.download_profile_photo(user, file="static/images/user_photo.jpg") if user.photo else "static/images/Desconocido.jpg"

            group_chat = await event.get_chat()

            user_data = {
                "id": user.id,
                "first_name": user.first_name or "N/A",
                "last_name": user.last_name or "N/A",
                "username": user.username or "N/A",
                "bio": getattr(user, 'about', "N/A"),
                "restricted": user.restricted,
                "verified": user.verified,
                "premium": user.premium,
                "user_photo": os.path.abspath(user_photo_path),
                "hora_GTM": datetime.now(self.zona_argentina).strftime('%H:%M:%S'),
                "Fecha_GTM": datetime.now(self.zona_argentina).strftime('%Y-%m-%d'),
                "nombre_del_grupo": group_chat.title
            }
            return user_data
        except Exception as e:
            logging.error(f"Error al obtener datos del usuario: {e}")
            return None

    async def crear_html_bienvenida(self, user_data):
        # Crear nombre único para cada usuario
        temp_image_path = f'temp_bienvenida_foto_{user_data["id"]}.png'
        final_image_path = f'bienvenida_foto_{user_data["id"]}.png'  # Nombre único para evitar conflictos

        try:
            # Eliminar archivo temporal previo si existe
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
    
            logging.info("Cargando la plantilla de bienvenida...")
    
            # Intentar cargar la plantilla de la imagen de bienvenida
            try:
                template_foto = self.env.get_template('Bienvenido_foto.html')
            except Exception as e:
                logging.error(f"Error al cargar la plantilla: {e}")
                return "Error al cargar la plantilla.", None

            # Renderizar HTML
            html_renderizado_foto = template_foto.render(user_data)
    
            # Tomar screenshot y guardarlo en el archivo temporal
            self.hti.screenshot(html_str=html_renderizado_foto, save_as=temp_image_path)
            await asyncio.sleep(0.5)  # Esperar un poco después de tomar el screenshot
    
            # Eliminar el archivo final anterior si existe
            if os.path.exists(final_image_path):
                try:
                    os.remove(final_image_path)
                except Exception as e:
                    logging.error(f"Error al eliminar el archivo final: {e}")
    
            # Renombrar el archivo temporal al nombre final
            os.rename(temp_image_path, final_image_path)
    
            # Obtener y agregar frase aleatoria
            frase = self.obtener_frase_aleatoria()
            user_data["frase"] = frase
    
            # Cargar y renderizar la plantilla de texto
            template_texto = self.env.get_template('Bienvenida_texto.html')
            html_renderizado_texto = template_texto.render(user_data)
    
            return (html_renderizado_texto.replace("<!DOCTYPE html>", "")
                                           .replace("<html>", "")
                                           .replace("</html>", "")
                                           .replace("<head>", "")
                                           .replace("</head>", "")
                                           .replace("<body>", "")
                                           .replace("</body>", "")
                                           .strip(), final_image_path)
    
        except Exception as e:
            logging.error(f"Error al procesar la plantilla: {e}")
            return "Error al procesar la plantilla.", None

    

    async def handler(self, event):
        if event.user_joined or event.user_added:
            user_data = await self.obtener_datos_usuario(event)

            if user_data:
                texto_bienvenida, temp_image_path = await self.crear_html_bienvenida(user_data)

                if temp_image_path and os.path.exists(temp_image_path):
                    try:
                        await self.client.send_file(event.chat_id, temp_image_path, caption=texto_bienvenida, parse_mode='html')
                        logging.info(f"Bienvenida enviada al usuario {user_data['id']}.")
                    except Exception as e:
                        logging.error(f"Error al enviar la imagen de bienvenida: {e}")
                    finally:
                        # Eliminar archivo después de enviarlo
                        if os.path.exists(temp_image_path):
                            os.remove(temp_image_path)

    async def comando_start(self, message):
        welcome_message = "🎉 ¡Hola! Soy el Bot de Bienvenida. Estoy aquí para darte la bienvenida y proporcionarte información sobre el grupo. Usa /help para ver los comandos disponibles."
        await self.bot.send_message(message.chat.id, welcome_message)

    async def comando_help(self, message):
        help_message = ("/start - Muestra un mensaje de presentación.\n"
                        "/help - Muestra los comandos disponibles.\n"
                        "/info - Muestra información sobre el grupo y sus reglas.\n"
                        "/staff - Lista al equipo administrativo del grupo.")
        await self.bot.send_message(message.chat.id, help_message)

    async def comando_info(self, message):
        info_message = "📜 Bienvenido al grupo. Aquí compartimos conocimientos sobre programación, física, y otras ciencias. Por favor, revisa las reglas y sé respetuoso con todos los miembros."
        await self.bot.send_message(message.chat.id, info_message)

    async def comando_staff(self, message):
        staff_message = "👥 Nuestro equipo de administración:\n- Owner: @owner_username\n- Co-fundador: @co_fundador_username\n- Admin: @admin_username"
        await self.bot.send_message(message.chat.id, staff_message)


if __name__ == '__main__':
    bienvenida_bot = BienvenidaBot()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bienvenida_bot.run())