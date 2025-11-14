# ============================================================================
# COG: JOGOS DE CASSINO - Coinflip, Slots, Blackjack, Roleta
# ============================================================================

import discord
from discord.ext import commands
from database import db
from datetime import datetime
import random

class Cassino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='coinflip', help='Cara ou Coroa')
    async def coinflip(self, ctx, aposta: int, escolha: str = None):
        """Jogar Cara ou Coroa"""
        usuario = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        
        # Validar aposta
        if aposta <= 0:
            await ctx.send('A aposta deve ser maior que 0!')
            return
        
        if usuario['saldo'] < aposta:
            embed = discord.Embed(
                title='❌ Saldo Insuficiente',
                description=f'Você precisa de 💵 {aposta}, mas tem apenas 💵 {usuario["saldo"]:.2f}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Se não escolheu, sortear
        if escolha is None or escolha.lower() not in ['cara', 'coroa', 'c', 'k']:
            escolha = random.choice(['cara', 'coroa'])
        else:
            escolha = 'cara' if escolha.lower() in ['cara', 'c'] else 'coroa'
        
        resultado = random.choice(['cara', 'coroa'])
        ganhou = escolha == resultado
        
        # Calcular ganho/perda
        if ganhou:
            ganho = aposta * 2  # Duplica
            imposto = int(ganho * 0.1) if ganho > 1000 else 0
            ganho_liquido = ganho - aposta - imposto
            
            db.atualizar_saldo(ctx.author.id, ganho_liquido, 'aposta_ganha', 'Coinflip vencida')
            
            if imposto > 0:
                db.registrar_transacao(
                    ctx.author.id,
                    -imposto,
                    'imposto',
                    usuario['saldo'] + ganho_liquido + imposto,
                    usuario['saldo'] + ganho_liquido,
                    'Imposto sobre ganho de coinflip'
                )
            
            embed = discord.Embed(
                title='🎉 Você Ganhou!',
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name='Resultado', value=f'🪙 {resultado.upper()}', inline=True)
            embed.add_field(name='Sua Escolha', value=f'🎯 {escolha.upper()}', inline=True)
            embed.add_field(name='Aposta', value=f'💵 {aposta}', inline=True)
            embed.add_field(name='Ganho Bruto', value=f'💰 {ganho}', inline=True)
            if imposto > 0:
                embed.add_field(name='Imposto', value=f'💼 -{imposto}', inline=True)
            embed.add_field(name='Ganho Líquido', value=f'✨ +{ganho_liquido}', inline=True)
            embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] + ganho_liquido}', inline=False)
        else:
            db.atualizar_saldo(ctx.author.id, -aposta, 'aposta_perdida', 'Coinflip perdida')
            
            embed = discord.Embed(
                title='😢 Você Perdeu!',
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.add_field(name='Resultado', value=f'🪙 {resultado.upper()}', inline=True)
            embed.add_field(name='Sua Escolha', value=f'🎯 {escolha.upper()}', inline=True)
            embed.add_field(name='Aposta Perdida', value=f'💵 -{aposta}', inline=True)
            embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] - aposta}', inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='slots', help='Máquina Caça-Níqueis')
    async def slots(self, ctx, aposta: int):
        """Jogar na máquina caça-níqueis"""
        usuario = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        
        if aposta <= 0 or usuario['saldo'] < aposta:
            embed = discord.Embed(
                title='❌ Aposta Inválida',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Gerar rolagem
        simbolos = ['🍎', '🍊', '🍋', '⭐', '💎', '🎲']
        rolo1 = random.choice(simbolos)
        rolo2 = random.choice(simbolos)
        rolo3 = random.choice(simbolos)
        
        # Determinar prêmio
        if rolo1 == rolo2 == rolo3:
            if rolo1 == '💎':
                ganho = aposta * 10  # Jackpot
            else:
                ganho = aposta * 5
        elif rolo1 == rolo2 or rolo2 == rolo3:
            ganho = aposta * 2
        else:
            ganho = 0
        
        if ganho > 0:
            imposto = int(ganho * 0.1) if ganho > 1000 else 0
            ganho_liquido = ganho - aposta - imposto
            
            db.atualizar_saldo(ctx.author.id, ganho_liquido, 'aposta_ganha', 'Slots vencida')
            
            if imposto > 0:
                db.registrar_transacao(
                    ctx.author.id,
                    -imposto,
                    'imposto',
                    usuario['saldo'] + ganho_liquido + imposto,
                    usuario['saldo'] + ganho_liquido,
                    'Imposto sobre ganho de slots'
                )
            
            titulo = '🎉 JACKPOT!' if rolo1 == rolo2 == rolo3 and rolo1 == '💎' else '🎉 Você Ganhou!'
            embed = discord.Embed(title=titulo, color=discord.Color.green())
            embed.add_field(name='Resultado', value=f'{rolo1} {rolo2} {rolo3}', inline=False)
            embed.add_field(name='Ganho Bruto', value=f'💰 {ganho}', inline=True)
            if imposto > 0:
                embed.add_field(name='Imposto', value=f'💼 -{imposto}', inline=True)
            embed.add_field(name='Ganho Líquido', value=f'✨ +{ganho_liquido}', inline=True)
            embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] + ganho_liquido}', inline=False)
        else:
            db.atualizar_saldo(ctx.author.id, -aposta, 'aposta_perdida', 'Slots perdida')
            
            embed = discord.Embed(
                title='😢 Nenhuma Combinação',
                color=discord.Color.red()
            )
            embed.add_field(name='Resultado', value=f'{rolo1} {rolo2} {rolo3}', inline=False)
            embed.add_field(name='Aposta Perdida', value=f'💵 -{aposta}', inline=True)
            embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] - aposta}', inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='roleta', help='Jogar na Roleta')
    async def roleta(self, ctx, aposta: int, numero: int = None):
        """Jogar na Roleta (0-36)"""
        usuario = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        
        if aposta <= 0 or usuario['saldo'] < aposta:
            embed = discord.Embed(title='❌ Aposta Inválida', color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        
        # Se não escolheu número, sortear
        if numero is None:
            numero = random.randint(0, 36)
        elif numero < 0 or numero > 36:
            await ctx.send('Escolha um número entre 0 e 36!')
            return
        
        resultado = random.randint(0, 36)
        ganhou = numero == resultado
        
        if ganhou:
            ganho = aposta * 36  # Prêmio 36:1
            imposto = int(ganho * 0.1) if ganho > 1000 else 0
            ganho_liquido = ganho - aposta - imposto
            
            db.atualizar_saldo(ctx.author.id, ganho_liquido, 'aposta_ganha', 'Roleta vencida')
            
            if imposto > 0:
                db.registrar_transacao(
                    ctx.author.id,
                    -imposto,
                    'imposto',
                    usuario['saldo'] + ganho_liquido + imposto,
                    usuario['saldo'] + ganho_liquido,
                    'Imposto sobre ganho de roleta'
                )
            
            embed = discord.Embed(title='🎉 VOCÊ ACERTOU!', color=discord.Color.green())
            embed.add_field(name='Número Sorteado', value=f'🎲 {resultado}', inline=True)
            embed.add_field(name='Sua Escolha', value=f'🎯 {numero}', inline=True)
            embed.add_field(name='Ganho Bruto', value=f'💰 {ganho}', inline=True)
            if imposto > 0:
                embed.add_field(name='Imposto', value=f'💼 -{imposto}', inline=True)
            embed.add_field(name='Ganho Líquido', value=f'✨ +{ganho_liquido}', inline=True)
            embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] + ganho_liquido}', inline=False)
        else:
            db.atualizar_saldo(ctx.author.id, -aposta, 'aposta_perdida', 'Roleta perdida')
            
            embed = discord.Embed(title='😢 Número Incorreto', color=discord.Color.red())
            embed.add_field(name='Número Sorteado', value=f'🎲 {resultado}', inline=True)
            embed.add_field(name='Sua Escolha', value=f'🎯 {numero}', inline=True)
            embed.add_field(name='Aposta Perdida', value=f'💵 -{aposta}', inline=False)
            embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] - aposta}', inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Cassino(bot))
