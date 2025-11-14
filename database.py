import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/economia_bot_b3')

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
            self.client.admin.command('ping')
            self.db = self.client['economia_bot_b3']
            
            # Coleções principais
            self.usuarios = self.db['usuarios']
            self.transacoes = self.db['transacoes']
            self.investimentos = self.db['investimentos']
            self.pix_transacoes = self.db['pix_transacoes']
            self.usuario_bloqueado_pix = self.db['usuario_bloqueado_pix']
            
            print("✅ Conectado ao MongoDB com sucesso!")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ Erro ao conectar ao MongoDB: {e}")
            raise

    # ===== USUÁRIOS =====
    def criar_usuario(self, user_id, nome_usuario):
        usuario = {
            'user_id': user_id,
            'nome': nome_usuario,
            'saldo': 1000.00,
            'xp': 0,
            'nivel': 1,
            'streak_daily': 0,
            'data_criacao': datetime.now()
        }
        self.usuarios.update_one({'user_id': user_id}, {'$set': usuario}, upsert=True)
        return usuario

    def obter_usuario(self, user_id):
        usuario = self.usuarios.find_one({'user_id': user_id})
        if not usuario:
            return self.criar_usuario(user_id, f"User{user_id}")
        return usuario

    def atualizar_saldo(self, user_id, valor):
        usuario = self.obter_usuario(user_id)
        novo_saldo = usuario.get('saldo', 0) + valor
        self.usuarios.update_one({'user_id': user_id}, {'$set': {'saldo': novo_saldo}})
        return novo_saldo

    def definir_saldo(self, user_id, valor):
        self.usuarios.update_one({'user_id': user_id}, {'$set': {'saldo': valor}}, upsert=True)

    def obter_saldo(self, user_id):
        usuario = self.obter_usuario(user_id)
        return usuario.get('saldo', 0)

    def adicionar_xp(self, user_id, xp):
        self.usuarios.update_one({'user_id': user_id}, {'$inc': {'xp': xp}}, upsert=True)

    def adicionar_nivel(self, user_id):
        self.usuarios.update_one({'user_id': user_id}, {'$inc': {'nivel': 1}}, upsert=True)

    # ===== TRANSAÇÕES =====
    def registrar_transacao(self, user_id, tipo, valor, descricao=""):
        transacao = {
            'user_id': user_id,
            'tipo': tipo,
            'valor': valor,
            'descricao': descricao,
            'data': datetime.now()
        }
        self.transacoes.insert_one(transacao)
        return transacao

    def obter_historico(self, user_id, limite=10):
        return list(self.transacoes.find({'user_id': user_id}).sort('data', -1).limit(limite))

    def obter_extrato(self, user_id, limite=50):
        return list(self.transacoes.find({'user_id': user_id}).sort('data', -1).limit(limite))

    # ===== INVESTIMENTOS =====
    def obter_carteira(self, user_id):
        carteira = self.investimentos.find_one({'user_id': user_id})
        if not carteira:
            carteira = {'user_id': user_id, 'acoes': {}}
            self.investimentos.insert_one(carteira)
        return carteira.get('acoes', {})

    def adicionar_acao(self, user_id, ticker, quantidade, preco_compra):
        carteira = self.investimentos.find_one({'user_id': user_id})
        if not carteira:
            carteira = {'user_id': user_id, 'acoes': {}}
            self.investimentos.insert_one(carteira)
        
        if ticker not in carteira['acoes']:
            carteira['acoes'][ticker] = {'quantidade': 0, 'preco_medio': 0}
        
        acao = carteira['acoes'][ticker]
        quantidade_total = acao['quantidade'] + quantidade
        preco_medio = ((acao['quantidade'] * acao['preco_medio']) + (quantidade * preco_compra)) / quantidade_total
        
        self.investimentos.update_one(
            {'user_id': user_id},
            {'$set': {f'acoes.{ticker}': {'quantidade': quantidade_total, 'preco_medio': preco_medio}}}
        )

    def vender_acao(self, user_id, ticker, quantidade):
        carteira = self.investimentos.find_one({'user_id': user_id})
        if not carteira or ticker not in carteira['acoes']:
            return False
        
        acao = carteira['acoes'][ticker]
        if acao['quantidade'] < quantidade:
            return False
        
        nova_quantidade = acao['quantidade'] - quantidade
        if nova_quantidade == 0:
            self.investimentos.update_one({'user_id': user_id}, {'$unset': {f'acoes.{ticker}': 1}})
        else:
            self.investimentos.update_one({'user_id': user_id}, {'$set': {f'acoes.{ticker}.quantidade': nova_quantidade}})
        
        return True

    # ===== PIX =====
    def registrar_transacao_pix(self, remetente_id, remetente_nome, destinatario_id, destinatario_nome, valor_bruto, taxa, valor_liquido, descricao, servidor_id, servidor_nome, canal_id, mensagem_id):
        transacao_pix = {
            'remetente_id': remetente_id,
            'remetente_nome': remetente_nome,
            'destinatario_id': destinatario_id,
            'destinatario_nome': destinatario_nome,
            'valor_bruto': valor_bruto,
            'taxa': taxa,
            'valor_liquido': valor_liquido,
            'descricao': descricao,
            'data': datetime.now(),
            'servidor_id': servidor_id,
            'servidor_nome': servidor_nome,
            'canal_id': canal_id,
            'mensagem_id': mensagem_id,
            'status': 'concluido'
        }
        self.pix_transacoes.insert_one(transacao_pix)
        return transacao_pix

    def obter_historico_pix(self, user_id, limite=10):
        enviados = list(self.pix_transacoes.find({'remetente_id': user_id}).sort('data', -1).limit(limite))
        recebidos = list(self.pix_transacoes.find({'destinatario_id': user_id}).sort('data', -1).limit(limite))
        return {'enviados': enviados, 'recebidos': recebidos}

    def obter_estatisticas_pix(self, user_id):
        enviados = list(self.pix_transacoes.find({'remetente_id': user_id}))
        recebidos = list(self.pix_transacoes.find({'destinatario_id': user_id}))
        
        total_enviado = sum([pix['valor_bruto'] for pix in enviados])
        total_recebido = sum([pix['valor_liquido'] for pix in recebidos])
        total_taxas = sum([pix['taxa'] for pix in enviados])
        
        return {
            'pix_enviados': len(enviados),
            'pix_recebidos': len(recebidos),
            'valor_total_enviado': total_enviado,
            'valor_total_recebido': total_recebido,
            'taxas_pagas': total_taxas,
            'balanço_liquido': total_recebido - total_enviado
        }

    def obter_pix_suspeitos(self):
        # PIX de alto valor
        alto_valor = list(self.pix_transacoes.find({'valor_bruto': {'$gt': 10000}}))
        
        # Usuários muito ativos
        usuarios_ativos = {}
        for pix in self.pix_transacoes.find():
            remetente = pix['remetente_id']
            if remetente not in usuarios_ativos:
                usuarios_ativos[remetente] = 0
            usuarios_ativos[remetente] += 1
        
        hiperativos = [{'user_id': uid, 'count': count} for uid, count in usuarios_ativos.items() if count > 20]
        
        return {'alto_valor': alto_valor, 'usuarios_hiperativos': hiperativos}

    def obter_relatorio_pix_servidor(self, dias=30):
        from datetime import timedelta
        data_limite = datetime.now() - timedelta(days=dias)
        transacoes = list(self.pix_transacoes.find({'data': {'$gte': data_limite}}))
        
        total_transacoes = len(transacoes)
        volume_total = sum([pix['valor_bruto'] for pix in transacoes])
        taxas_arrecadadas = sum([pix['taxa'] for pix in transacoes])
        
        return {
            'total_transacoes': total_transacoes,
            'volume_total': volume_total,
            'taxas_arrecadadas': taxas_arrecadadas,
            'ticket_medio': volume_total / total_transacoes if total_transacoes > 0 else 0,
            'transacoes': transacoes
        }

    def bloquear_usuario_pix(self, user_id, motivo):
        self.usuario_bloqueado_pix.insert_one({'user_id': user_id, 'motivo': motivo, 'data': datetime.now()})

    def desbloquear_usuario_pix(self, user_id):
        self.usuario_bloqueado_pix.delete_one({'user_id': user_id})

    def verificar_bloqueio_pix(self, user_id):
        return self.usuario_bloqueado_pix.find_one({'user_id': user_id}) is not None

    # ===== RANKING =====
    def obter_ranking(self, limite=10):
        usuarios = list(self.usuarios.find().sort('saldo', -1).limit(limite))
        return usuarios

    def obter_top_xp(self, limite=10):
        usuarios = list(self.usuarios.find().sort('xp', -1).limit(limite))
        return usuarios

db = Database()
