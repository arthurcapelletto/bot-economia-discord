# ============================================================================
# COG: PIX - TRANSFERÊNCIAS ENTRE USUÁRIOS (AUDITÁVEL)
# ============================================================================

import discord
from discord.ext import commands
from database import db
from datetime import datetime
import re

class Pix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.transacoes_pendentes = {}  # Armazenar confirmações pendentes
    
    @commands.command(name='pix', help='Enviar dinheiro via Pix para outro usuário')
    async def pix(self, ctx, destinatario: discord.User, valor: float, *, descricao: str = None):
        """
        Transferir dinheiro para outro usuário via PIX
        Exemplo: !pix @usuario 100 Pagamento de aposta
        """
        
        # ========== VALIDAÇÕES ==========
        
        # 1. Não pode enviar para si mesmo
        if destinatario.id == ctx.author.id:
            embed = discord.Embed(
                title='❌ Erro na Transação',
                description='Você não pode enviar PIX para si mesmo!',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # 2. Não pode enviar para bots
        if destinatario.bot:
            embed = discord.Embed(
                title='❌ Erro na Transação',
                description='Você não pode enviar PIX para bots!',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # 3. Valor deve ser positivo e mínimo 1
        if valor < 1:
            embed = discord.Embed(
                title='❌ Valor Inválido',
                description='O valor mínimo para PIX é 💵 1.00',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Arredondar valor para 2 casas decimais
        valor = round(valor, 2)
        
        # 4. Limitar valor máximo por transação (anti-lavagem)
        LIMITE_MAXIMO = 50000.00
        if valor > LIMITE_MAXIMO:
            embed = discord.Embed(
                title='❌ Limite Excedido',
                description=f'O valor máximo por transação é 💵 {LIMITE_MAXIMO:.2f}\n\n'
                           f'Para valores maiores, faça múltiplas transações.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # 5. Verificar saldo do remetente
        remetente = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        
        if remetente['saldo'] < valor:
            embed = discord.Embed(
                title='❌ Saldo Insuficiente',
                description=f'Você precisa de 💵 {valor:.2f}\n'
                           f'Saldo disponível: 💵 {remetente["saldo"]:.2f}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # 6. Criar ou verificar destinatário
        dest = db.obter_ou_criar_usuario(destinatario.id, destinatario.name)
        
        # ========== TAXA DE TRANSAÇÃO (1%) ==========
        TAXA_PERCENTUAL = 0.01  # 1%
        taxa = round(valor * TAXA_PERCENTUAL, 2)
        valor_liquido = valor - taxa
        
        # ========== CONFIRMAÇÃO INTERATIVA ==========
        
        # Criar embed de confirmação
        embed_confirmacao = discord.Embed(
            title='🔐 Confirmação de PIX',
            description='Revise os detalhes da transação antes de confirmar:',
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed_confirmacao.add_field(
            name='📤 Remetente',
            value=f'{ctx.author.mention}\n💵 Saldo atual: {remetente["saldo"]:.2f}',
            inline=False
        )
        
        embed_confirmacao.add_field(
            name='📥 Destinatário',
            value=f'{destinatario.mention}',
            inline=False
        )
        
        embed_confirmacao.add_field(
            name='💰 Valor',
            value=f'**{valor:.2f}**',
            inline=True
        )
        
        embed_confirmacao.add_field(
            name='💳 Taxa (1%)',
            value=f'{taxa:.2f}',
            inline=True
        )
        
        embed_confirmacao.add_field(
            name='✨ Valor Líquido',
            value=f'**{valor_liquido:.2f}**',
            inline=True
        )
        
        if descricao:
            embed_confirmacao.add_field(
                name='📝 Descrição',
                value=descricao[:200],  # Limitar a 200 caracteres
                inline=False
            )
        
        embed_confirmacao.add_field(
            name='💵 Novo Saldo',
            value=f'{remetente["saldo"] - valor:.2f}',
            inline=False
        )
        
        embed_confirmacao.set_footer(
            text='Digite "confirmar" para completar ou "cancelar" para abortar (30s)'
        )
        
        await ctx.send(embed=embed_confirmacao)
        
        # ========== AGUARDAR CONFIRMAÇÃO ==========
        
        def check(m):
            return (
                m.author.id == ctx.author.id and 
                m.channel.id == ctx.channel.id and
                m.content.lower() in ['confirmar', 'cancelar', 'sim', 'não', 'nao']
            )
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            
            if msg.content.lower() in ['cancelar', 'não', 'nao']:
                embed_cancelado = discord.Embed(
                    title='❌ Transação Cancelada',
                    description='O PIX foi cancelado pelo remetente.',
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed_cancelado)
                return
            
        except Exception:
            embed_timeout = discord.Embed(
                title='⏰ Tempo Esgotado',
                description='Transação cancelada por timeout (30s).',
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed_timeout)
            return
        
        # ========== EXECUTAR TRANSAÇÃO ==========
        
        try:
            # Verificar saldo novamente (pode ter mudado durante confirmação)
            remetente_atualizado = db.obter_usuario(ctx.author.id)
            if remetente_atualizado['saldo'] < valor:
                embed = discord.Embed(
                    title='❌ Saldo Insuficiente',
                    description='Seu saldo mudou durante a confirmação!',
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            # Debitar do remetente (valor total = valor + taxa já incluída)
            db.atualizar_saldo(
                ctx.author.id,
                -valor,
                'pix_enviado',
                f'PIX para {destinatario.name}: {descricao or "Sem descrição"}'
            )
            
            # Registrar taxa de transação
            db.registrar_transacao(
                ctx.author.id,
                -taxa,
                'taxa_pix',
                remetente_atualizado['saldo'] - valor,
                remetente_atualizado['saldo'] - valor,
                f'Taxa de 1% sobre PIX de {valor:.2f}'
            )
            
            # Creditar ao destinatário (valor líquido, sem a taxa)
            db.atualizar_saldo(
                destinatario.id,
                valor_liquido,
                'pix_recebido',
                f'PIX de {ctx.author.name}: {descricao or "Sem descrição"}'
            )
            
            # Registrar transação PIX completa na coleção específica
            db.registrar_transacao_pix(
                remetente_id=ctx.author.id,
                remetente_nome=ctx.author.name,
                destinatario_id=destinatario.id,
                destinatario_nome=destinatario.name,
                valor_bruto=valor,
                taxa=taxa,
                valor_liquido=valor_liquido,
                descricao=descricao or "Sem descrição",
                servidor_id=ctx.guild.id if ctx.guild else None,
                servidor_nome=ctx.guild.name if ctx.guild else "DM",
                canal_id=ctx.channel.id,
                mensagem_id=ctx.message.id
            )
            
            # Adicionar experiência
            db.adicionar_experiencia(ctx.author.id, 10)
            db.adicionar_experiencia(destinatario.id, 5)
            
            # ========== EMBED DE SUCESSO ==========
            
            embed_sucesso = discord.Embed(
                title='✅ PIX Realizado com Sucesso!',
                description='Transação processada e registrada no sistema.',
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed_sucesso.add_field(
                name='📤 De',
                value=f'{ctx.author.mention}',
                inline=True
            )
            
            embed_sucesso.add_field(
                name='📥 Para',
                value=f'{destinatario.mention}',
                inline=True
            )
            
            embed_sucesso.add_field(
                name='💰 Valor',
                value=f'{valor:.2f}',
                inline=True
            )
            
            embed_sucesso.add_field(
                name='💳 Taxa',
                value=f'{taxa:.2f}',
                inline=True
            )
            
            embed_sucesso.add_field(
                name='✨ Recebido',
                value=f'{valor_liquido:.2f}',
                inline=True
            )
            
            embed_sucesso.add_field(
                name='📊 Novo Saldo (Remetente)',
                value=f'💵 {remetente_atualizado["saldo"] - valor:.2f}',
                inline=True
            )
            
            if descricao:
                embed_sucesso.add_field(
                    name='📝 Descrição',
                    value=descricao[:200],
                    inline=False
                )
            
            embed_sucesso.set_footer(text=f'ID da Transação registrado | Use !extrato para verificar')
            
            await ctx.send(embed=embed_sucesso)
            
            # ========== NOTIFICAR DESTINATÁRIO ==========
            
            try:
                embed_notificacao = discord.Embed(
                    title='💰 Você Recebeu um PIX!',
                    description=f'Você recebeu uma transferência de {ctx.author.mention}',
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                embed_notificacao.add_field(
                    name='💵 Valor Recebido',
                    value=f'**{valor_liquido:.2f}**',
                    inline=False
                )
                
                if descricao:
                    embed_notificacao.add_field(
                        name='📝 Descrição',
                        value=descricao[:200],
                        inline=False
                    )
                
                embed_notificacao.add_field(
                    name='🏦 Servidor',
                    value=ctx.guild.name if ctx.guild else 'DM',
                    inline=False
                )
                
                embed_notificacao.set_footer(text='Use !extrato para ver o histórico completo')
                
                await destinatario.send(embed=embed_notificacao)
            except:
                # Usuário pode ter DMs desativadas
                pass
            
        except Exception as e:
            embed_erro = discord.Embed(
                title='❌ Erro na Transação',
                description=f'Ocorreu um erro ao processar o PIX.\n\n**Erro:** {str(e)}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed_erro)
            print(f'Erro no PIX: {e}')
    
    @commands.command(name='pix_historico', help='Ver histórico completo de PIX enviados e recebidos')
    async def pix_historico(self, ctx, limite: int = 10):
        """Ver histórico de PIX (enviados e recebidos)"""
        
        # Validar limite
        if limite < 1 or limite > 50:
            limite = 10
        
        historico = db.obter_historico_pix(ctx.author.id, limite)
        
        if not historico:
            embed = discord.Embed(
                title='📋 Histórico Vazio',
                description='Você ainda não realizou nenhuma transação PIX.',
                color=discord.Color.gray()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f'📊 Histórico PIX de {ctx.author.name}',
            description=f'Últimas {len(historico)} transações',
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for trans in historico:
            data = trans['data']
            if isinstance(data, str):
                data = datetime.fromisoformat(data)
            
            # Determinar se foi enviado ou recebido
            if trans['remetente_id'] == ctx.author.id:
                tipo_emoji = '📤'
                tipo_texto = 'ENVIADO'
                outro_usuario = trans['destinatario_nome']
                valor_display = f'-{trans["valor_bruto"]:.2f}'
            else:
                tipo_emoji = '📥'
                tipo_texto = 'RECEBIDO'
                outro_usuario = trans['remetente_nome']
                valor_display = f'+{trans["valor_liquido"]:.2f}'
            
            embed.add_field(
                name=f'{tipo_emoji} {tipo_texto} - {data.strftime("%d/%m/%y %H:%M")}',
                value=(
                    f'**{outro_usuario}**\n'
                    f'💵 {valor_display}\n'
                    f'📝 {trans["descricao"][:50]}'
                ),
                inline=False
            )
        
        embed.set_footer(text='Use !extrato para ver todas as transações')
        
        await ctx.send(embed=embed)
    
    @commands.command(name='pix_stats', help='Ver estatísticas de PIX')
    async def pix_stats(self, ctx):
        """Ver estatísticas de PIX do usuário"""
        
        stats = db.obter_estatisticas_pix(ctx.author.id)
        
        embed = discord.Embed(
            title=f'📊 Estatísticas PIX de {ctx.author.name}',
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name='📤 PIX Enviados',
            value=f'{stats["total_enviados"]}\n💵 {stats["valor_total_enviado"]:.2f}',
            inline=True
        )
        
        embed.add_field(
            name='📥 PIX Recebidos',
            value=f'{stats["total_recebidos"]}\n💵 {stats["valor_total_recebido"]:.2f}',
            inline=True
        )
        
        embed.add_field(
            name='💳 Taxas Pagas',
            value=f'💵 {stats["total_taxas"]:.2f}',
            inline=True
        )
        
        embed.add_field(
            name='📊 Balanço Líquido',
            value=f'💵 {stats["balanco"]:.2f}',
            inline=False
        )
        
        if stats['maior_pix_enviado']:
            embed.add_field(
                name='🏆 Maior PIX Enviado',
                value=f'💵 {stats["maior_pix_enviado"]:.2f}',
                inline=True
            )
        
        if stats['maior_pix_recebido']:
            embed.add_field(
                name='🎁 Maior PIX Recebido',
                value=f'💵 {stats["maior_pix_recebido"]:.2f}',
                inline=True
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pix(bot))
