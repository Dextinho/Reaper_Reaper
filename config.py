import os
from dotenv import load_dotenv
from telethon import TelegramClient

class Config:
    def __init__(self):
        # Cargar variables de entorno
        load_dotenv()

        # Obtener el token del bot y las credenciales de API
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        self.API_ID = os.getenv('API_ID')
        self.API_HASH = os.getenv('API_HASH')

        # Validar que las variables de entorno están definidas
        self.validar_variables()

        # Inicialización del cliente de Telethon
        self.client = TelegramClient('bot', self.API_ID, self.API_HASH).start(bot_token=self.BOT_TOKEN)

    def validar_variables(self):
        if self.BOT_TOKEN is None:
            raise ValueError("No se ha encontrado el token del bot. Verifica que BOT_TOKEN esté definido en el archivo .env")
        if self.API_ID is None:
            raise ValueError("No se ha encontrado el API ID. Verifica que API_ID esté definido en el archivo .env")
        if self.API_HASH is None:
            raise ValueError("No se ha encontrado el API HASH. Verifica que API_HASH esté definido en el archivo .env")

# Instancia de configuración
config = Config()
