from datetime import datetime
from collections import defaultdict

class Database:
    """Database em memória - sem MongoDB"""
    
    def __init__(self):
        # Dados dos usuários
        self.usuarios = {}
        
        # Transações gerais
        self.transacoes_list = []
        
        # Investimentos
        self.investimentos = {}
        
        # PIX
        self.pix_transacoes_list = []
        self.usuarios_bloqueados_pix = set()
        
        print("✅ Database em memória inicializado!")

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
        self.usuarios[user_id] = usuario
        return usuario

    def obter_usuario(self, user_id):
        if user_id not in self.usuarios:
            return self.criar_usuario(user_id, f"User{user_id}")
        return self.usuarios[user_id]

    def atualizar_saldo(self, user_id, valor):
        usuario = self.obter_usuario(user_id)
        novo_saldo = usuario.get('saldo', 0) + valor
        usuario['saldo'] = novo_saldo
        return novo_saldo

    def definir_saldo(self, user_id, valor):
        usuario = self.obter_usuario(user_id)
        usuario['saldo'] = valor

    def obter_saldo(self, user_id):
        usuario = self.obter_usuario(user_id)
        return usuario.get('saldo', 0)

    def adicionar_xp(self, user_id, xp):
        usuario = self.obter_usuario(user_id)
        usuario['xp'] = usuario.get('xp', 0) + xp

    def adicionar_nivel(self, user_id):
        usuario = self.obter_usuario(user_id)
        usuario['nivel'] = usuario.get('nivel', 1) + 1

    # ===== TRANSAÇÕES =====
    def registrar_transacao(self, user_id, tipo, valor, descricao=""):
        transacao = {
            'user_id': user_id,
            'tipo': tipo,
            'valor': valor,
            'descricao': descricao,
            'data': datetime.now()
        }
        self.transacoes_list.append(transacao)
        return transacao

    def obter_historico(self, user_id, limite=10):
        return [t for t in self.transacoes_list if t['user_id'] == user_id][-limite:]

    def obter_extrato(self, user_id, limite=50):
        return [t for t in self.transacoes_list if t['user_id'] == user_id][-limite:]

    # ===== INVESTIMENTOS =====
    def obter_carteira(self, user_id):
        if user_id not in self.investimentos:
            self.investimentos[user_id] = {}
        return self.investimentos[user_id]

    def adicionar_acao(self, user_id, ticker, quantidade, preco_compra):
        carteira = self.obter_carteira(user_id)
        
        if ticker not in carteira:
            carteira[ticker] = {'quantidade': 0, 'preco_medio': 0}
        
        acao = carteira[ticker]
        quantidade_total = acao['quantidade'] + quantidade
        preco_medio = ((acao['quantidade'] * acao['preco_medio']) + (quantidade * preco_compra)) / quantidade_total
        
        carteira[ticker] = {'quantidade': quantidade_total, 'preco_medio': preco_medio}

    def vender_acao(self, user_id, ticker, quantidade):
        carteira = self.obter_carteira(user_id)
        
        if ticker not in carteira:
            return False
        
        acao = carteira[ticker]
        if acao['quantidade'] < quantidade:
            return False
        
        nova_quantidade = acao['quantidade'] - quantidade
        if nova_quantidade == 0:
            del carteira[ticker]
        else:
            carteira[ticker]['quantidade'] = nova_quantidade
        
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
        self.pix_transacoes_list.append(transacao_pix)
        return transacao_pix

    def obter_historico_pix(self, user_id, limite=10):
        enviados = [p for p in self.pix_transacoes_list if p['remetente_id'] == user_id][-limite:]
        recebidos = [p for p in self.pix_transacoes_list if p['destinatario_id'] == user_id][-limite:]
        return {'enviados': enviados, 'recebidos': recebidos}

    def obter_estatisticas_pix(self, user_id):
        enviados = [p for p in self.pix_transacoes_list if p['remetente_id'] == user_id]
        recebidos = [p for p in self.pix_transacoes_list if p['destinatario_id'] == user_id]
        
        total_enviado = sum([p['valor_bruto'] for p in enviados])
        total_recebido = sum([p['valor_liquido'] for p in recebidos])
        total_taxas = sum([p['taxa'] for p in enviados])
        
        return {
            'pix_enviados': len(enviados),
            'pix_recebidos': len(recebidos),
            'valor_total_enviado': total_enviado,
            'valor_total_recebido': total_recebido,
            'taxas_pagas': total_taxas,
            'balanço_liquido': total_recebido - total_enviado
        }

    def obter_pix_suspeitos(self):
        alto_valor = [p for p in self.pix_transacoes_list if p['valor_bruto'] > 10000]
        
        usuarios_ativos = defaultdict(int)
        for pix in self.pix_transacoes_list:
            usuarios_ativos[pix['remetente_id']] += 1
        
        hiperativos = [{'user_id': uid, 'count': count} for uid, count in usuarios_ativos.items() if count > 20]
        
        return {'alto_valor': alto_valor, 'usuarios_hiperativos': hiperativos}

    def obter_relatorio_pix_servidor(self, dias=30):
        transacoes = self.pix_transacoes_list
        
        total_transacoes = len(transacoes)
        volume_total = sum([p['valor_bruto'] for p in transacoes])
        taxas_arrecadadas = sum([p['taxa'] for p in transacoes])
        
        return {
            'total_transacoes': total_transacoes,
            'volume_total': volume_total,
            'taxas_arrecadadas': taxas_arrecadadas,
            'ticket_medio': volume_total / total_transacoes if total_transacoes > 0 else 0,
            'transacoes': transacoes
        }

    def bloquear_usuario_pix(self, user_id, motivo):
        self.usuarios_bloqueados_pix.add(user_id)

    def desbloquear_usuario_pix(self, user_id):
        self.usuarios_bloqueados_pix.discard(user_id)

    def verificar_bloqueio_pix(self, user_id):
        return user_id in self.usuarios_bloqueados_pix

    # ===== RANKING =====
    def obter_ranking(self, limite=10):
        usuarios = sorted(self.usuarios.values(), key=lambda x: x['saldo'], reverse=True)
        return usuarios[:limite]

    def obter_top_xp(self, limite=10):
        usuarios = sorted(self.usuarios.values(), key=lambda x: x['xp'], reverse=True)
        return usuarios[:limite]

# Instância global
db = Database()
