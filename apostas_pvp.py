# ============================================================================
# COG: APOSTAS ENTRE JOGADORES
# ============================================================================

import discord
from discord.ext import commands
from database import db
from datetime import datetime

class ApostasPvP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='apostar', help='Desafiar outro jogador a uma aposta')
    async def apostar(self, ctx, usuario_desafiado: discord.User, valor: int, descricao: str = None):
        """Criar aposta com outro jogador"""
        
        # Validações
        if usuario_desafiado.id == ctx.author.id:
            await ctx.send('Você não pode apostar contra si mesmo!')
            return
        
        if usuario_desafiado.bot:
            await ctx.send('Você não pode apostar contra bots!')
            return
        
        if valor <= 0:
            await ctx.send('O valor da aposta deve ser maior que 0!')
            return
        
        # Verificar saldo do apostador
        usuario_apostador = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        if usuario_apostador['saldo'] < valor:
            embed = discord.Embed(
                title='❌ Saldo Insuficiente',
                description=f'Você precisa de 💵 {valor}, mas tem apenas 💵 {usuario_apostador["saldo"]:.2f}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Verificar saldo do desafiado
        usuario_desafiado_db = db.obter_ou_criar_usuario(usuario_desafiado.id, usuario_desafiado.name)
        if usuario_desafiado_db['saldo'] < valor:
            embed = discord.Embed(
                title='❌ Saldo Insuficiente',
                description=f'{usuario_desafiado.mention} não tem saldo suficiente (precisa de 💵 {valor})',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Bloquear saldos
        db.atualizar_saldo(ctx.author.id, -valor, 'aposta_bloqueada', 'Saldo bloqueado em aposta')
        db.atualizar_saldo(usuario_desafiado.id, -valor, 'aposta_bloqueada', 'Saldo bloqueado em aposta')
        
        # Criar aposta
        aposta_id = db.criar_aposta(
            ctx.author.id,
            usuario_desafiado.id,
            valor,
            descricao or 'Sem descrição'
        )
        
        embed = discord.Embed(
            title='🎯 Nova Aposta Criada!',
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.add_field(name='Apostador', value=f'{ctx.author.mention}', inline=True)
        embed.add_field(name='Desafiado', value=f'{usuario_desafiado.mention}', inline=True)
        embed.add_field(name='Valor', value=f'💵 {valor}', inline=True)
        embed.add_field(name='Descrição', value=descricao or 'Sem descrição', inline=False)
        embed.add_field(name='ID da Aposta', value=f'`{aposta_id}`', inline=False)
        embed.add_field(name='⚠️ Status', value='Aguardando aceitação', inline=False)
        
        embed.set_footer(text=f'Use !aceitar_aposta {aposta_id} para aceitar ou !recusar_aposta {aposta_id} para recusar')
        
        await ctx.send(embed=embed)
        
        # Enviar DM ao desafiado
        try:
            dm_embed = discord.Embed(
                title='🎯 Você foi desafiado a uma aposta!',
                color=discord.Color.purple(),
                timestamp=datetime.now()
            )
            dm_embed.add_field(name='Apostador', value=f'{ctx.author.mention}', inline=False)
            dm_embed.add_field(name='Valor', value=f'💵 {valor}', inline=False)
            dm_embed.add_field(name='Descrição', value=descricao or 'Sem descrição', inline=False)
            dm_embed.add_field(name='Servidor', value=ctx.guild.name if ctx.guild else 'DM', inline=False)
            dm_embed.set_footer(text=f'ID da Aposta: {aposta_id}')
            
            await usuario_desafiado.send(embed=dm_embed)
        except:
            pass  # Usuário pode ter DMs desativadas
    
    @commands.command(name='minhas_apostas', help='Ver suas apostas pendentes')
    async def minhas_apostas(self, ctx):
        """Mostrar apostas pendentes do usuário"""
        apostas = db.obter_apostas_pendentes(ctx.author.id)
        
        if not apostas:
            embed = discord.Embed(
                title='📋 Nenhuma Aposta Pendente',
                description=f'{ctx.author.mention} não tem apostas aguardando',
                color=discord.Color.gray()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f'📋 Apostas Pendentes de {ctx.author.name}',
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        for aposta in apostas:
            apostador_id = aposta['apostador']
            try:
                apostador = await self.bot.fetch_user(apostador_id)
                apostador_nome = apostador.mention
            except:
                apostador_nome = f'<@{apostador_id}>'
            
            embed.add_field(
                name=f'Aposta #{aposta["_id"]}',
                value=f'De: {apostador_nome}\nValor: 💵 {aposta["valor"]}\nDescrição: {aposta["descricao"]}',
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='definir_vencedor', help='Definir vencedor da aposta (admin)')
    @commands.has_permissions(administrator=True)
    async def definir_vencedor(self, ctx, aposta_id: str, vencedor: discord.User):
        """Definir vencedor (requer admin)"""
        try:
            from bson.objectid import ObjectId
            aposta = db.apostas.find_one({'_id': ObjectId(aposta_id)})
            
            if not aposta:
                await ctx.send('Aposta não encontrada!')
                return
            
            if aposta['status'] != 'pendente':
                await ctx.send('Esta aposta já foi finalizada!')
                return
            
            # Créditos para o vencedor
            valor_total = aposta['valor'] * 2
            imposto = int(valor_total * 0.1) if valor_total > 1000 else 0
            valor_liquido = valor_total - imposto
            
            db.atualizar_saldo(
                vencedor.id,
                valor_liquido,
                'aposta_vencida',
                f'Vitória em aposta contra {aposta["apostador"]}'
            )
            
            if imposto > 0:
                db.registrar_transacao(
                    vencedor.id,
                    -imposto,
                    'imposto',
                    vencedor.id,
                    0,
                    'Imposto sobre ganho de aposta'
                )
            
            # Finalizar aposta
            db.finalizar_aposta(ObjectId(aposta_id), vencedor.id)
            
            embed = discord.Embed(
                title='✅ Aposta Finalizada!',
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name='Vencedor', value=f'{vencedor.mention}', inline=True)
            embed.add_field(name='Prêmio Bruto', value=f'💰 {valor_total}', inline=True)
            if imposto > 0:
                embed.add_field(name='Imposto', value=f'💼 -{imposto}', inline=True)
            embed.add_field(name='Prêmio Líquido', value=f'✨ {valor_liquido}', inline=True)
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f'Erro: {e}')

async def setup(bot):
    await bot.add_cog(ApostasPvP(bot))
