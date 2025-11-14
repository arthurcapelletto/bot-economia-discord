# ============================================================================
# BOT DISCORD ECONOMIA COM BOLSA B3 - ARQUIVO PRINCIPAL
# ============================================================================

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')
BRAPI_TOKEN = os.getenv('BRAPI_TOKEN')

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Evento: Bot pronto
@bot.event
async def on_ready():
    print(f'{bot.user} conectado com sucesso!')
    print('Carregando cogs...')
    
    # Carregar todos os cogs de economia e jogos
    cogs_dir = 'cogs'
    for folder in os.listdir(cogs_dir):
        folder_path = os.path.join(cogs_dir, folder)
        if os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith('.py') and not filename.startswith('_'):
                    cog_name = filename[:-3]
                    try:
                        await bot.load_extension(f'cogs.{folder}.{cog_name}')
                        print(f'✓ Cog carregado: {folder}/{cog_name}')
                    except Exception as e:
                        print(f'✗ Erro ao carregar {folder}/{cog_name}: {e}')

# Executar o bot
if __name__ == '__main__':
    bot.run(TOKEN)