# ============================================================================
# COG: ADMIN PIX - AUDITORIA E CONTROLE (SOMENTE ADMINS)
# ============================================================================

import discord
from discord.ext import commands
from database import db
from datetime import datetime, timedelta
import io
import csv

class AdminPix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='pix_auditoria', help='[ADMIN] Ver auditoria completa de PIX')
    @commands.has_permissions(administrator=True)
    async def pix_auditoria(self, ctx, user: discord.User = None, limite: int = 20):
        """Ver auditoria de PIX de um usuário específico ou servidor"""
        
        if limite < 1 or limite > 100:
            limite = 20
        
        if user:
            # Auditoria de usuário específico
            historico = db.obter_historico_pix(user.id, limite)
            titulo = f'🔍 Auditoria PIX - {user.name}'
        else:
            # Auditoria geral do servidor
            historico = list(
                db.pix_transacoes.find({
                    'servidor_id': ctx.guild.id
                }).sort('data', -1).limit(limite)
            )
            titulo = f'🔍 Auditoria PIX - {ctx.guild.name}'
        
        if not historico:
            embed = discord.Embed(
                title='📋 Sem Dados',
                description='Nenhuma transação PIX encontrada.',
                color=discord.Color.gray()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=titulo,
            description=f'Últimas {len(historico)} transações',
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        for trans in historico[:10]:  # Mostrar apenas 10 no embed
            data = trans['data']
            if isinstance(data, str):
                data = datetime.fromisoformat(data)
            
            try:
                remetente = await self.bot.fetch_user(trans['remetente_id'])
                destinatario = await self.bot.fetch_user(trans['destinatario_id'])
                rem_nome = remetente.mention
                dest_nome = destinatario.mention
            except:
                rem_nome = trans['remetente_nome']
                dest_nome = trans['destinatario_nome']
            
            embed.add_field(
                name=f'📤 {data.strftime("%d/%m/%y %H:%M:%S")}',
                value=(
                    f'**De:** {rem_nome}\n'
                    f'**Para:** {dest_nome}\n'
                    f'💵 Bruto: {trans["valor_bruto"]:.2f} | '
                    f'Taxa: {trans["taxa"]:.2f} | '
                    f'Líquido: {trans["valor_liquido"]:.2f}\n'
                    f'📝 {trans["descricao"][:50]}'
                ),
                inline=False
            )
        
        embed.set_footer(text=f'Mostrando 10 de {len(historico)} | Use !pix_relatorio para CSV completo')
        
        await ctx.send(embed=embed)
    
    @commands.command(name='pix_relatorio', help='[ADMIN] Gerar relatório CSV de PIX')
    @commands.has_permissions(administrator=True)
    async def pix_relatorio(self, ctx, dias: int = 7):
        """Gerar relatório CSV de PIX do servidor"""
        
        if dias < 1 or dias > 365:
            await ctx.send('Período deve ser entre 1 e 365 dias!')
            return
        
        data_inicio = datetime.now() - timedelta(days=dias)
        
        # Buscar todas transações do período
        transacoes = list(
            db.pix_transacoes.find({
                'servidor_id': ctx.guild.id,
                'data': {'$gte': data_inicio}
            }).sort('data', -1)
        )
        
        if not transacoes:
            await ctx.send('Nenhuma transação encontrada no período!')
            return
        
        # Criar CSV em memória
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow([
            'Data/Hora',
            'Remetente ID',
            'Remetente Nome',
            'Destinatário ID',
            'Destinatário Nome',
            'Valor Bruto',
            'Taxa (1%)',
            'Valor Líquido',
            'Descrição',
            'Canal ID',
            'Mensagem ID',
            'Status'
        ])
        
        # Dados
        for trans in transacoes:
            data = trans['data']
            if isinstance(data, str):
                data = datetime.fromisoformat(data)
            
            writer.writerow([
                data.strftime('%Y-%m-%d %H:%M:%S'),
                trans['remetente_id'],
                trans['remetente_nome'],
                trans['destinatario_id'],
                trans['destinatario_nome'],
                f"{trans['valor_bruto']:.2f}",
                f"{trans['taxa']:.2f}",
                f"{trans['valor_liquido']:.2f}",
                trans['descricao'],
                trans.get('canal_id', ''),
                trans.get('mensagem_id', ''),
                trans.get('status', 'concluido')
            ])
        
        # Resetar posição do buffer
        output.seek(0)
        
        # Criar arquivo
        arquivo = discord.File(
            io.BytesIO(output.getvalue().encode('utf-8')),
            filename=f'relatorio_pix_{ctx.guild.name}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
        # Estatísticas do período
        volume_total = sum(t['valor_bruto'] for t in transacoes)
        taxas_total = sum(t['taxa'] for t in transacoes)
        
        embed = discord.Embed(
            title='📊 Relatório PIX Gerado',
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name='Período', value=f'Últimos {dias} dias', inline=False)
        embed.add_field(name='Total de Transações', value=f'{len(transacoes)}', inline=True)
        embed.add_field(name='Volume Total', value=f'💵 {volume_total:.2f}', inline=True)
        embed.add_field(name='Taxas Arrecadadas', value=f'💰 {taxas_total:.2f}', inline=True)
        
        await ctx.send(embed=embed, file=arquivo)
    
    @commands.command(name='pix_suspeitos', help='[ADMIN] Detectar transações suspeitas')
    @commands.has_permissions(administrator=True)
    async def pix_suspeitos(self, ctx):
        """Detectar PIX suspeitos (anti-lavagem)"""
        
        suspeitos = db.obter_pix_suspeitos(limite_valor=10000, limite_quantidade=20)
        
        embed = discord.Embed(
            title='🚨 Transações Suspeitas Detectadas',
            description='Análise anti-lavagem de dinheiro',
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # PIX de alto valor
        if suspeitos['alto_valor']:
            alto_valor_text = []
            for trans in suspeitos['alto_valor'][:5]:
                data = trans['data']
                if isinstance(data, str):
                    data = datetime.fromisoformat(data)
                alto_valor_text.append(
                    f"💵 {trans['valor_bruto']:.2f} - {data.strftime('%d/%m %H:%M')}"
                )
            
            embed.add_field(
                name='💰 PIX de Alto Valor (>10k)',
                value='\n'.join(alto_valor_text) if alto_valor_text else 'Nenhum',
                inline=False
            )
        
        # Usuários muito ativos
        if suspeitos['usuarios_frequentes']:
            frequentes_text = []
            for user_stat in suspeitos['usuarios_frequentes'][:5]:
                try:
                    user = await self.bot.fetch_user(user_stat['_id'])
                    nome = user.mention
                except:
                    nome = f"ID: {user_stat['_id']}"
                
                frequentes_text.append(
                    f"{nome}: {user_stat['total']} PIX | 💵 {user_stat['valor_total']:.2f}"
                )
            
            embed.add_field(
                name='🔥 Usuários Muito Ativos (>20 PIX)',
                value='\n'.join(frequentes_text) if frequentes_text else 'Nenhum',
                inline=False
            )
        
        embed.set_footer(text='⚠️ Revisar manualmente transações suspeitas')
        
        await ctx.send(embed=embed)
    
    @commands.command(name='pix_stats_servidor', help='[ADMIN] Estatísticas gerais do servidor')
    @commands.has_permissions(administrator=True)
    async def pix_stats_servidor(self, ctx, dias: int = 30):
        """Estatísticas de PIX do servidor"""
        
        if dias < 1 or dias > 365:
            dias = 30
        
        data_inicio = datetime.now() - timedelta(days=dias)
        data_fim = datetime.now()
        
        relatorio = db.obter_relatorio_pix_servidor(ctx.guild.id, data_inicio, data_fim)
        
        embed = discord.Embed(
            title=f'📊 Estatísticas PIX - {ctx.guild.name}',
            description=f'Período: Últimos {dias} dias',
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name='📈 Total de Transações',
            value=f"{relatorio.get('total_transacoes', 0)}",
            inline=True
        )
        
        embed.add_field(
            name='💰 Volume Total',
            value=f"{relatorio.get('volume_total', 0):.2f}",
            inline=True
        )
        
        embed.add_field(
            name='💳 Taxas Arrecadadas',
            value=f"{relatorio.get('total_taxas', 0):.2f}",
            inline=True
        )
        
        embed.add_field(
            name='📊 Ticket Médio',
            value=f"{relatorio.get('ticket_medio', 0):.2f}",
            inline=True
        )
        
        # Média por dia
        if relatorio.get('total_transacoes', 0) > 0:
            media_dia = relatorio['total_transacoes'] / dias
            embed.add_field(
                name='📅 Média por Dia',
                value=f"{media_dia:.1f} transações",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='pix_bloquear', help='[ADMIN] Bloquear PIX de um usuário')
    @commands.has_permissions(administrator=True)
    async def pix_bloquear(self, ctx, user: discord.User, motivo: str = "Sem motivo"):
        """Bloquear usuário de fazer PIX"""
        
        usuario = db.obter_ou_criar_usuario(user.id, user.name)
        
        # Adicionar flag de bloqueio
        db.usuarios.update_one(
            {'user_id': user.id},
            {'$set': {'pix_bloqueado': True, 'pix_bloqueio_motivo': motivo}}
        )
        
        embed = discord.Embed(
            title='🔒 Usuário Bloqueado',
            description=f'{user.mention} foi bloqueado de realizar PIX',
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name='Motivo', value=motivo, inline=False)
        
        await ctx.send(embed=embed)
        
        # Notificar usuário
        try:
            dm_embed = discord.Embed(
                title='🔒 Acesso PIX Bloqueado',
                description=f'Seu acesso ao sistema PIX foi bloqueado.',
                color=discord.Color.red()
            )
            dm_embed.add_field(name='Motivo', value=motivo, inline=False)
            dm_embed.add_field(name='Servidor', value=ctx.guild.name, inline=False)
            await user.send(embed=dm_embed)
        except:
            pass
    
    @commands.command(name='pix_desbloquear', help='[ADMIN] Desbloquear PIX de um usuário')
    @commands.has_permissions(administrator=True)
    async def pix_desbloquear(self, ctx, user: discord.User):
        """Desbloquear usuário"""
        
        db.usuarios.update_one(
            {'user_id': user.id},
            {'$set': {'pix_bloqueado': False}, '$unset': {'pix_bloqueio_motivo': ''}}
        )
        
        embed = discord.Embed(
            title='🔓 Usuário Desbloqueado',
            description=f'{user.mention} pode realizar PIX novamente',
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminPix(bot))
