# ============================================================================
# API B3 - INTEGRAÇÃO COM BRAPI.DEV
# ============================================================================

import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

load_dotenv()
BRAPI_TOKEN = os.getenv('BRAPI_TOKEN', '')  # Gratuito sem token
BRAPI_URL = 'https://brapi.dev/api'

class BrapiAPI:
    def __init__(self, token=''):
        self.token = token
        self.base_url = BRAPI_URL
        self.cache = {}
        self.cache_tempo = {}  # Controlar tempo de cache
    
    def _fazer_requisicao(self, endpoint, params=None):
        """Fazer requisição à API Brapi"""
        if params is None:
            params = {}
        
        if self.token:
            params['token'] = self.token
        
        try:
            url = f'{self.base_url}{endpoint}'
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f'Erro na requisição Brapi: {e}')
            return None
    
    def _cache_valido(self, chave, minutos=5):
        """Verificar se cache ainda é válido"""
        if chave not in self.cache_tempo:
            return False
        
        tempo_decorrido = (datetime.now() - self.cache_tempo[chave]).total_seconds() / 60
        return tempo_decorrido < minutos
    
    def obter_cotacao(self, ticker, usar_cache=True):
        """Obter cotação atual de uma ação"""
        if usar_cache and self._cache_valido(f'cotacao_{ticker}'):
            return self.cache.get(f'cotacao_{ticker}')
        
        response = self._fazer_requisicao(
            '/quote/list',
            {'search': ticker, 'limit': 1}
        )
        
        if response and 'stocks' in response and len(response['stocks']) > 0:
            cotacao = response['stocks'][0]
            self.cache[f'cotacao_{ticker}'] = cotacao
            self.cache_tempo[f'cotacao_{ticker}'] = datetime.now()
            return cotacao
        
        return None
    
    def obter_cotacoes_multiplas(self, tickers):
        """Obter cotações de múltiplas ações"""
        tickers_str = ','.join(tickers)
        response = self._fazer_requisicao(
            f'/quote/{tickers_str}'
        )
        
        if response and 'results' in response:
            return response['results']
        return []
    
    def listar_acoes_setor(self, setor='', limite=50):
        """Listar ações por setor"""
        params = {'limit': limite}
        if setor:
            params['sector'] = setor
        
        response = self._fazer_requisicao('/quote/list', params)
        
        if response and 'stocks' in response:
            return response['stocks']
        return []
    
    def obter_setores(self):
        """Obter lista de setores disponíveis"""
        response = self._fazer_requisicao('/quote/list', {'limit': 1})
        
        if response and 'availableSectors' in response:
            return response['availableSectors']
        return []
    
    def obter_preco_atual(self, ticker):
        """Obter apenas o preço atual de uma ação"""
        cotacao = self.obter_cotacao(ticker)
        if cotacao:
            return cotacao.get('regularMarketPrice', 0)
        return 0
    
    def obter_dados_fundamentalistas(self, ticker):
        """Obter dados fundamentalistas (requer módulo)"""
        response = self._fazer_requisicao(
            f'/quote/{ticker}',
            {'module': 'fundamentalData'}
        )
        
        if response and 'results' in response and len(response['results']) > 0:
            return response['results'][0].get('fundamentalData', {})
        return {}
    
    def validar_ticker(self, ticker):
        """Validar se ticker existe na B3"""
        cotacao = self.obter_cotacao(ticker, usar_cache=False)
        return cotacao is not None

# Instância global
brapi = BrapiAPI(BRAPI_TOKEN)
