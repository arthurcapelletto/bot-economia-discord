# ============================================================================
# COG: INVESTIMENTOS - Compra/Venda de Ações na Bolsa B3
# ============================================================================

import discord
from discord.ext import commands
from database import db
from brapi_client import brapi
from datetime import datetime

class Investimentos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='comprar', help='Comprar ação da Bolsa B3')
    async def comprar_acao(self, ctx, ticker: str, quantidade: int):
        """Comprar ação"""
        usuario = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        
        # Validar ticker
        cotacao = brapi.obter_cotacao(ticker)
        if not cotacao:
            embed = discord.Embed(
                title='❌ Erro',
                description=f'Ticker {ticker} não encontrado na B3',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        preco = cotacao.get('regularMarketPrice', 0)
        custo_total = preco * quantidade
        
        # Verificar saldo
        if usuario['saldo'] < custo_total:
            embed = discord.Embed(
                title='❌ Saldo Insuficiente',
                description=f'Você precisa de 💵 {custo_total:.2f}, mas tem apenas 💵 {usuario["saldo"]:.2f}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Executar compra
        db.atualizar_saldo(
            ctx.author.id,
            -custo_total,
            'investimento',
            f'Compra de {quantidade} {ticker} @ {preco:.2f}'
        )
        db.comprar_acao(ctx.author.id, ticker, quantidade, preco)
        
        embed = discord.Embed(
            title='✅ Compra Realizada!',
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name='Ativo', value=f'📈 {ticker}', inline=True)
        embed.add_field(name='Quantidade', value=f'📊 {quantidade}', inline=True)
        embed.add_field(name='Preço Unitário', value=f'💵 {preco:.2f}', inline=True)
        embed.add_field(name='Custo Total', value=f'💰 {custo_total:.2f}', inline=True)
        embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] - custo_total:.2f}', inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='vender', help='Vender ação')
    async def vender_acao(self, ctx, ticker: str, quantidade: int):
        """Vender ação"""
        usuario = db.obter_ou_criar_usuario(ctx.author.id, ctx.author.name)
        
        # Verificar se possui ação
        carteira = db.obter_carteira(ctx.author.id)
        investimento = next((inv for inv in carteira if inv['ticker'] == ticker), None)
        
        if not investimento or investimento['quantidade'] < quantidade:
            embed = discord.Embed(
                title='❌ Quantidade Insuficiente',
                description=f'Você não possui {quantidade} {ticker}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Obter preço atual
        cotacao = brapi.obter_cotacao(ticker)
        if not cotacao:
            embed = discord.Embed(
                title='❌ Erro',
                description=f'Não foi possível obter cotação de {ticker}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        preco_atual = cotacao.get('regularMarketPrice', 0)
        receita_total = preco_atual * quantidade
        
        # Calcular lucro/prejuizo e imposto
        custo_medio = investimento['preco_medio']
        custo_investido = custo_medio * quantidade
        lucro = receita_total - custo_investido
        imposto = max(0, int(lucro * 0.05)) if lucro > 0 else 0  # 5% de imposto sobre lucro
        
        receita_liquida = receita_total - imposto
        
        # Executar venda
        db.atualizar_saldo(
            ctx.author.id,
            receita_liquida,
            'venda_acao',
            f'Venda de {quantidade} {ticker} @ {preco_atual:.2f}'
        )
        
        if imposto > 0:
            db.registrar_transacao(
                ctx.author.id,
                -imposto,
                'imposto',
                usuario['saldo'] + receita_total,
                usuario['saldo'] + receita_liquida,
                f'Imposto sobre venda de {ticker}'
            )
        
        db.vender_acao(ctx.author.id, ticker, quantidade)
        
        embed = discord.Embed(
            title='✅ Venda Realizada!',
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name='Ativo', value=f'📈 {ticker}', inline=True)
        embed.add_field(name='Quantidade', value=f'📊 {quantidade}', inline=True)
        embed.add_field(name='Preço Unitário', value=f'💵 {preco_atual:.2f}', inline=True)
        embed.add_field(name='Receita Bruta', value=f'💰 {receita_total:.2f}', inline=True)
        embed.add_field(name='Lucro/Prejuizo', value=f'📊 {lucro:.2f}', inline=True)
        embed.add_field(name='Imposto (5%)', value=f'💼 {imposto:.2f}', inline=True)
        embed.add_field(name='Receita Líquida', value=f'✨ {receita_liquida:.2f}', inline=True)
        embed.add_field(name='Novo Saldo', value=f'💵 {usuario["saldo"] + receita_liquida:.2f}', inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='carteira', help='Ver carteira de investimentos')
    async def carteira(self, ctx, user: discord.User = None):
        """Mostrar carteira de ações"""
        if user is None:
            user = ctx.author
        
        carteira = db.obter_carteira(user.id)
        
        if not carteira:
            embed = discord.Embed(
                title='📊 Carteira Vazia',
                description=f'{user.mention} não possui ações',
                color=discord.Color.gray()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f'📊 Carteira de {user.name}',
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        valor_total = 0
        for inv in carteira:
            cotacao = brapi.obter_cotacao(inv['ticker'])
            if cotacao:
                preco_atual = cotacao.get('regularMarketPrice', inv['preco_medio'])
            else:
                preco_atual = inv['preco_medio']
            
            quantidade = inv['quantidade']
            valor_posicao = preco_atual * quantidade
            valor_total += valor_posicao
            
            lucro = (preco_atual - inv['preco_medio']) * quantidade
            percentual = (lucro / (inv['preco_medio'] * quantidade)) * 100 if inv['preco_medio'] > 0 else 0
            
            sinal_lucro = '📈' if lucro >= 0 else '📉'
            
            embed.add_field(
                name=f'{inv["ticker"]} - {quantidade} ações',
                value=f'💵 {preco_atual:.2f} | Valor: {valor_posicao:.2f}\n{sinal_lucro} Lucro: {lucro:.2f} ({percentual:.2f}%)',
                inline=False
            )
        
        embed.add_field(
            name='💰 Valor Total da Carteira',
            value=f'{valor_total:.2f}',
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='buscar_acao', help='Buscar informações de uma ação')
    async def buscar_acao(self, ctx, ticker: str):
        """Buscar detalhes de uma ação"""
        cotacao = brapi.obter_cotacao(ticker)
        
        if not cotacao:
            embed = discord.Embed(
                title='❌ Ação não encontrada',
                description=f'Ticker {ticker} não existe na B3',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f'📈 {cotacao.get("stock", ticker)}',
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name='Ticker', value=cotacao.get('stock', 'N/A'), inline=True)
        embed.add_field(name='Preço Atual', value=f'💵 {cotacao.get("regularMarketPrice", "N/A")}', inline=True)
        embed.add_field(name='Variação Dia', value=f'{cotacao.get("regularMarketChangePercent", "N/A")}%', inline=True)
        embed.add_field(name='Máxima', value=f'{cotacao.get("regularMarketDayHigh", "N/A")}', inline=True)
        embed.add_field(name='Mínima', value=f'{cotacao.get("regularMarketDayLow", "N/A")}', inline=True)
        embed.add_field(name='Volume', value=f'{cotacao.get("regularMarketVolume", "N/A")}', inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Investimentos(bot))
