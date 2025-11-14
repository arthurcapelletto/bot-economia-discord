# ============================================================================
# BANCO DE DADOS - MONGODB INTEGRATION
# ============================================================================

import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')

class Database:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client['economia_bot_b3']
        self.usuarios = self.db['usuarios']
        self.transacoes = self.db['transacoes']
        self.investimentos = self.db['investimentos']
        self.apostas = self.db['apostas']
        
        # Criar índices
        self._criar_indices()
    
    def _criar_indices(self):
        """Criar índices para melhor performance"""
        self.usuarios.create_index('user_id', unique=True)
        self.transacoes.create_index('user_id')
        self.transacoes.create_index('data')
        self.investimentos.create_index('user_id')
        self.apostas.create_index('user_id')
    
    # ========== USUÁRIOS ==========
    def criar_usuario(self, user_id, username):
        """Criar novo usuário"""
        usuario = {
            'user_id': user_id,
            'username': username,
            'saldo': 1000,  # Saldo inicial
            'saldo_bloqueado': 0,  # Saldo em apostas/jogos
            'nivel': 1,
            'experiencia': 0,
            'ultima_recompensa_daily': None,
            'streak_daily': 0,
            'data_criacao': datetime.now(),
            'perfil': {
                'cor_rank': '#00ff00',
                'titulo': 'Iniciante',
                'badge': '🆕'
            }
        }
        try:
            self.usuarios.insert_one(usuario)
            return usuario
        except:
            return None
    
    def obter_usuario(self, user_id):
        """Obter dados do usuário"""
        return self.usuarios.find_one({'user_id': user_id})
    
    def obter_ou_criar_usuario(self, user_id, username):
        """Obter usuário ou criar se não existir"""
        usuario = self.obter_usuario(user_id)
        if not usuario:
            usuario = self.criar_usuario(user_id, username)
        return usuario
    
    def atualizar_saldo(self, user_id, quantidade, motivo, descricao=""):
        """Atualizar saldo e registrar transação"""
        usuario = self.obter_usuario(user_id)
        if not usuario:
            return False
        
        novo_saldo = usuario['saldo'] + quantidade
        
        # Não permitir saldo negativo (exceto para saque de aposta)
        if novo_saldo < 0 and motivo != 'aposta_perdida':
            return False
        
        # Atualizar saldo
        self.usuarios.update_one(
            {'user_id': user_id},
            {'$set': {'saldo': novo_saldo}}
        )
        
        # Registrar transação
        self.registrar_transacao(
            user_id, 
            quantidade, 
            motivo, 
            usuario['saldo'], 
            novo_saldo,
            descricao
        )
        
        return True
    
    def adicionar_experiencia(self, user_id, xp):
        """Adicionar experiência ao usuário"""
        usuario = self.obter_usuario(user_id)
        if not usuario:
            return False
        
        nova_exp = usuario['experiencia'] + xp
        novo_nivel = usuario['nivel'] + (nova_exp // 1000)  # 1000 XP por nível
        nova_exp = nova_exp % 1000
        
        self.usuarios.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'experiencia': nova_exp,
                    'nivel': novo_nivel
                }
            }
        )
        return True
    
    # ========== TRANSAÇÕES / EXTRATO ==========
    def registrar_transacao(self, user_id, valor, tipo, saldo_anterior, saldo_posterior, descricao=""):
        """Registrar transação no histórico"""
        transacao = {
            'user_id': user_id,
            'valor': valor,
            'tipo': tipo,  # daily, aposta_ganha, aposta_perdida, investimento, venda, imposto, etc
            'saldo_anterior': saldo_anterior,
            'saldo_posterior': saldo_posterior,
            'descricao': descricao,
            'data': datetime.now()
        }
        self.transacoes.insert_one(transacao)
        return transacao
    
    def obter_extrato(self, user_id, limite=50, filtro_tipo=None):
        """Obter histórico de transações do usuário"""
        query = {'user_id': user_id}
        if filtro_tipo:
            query['tipo'] = filtro_tipo
        
        transacoes = list(
            self.transacoes.find(query)
            .sort('data', -1)
            .limit(limite)
        )
        return transacoes
    
    def obter_extrato_data_intervalo(self, user_id, data_inicio, data_fim):
        """Obter transações em um intervalo de datas"""
        return list(
            self.transacoes.find({
                'user_id': user_id,
                'data': {'$gte': data_inicio, '$lte': data_fim}
            }).sort('data', -1)
        )
    
    # ========== INVESTIMENTOS (BOLSA B3) ==========
    def comprar_acao(self, user_id, ticker, quantidade, preco_unitario):
        """Registrar compra de ação"""
        investimento = self.investimentos.find_one({
            'user_id': user_id,
            'ticker': ticker
        })
        
        custo_total = quantidade * preco_unitario
        
        if investimento:
            # Atualizar quantidade e preço médio
            nova_quantidade = investimento['quantidade'] + quantidade
            novo_preco_medio = (
                (investimento['quantidade'] * investimento['preco_medio']) + custo_total
            ) / nova_quantidade
            
            self.investimentos.update_one(
                {'user_id': user_id, 'ticker': ticker},
                {
                    '$set': {
                        'quantidade': nova_quantidade,
                        'preco_medio': novo_preco_medio,
                        'data_ultima_atualizacao': datetime.now()
                    }
                }
            )
        else:
            # Criar novo investimento
            self.investimentos.insert_one({
                'user_id': user_id,
                'ticker': ticker,
                'quantidade': quantidade,
                'preco_medio': preco_unitario,
                'data_compra': datetime.now(),
                'data_ultima_atualizacao': datetime.now()
            })
        
        return True
    
    def vender_acao(self, user_id, ticker, quantidade):
        """Vender ação"""
        investimento = self.investimentos.find_one({
            'user_id': user_id,
            'ticker': ticker
        })
        
        if not investimento or investimento['quantidade'] < quantidade:
            return False
        
        nova_quantidade = investimento['quantidade'] - quantidade
        
        if nova_quantidade == 0:
            # Remover investimento se quantidade for 0
            self.investimentos.delete_one({
                'user_id': user_id,
                'ticker': ticker
            })
        else:
            self.investimentos.update_one(
                {'user_id': user_id, 'ticker': ticker},
                {'$set': {'quantidade': nova_quantidade}}
            )
        
        return True
    
    def obter_carteira(self, user_id):
        """Obter carteira de investimentos do usuário"""
        return list(self.investimentos.find({'user_id': user_id}))
    
    # ========== APOSTAS ==========
    def criar_aposta(self, user_id_apostador, user_id_desafiante, valor, descricao):
        """Criar aposta entre dois jogadores"""
        aposta = {
            'apostador': user_id_apostador,
            'desafiante': user_id_desafiante,
            'valor': valor,
            'descricao': descricao,
            'status': 'pendente',  # pendente, aceita, finalizada
            'vencedor': None,
            'data': datetime.now()
        }
        resultado = self.apostas.insert_one(aposta)
        return resultado.inserted_id
    
    def obter_apostas_pendentes(self, user_id):
        """Obter apostas pendentes do usuário"""
        return list(self.apostas.find({
            'desafiante': user_id,
            'status': 'pendente'
        }))
    
    def finalizar_aposta(self, aposta_id, vencedor_id):
        """Finalizar aposta"""
        self.apostas.update_one(
            {'_id': aposta_id},
            {'$set': {'status': 'finalizada', 'vencedor': vencedor_id}}
        )
    
    # ========== RANKINGS ==========
    def obter_top_ricos(self, limite=10):
        """Obter top 10 usuários mais ricos"""
        return list(
            self.usuarios.find()
            .sort('saldo', -1)
            .limit(limite)
        )
    
    def obter_ranking_nivel(self, limite=10):
        """Obter ranking por nível"""
        return list(
            self.usuarios.find()
            .sort([('nivel', -1), ('experiencia', -1)])
            .limit(limite)
        )

# Instância global
db = Database()
