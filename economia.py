# ============================================================================
# COG: ECONOMIA BÁSICA - Saldo, Daily, Perfil, Ranking
# ============================================================================

import discord
from discord.ext import commands, tasks
from database import db
from datetime import datetime, timedelta
import random

class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='saldo', help='Ver seu saldo atual')
    async def saldo(self, ctx, user: discord.User = None):
        """Mostrar saldo do usuário"""
        if user is None:
            user = ctx.author
        
        usuario = db.obter_ou_criar_usuario(user.id, user.name)
        
        embed = discord.Embed(
            title=f'💰 Saldo de {user.name}',
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        embed.add_field(name='Saldo', value=f'💵 {usuario["saldo"]:.2f}', inline=False)
        embed.add_field(name='Nível', value=f'⭐ {usuario["nivel"]}', inline=True)
        embed.add_field(name='Experiência', value=f'📊 {usuario["experiencia"]}/1000', inline=True)
        embed.add_field(name='Streak Daily', value=f'🔥 {usuario["streak_daily"]}', inline=True)
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='daily', help='Receber recompensa diária aleatória')
    async def daily(self, ctx):
        """Comando daily com valor aleatório"""
        usuario = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        
        # Verificar se já resgatou hoje
        ultima_recompensa = usuario.get('ultima_recompensa_daily')
        if ultima_recompensa:
            ultima_data = datetime.fromisoformat(ultima_recompensa) if isinstance(ultima_recompensa, str) else ultima_recompensa
            tempo_decorrido = datetime.now() - ultima_data
            
            if tempo_decorrido.days < 1:
                horas_faltando = 24 - (tempo_decorrido.seconds // 3600)
                embed = discord.Embed(
                    title='⏰ Daily já resgatado!',
                    description=f'Volte em {horas_faltando} horas',
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        # Gerar valor aleatório (100 a 500)
        valor_recompensa = random.randint(100, 500)
        
        # Atualizar streak
        ultima_data = datetime.fromisoformat(ultima_recompensa) if ultima_recompensa and isinstance(ultima_recompensa, str) else ultima_recompensa
        if ultima_data and (datetime.now() - ultima_data).days == 1:
            nova_streak = usuario['streak_daily'] + 1
        else:
            nova_streak = 1
        
        # Bônus por streak (10% a cada dia consecutivo)
        bonus = int(valor_recompensa * (nova_streak * 0.1))
        valor_total = valor_recompensa + bonus
        
        # Atualizar banco de dados
        db.atualizar_saldo(
            ctx.author.id,
            valor_total,
            'daily',
            f'Daily com streak de {nova_streak}'
        )
        
        db.usuarios.update_one(
            {'user_id': ctx.author.id},
            {
                '$set': {
                    'ultima_recompensa_daily': datetime.now().isoformat(),
                    'streak_daily': nova_streak
                }
            }
        )
        
        db.adicionar_experiencia(ctx.author.id, 25)
        
        embed = discord.Embed(
            title='💎 Daily Resgatado!',
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name='Valor Base', value=f'💵 {valor_recompensa}', inline=True)
        embed.add_field(name='Bônus Streak', value=f'🔥 +{bonus}', inline=True)
        embed.add_field(name='Total', value=f'✨ {valor_total}', inline=True)
        embed.add_field(name='Streak Atual', value=f'🌟 {nova_streak} dia(s)', inline=False)
        embed.add_field(name='Novo Saldo', value=f'💰 {usuario["saldo"] + valor_total}', inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='perfil', help='Ver perfil do usuário')
    async def perfil(self, ctx, user: discord.User = None):
        """Mostrar perfil completo"""
        if user is None:
            user = ctx.author
        
        usuario = db.obter_ou_criar_usuario(user.id, user.name)
        
        # Calcular tempo ativo
        data_criacao = datetime.fromisoformat(usuario['data_criacao']) if isinstance(usuario['data_criacao'], str) else usuario['data_criacao']
        tempo_ativo = datetime.now() - data_criacao
        dias_ativo = tempo_ativo.days
        
        embed = discord.Embed(
            title=f'👤 Perfil de {user.name}',
            description=usuario['perfil']['titulo'],
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        
        embed.add_field(name='💰 Saldo', value=f'{usuario["saldo"]:.2f}', inline=False)
        embed.add_field(name='⭐ Nível', value=f'{usuario["nivel"]}', inline=True)
        embed.add_field(name='📊 Experiência', value=f'{usuario["experiencia"]}/1000', inline=True)
        embed.add_field(name='🔥 Streak Daily', value=f'{usuario["streak_daily"]}', inline=True)
        embed.add_field(name='📅 Dias Ativo', value=f'{dias_ativo}', inline=True)
        embed.add_field(name='🏷️ Badge', value=usuario['perfil']['badge'], inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='ranking', help='Ver top 10 usuários mais ricos')
    async def ranking(self, ctx):
        """Mostrar ranking de usuários mais ricos"""
        ricos = db.obter_top_ricos(10)
        
        if not ricos:
            await ctx.send('Nenhum usuário registrado ainda!')
            return
        
        embed = discord.Embed(
            title='🏆 Ranking - Top 10 Mais Ricos',
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        for i, usuario in enumerate(ricos, 1):
            medalhas = ['🥇', '🥈', '🥉']
            medalha = medalhas[i-1] if i <= 3 else f'#{i}'
            
            embed.add_field(
                name=f'{medalha} {usuario["username"]}',
                value=f'💰 {usuario["saldo"]:.2f} | ⭐ Nível {usuario["nivel"]}',
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='extrato', help='Ver histórico de transações')
    async def extrato(self, ctx, user: discord.User = None, limite: int = 10):
        """Mostrar extrato (histórico de transações)"""
        if user is None:
            user = ctx.author
        
        # Verificar permissões - usuário só pode ver seu próprio extrato ou admin pode ver qualquer um
        if user.id != ctx.author.id and not ctx.author.guild_permissions.administrator:
            await ctx.send('Você só pode ver seu próprio extrato!')
            return
        
        transacoes = db.obter_extrato(user.id, limite)
        
        if not transacoes:
            embed = discord.Embed(
                title='📋 Extrato Vazio',
                description=f'{user.mention} não tem transações registradas',
                color=discord.Color.gray()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f'📊 Extrato de {user.name}',
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for trans in transacoes:
            data = datetime.fromisoformat(trans['data']) if isinstance(trans['data'], str) else trans['data']
            valor_str = f'+{trans["valor"]}' if trans['valor'] > 0 else f'{trans["valor"]}'
            
            embed.add_field(
                name=f'{trans["tipo"].upper()} - {data.strftime("%d/%m %H:%M")}',
                value=f'{valor_str} | Saldo: {trans["saldo_posterior"]:.2f}',
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='imposto', help='Ver imposto a pagar')
    async def imposto(self, ctx):
        """Informações sobre impostos"""
        # Sistema de imposto: 10% sobre ganhos de jogos/apostas acima de 1000
        embed = discord.Embed(
            title='💼 Sistema de Impostos',
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name='📋 Regras de Imposto',
            value='• Ganhos de jogos/apostas > 1000: 10% de imposto\n• Ganhos de daily: Sem imposto\n• Ganhos de venda de ações: 5% de imposto (lucro)',
            inline=False
        )
        embed.add_field(
            name='💡 Informação',
            value='Os impostos são automaticamente descontados ao ganhar. Você pode verificar seus impostos pagos no extrato.',
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economia(bot))
