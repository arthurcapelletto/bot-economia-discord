# ============================================================================
# ESTRUTURA DO PROJETO
# ============================================================================

Seu bot de economia B3 está estruturado da seguinte forma:

```
bot_economia_b3/
│
├── bot_economia_b3.py          # Arquivo principal do bot
├── database.py                 # Integração com MongoDB
├── brapi_client.py             # Cliente para API da B3
├── requirements.txt            # Dependências Python
├── .env                        # Configurações (token, credenciais)
│
└── cogs/
    ├── economia/
    │   └── economia.py         # Saldo, Daily, Perfil, Ranking
    │
    ├── investimentos/
    │   └── investimentos.py     # Comprar/Vender ações B3
    │
    ├── cassino/
    │   └── cassino.py          # Coinflip, Slots, Roleta
    │
    └── apostas/
        └── apostas_pvp.py      # Apostas entre jogadores
```

## Instalação e Configuração

### 1. Clonar ou criar a estrutura
```bash
mkdir bot_economia_b3
cd bot_economia_b3
```

### 2. Criar estrutura de pastas
```bash
mkdir -p cogs/economia cogs/investimentos cogs/cassino cogs/apostas
touch cogs/__init__.py cogs/economia/__init__.py cogs/investimentos/__init__.py cogs/cassino/__init__.py cogs/apostas/__init__.py
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
Edite o arquivo `.env` com suas credenciais:
- `DISCORD_TOKEN`: Token do bot Discord
- `MONGODB_URI`: URI de conexão MongoDB Atlas
- `BRAPI_TOKEN`: Token da API brapi.dev (opcional)

### 5. Executar o bot
```bash
python bot_economia_b3.py
```

---

## Resumo de Comandos

### 📊 Economia Básica
- `!saldo [@usuario]` - Ver saldo
- `!daily` - Resgatar recompensa diária (aleatória 100-500 + bônus streak)
- `!perfil [@usuario]` - Ver perfil
- `!ranking` - Top 10 mais ricos
- `!extrato [@usuario] [limite]` - Histórico de transações
- `!imposto` - Informações sobre sistema de impostos

### 📈 Investimentos (Bolsa B3)
- `!comprar TICKER QUANTIDADE` - Comprar ação da B3 (ex: !comprar PETR4 10)
- `!vender TICKER QUANTIDADE` - Vender ação (com cálculo de imposto)
- `!carteira [@usuario]` - Ver carteira de investimentos
- `!buscar_acao TICKER` - Informações da ação (preço, variação, volume)

### 🎰 Jogos de Cassino
- `!coinflip VALOR [CARA/COROA]` - Cara ou Coroa (2:1)
- `!slots VALOR` - Máquina caça-níqueis (até 10:1)
- `!roleta VALOR [NUMERO 0-36]` - Roleta (36:1)

### 🎯 Apostas entre Jogadores
- `!apostar @usuario VALOR [descricao]` - Desafiar outro jogador
- `!minhas_apostas` - Ver apostas pendentes
- `!definir_vencedor aposta_id @usuario` - Finalizar aposta (admin)

---

## Recursos Principais

✅ **Sistema de Economia Completo**
- Saldo, Daily aleatório, Perfil, Ranking
- Extratos auditáveis com histórico de transações
- Sistema de níveis e experiência
- Streaks de daily com bônus progressivo

✅ **Integração Real com Bolsa B3**
- API brapi.dev para cotações em tempo real
- Compra/venda de ações com histórico
- Cálculo de lucro/prejuízo
- Carteira de investimentos com atualização de preços

✅ **Sistema de Impostos**
- 10% sobre ganhos de jogos/apostas > 1000
- 5% sobre lucro de vendas de ações
- Registro automático no extrato

✅ **Jogos de Cassino Pagos**
- Coinflip, Slots, Roleta com apostas reais
- Multiplicadores de ganho
- Cálculo e desconto automático de impostos

✅ **Apostas entre Jogadores**
- Desafios com valores definíveis
- Bloqueio de saldo durante aposta
- Registro completo de todas as operações

✅ **Segurança e Anti-Fraude**
- Nenhuma transferência direta entre usuários
- Daily apenas para si mesmo
- Bloqueio de saldo em operações pendentes
- Auditoria completa de transações

✅ **Banco de Dados MongoDB**
- Coleções: usuários, transações, investimentos, apostas
- Índices para performance
- Histórico permanente de todas operações

---

## Próximos Passos (Expansão)

1. **Mais Jogos**: Blackjack, Crash, Minas, Quiz, etc.
2. **Sistema de Loja**: Comprar items/roles com moeda
3. **Eventos Temáticos**: Bônus especiais, torneios
4. **Leaderboards Avançados**: Por setor, por tipo de jogo
5. **Dashboard Web**: Visualizar dados em tempo real
6. **Sistema de Referência**: Bônus por convidar amigos
7. **Divisão de Trabalho**: Crime, Trabalho, Roubo com cooldowns
8. **Sistema de Empregos**: Profissões com salários
9. **Mercado de Troca**: Usuários negociando entre si
10. **Alertas de Preço**: Notificações de movimentação de ações

---

## Troubleshooting

**Erro: "Token inválido"**
- Verifique se o DISCORD_TOKEN está correto no .env

**Erro: "Conexão MongoDB recusada"**
- Verifique MONGODB_URI e whitelist de IP no MongoDB Atlas
- Certifique-se de que PyMongo está instalado: `pip install pymongo`

**Erro: "Cog não carregado"**
- Verifique se os arquivos `__init__.py` existem em todas pastas
- Verifique se a função `async def setup(bot)` existe em cada cog

**Erro: "Brapi API error"**
- Tente novamente (pode ser rate limit)
- Se usar token, verifique em https://brapi.dev/dashboard

---

## Licença

Uso livre para fins educacionais e pessoais.

---

**Desenvolvido com ❤️ para economia gamificada em Discord**
