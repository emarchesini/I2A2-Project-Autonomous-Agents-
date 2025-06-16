# NF Agent UI

Interface web moderna desenvolvida com Vue.js 3 e Vuetify 3 que integra os serviços Load Service e NF Agent, proporcionando uma experiência unificada para upload de notas fiscais e interação com o agente inteligente.

## 🚀 Funcionalidades

### Upload de Arquivos
- **Drag & Drop**: Interface intuitiva para arrastar e soltar arquivos
- **Validação**: Suporte para arquivos .xml e .zip (máx. 100MB)
- **Progress Tracking**: Barra de progresso em tempo real
- **Feedback Visual**: Notificações de sucesso/erro detalhadas

### Chat com NF Agent
- **Interface Conversacional**: Chat em tempo real com o agente
- **Streaming**: Respostas em tempo real via Server-Sent Events
- **Estado Condicional**: Habilitado apenas após upload bem-sucedido
- **Histórico**: Mantém histórico da conversa durante a sessão

### Monitoramento do Sistema
- **Status dos Serviços**: Indicadores visuais do status dos serviços
- **Status do Banco**: Informações sobre registros e última atualização
- **Métricas**: Contadores de notas fiscais e itens processados

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Vue.js 3 +    │    │  Load Service   │    │   NF Agent      │
│   Vuetify 3     │◄──►│   (FastAPI)     │    │   (AutoGen)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │                 │
                    │   PostgreSQL    │
                    │   Database      │
                    │                 │
                    └─────────────────┘
```

## 🛠️ Tecnologias

- **Frontend**: Vue.js 3 (Composition API)
- **UI Framework**: Vuetify 3 (Material Design)
- **State Management**: Pinia
- **Build Tool**: Vite
- **HTTP Client**: Axios
- **Routing**: Vue Router 4
- **Icons**: Material Design Icons
- **Container**: Nginx (Alpine)

## 📦 Estrutura do Projeto

```
services/ui/
├── src/
│   ├── components/          # Componentes reutilizáveis
│   │   ├── FileUpload.vue   # Upload de arquivos
│   │   ├── DatabaseStatus.vue # Status do banco
│   │   └── AgentChat.vue    # Interface de chat
│   ├── views/               # Views/páginas
│   │   └── Home.vue         # Página principal
│   ├── stores/              # Stores Pinia
│   │   └── system.js        # Estado do sistema
│   ├── App.vue              # Componente raiz
│   └── main.js              # Entry point
├── public/                  # Arquivos estáticos
├── package.json             # Dependências
├── vite.config.js           # Configuração Vite
├── Dockerfile               # Container Docker
├── nginx.conf               # Configuração Nginx
└── README.md                # Documentação
```

## 🔧 Configuração

### Variáveis de Ambiente (via Nginx Proxy)

O serviço UI não usa variáveis de ambiente diretamente, mas se conecta aos serviços backend através de proxy reverso configurado no Nginx:

- `/api/load/*` → Load Service (porta 8000)
- `/api/agent/*` → NF Agent Service (porta 8001)

### Endpoints Utilizados

#### Load Service
- `GET /api/load/health` - Health check
- `GET /api/load/status` - Status do banco de dados
- `POST /api/load/upload/` - Upload de arquivos

#### NF Agent Service
- `GET /api/agent/` - Health check
- `POST /api/agent/tasks/` - Criar nova tarefa
- `POST /api/agent/tasks/{id}/stream` - Stream de respostas
- `POST /api/agent/tasks/{id}/input` - Enviar input para tarefa

## 🚀 Execução

### Desenvolvimento Local

```bash
# Instalar dependências
npm install

# Executar em modo desenvolvimento
npm run dev

# Build para produção
npm run build

# Preview da build
npm run preview
```

### Docker

```bash
# Build da imagem
docker build -t nf-agent-ui .

# Executar container
docker run -p 8080:8080 nf-agent-ui
```

### Docker Compose

```bash
# Executar todos os serviços
docker-compose up -d

# Acessar a interface
open http://localhost:8080
```

## 🎯 Fluxo de Uso

1. **Verificação de Status**: A interface verifica automaticamente o status dos serviços
2. **Upload de Arquivos**: Usuário faz upload de arquivos XML/ZIP de notas fiscais
3. **Processamento**: Load Service processa e popula o banco de dados
4. **Habilitação do Chat**: Chat é habilitado automaticamente após upload bem-sucedido
5. **Interação com Agent**: Usuário pode fazer perguntas e solicitar análises
6. **Respostas em Tempo Real**: Agent responde via streaming com análises dos dados

## 🔒 Segurança

- **Headers de Segurança**: CSP, XSS Protection, Frame Options
- **CORS**: Configurado para permitir comunicação entre serviços
- **Validação de Arquivos**: Tipos e tamanhos validados no frontend e backend
- **Proxy Reverso**: Nginx atua como proxy para os serviços backend

## 📊 Monitoramento

- **Health Checks**: Endpoint `/health` para verificação de status
- **Logs**: Logs do Nginx para acesso e erros
- **Métricas**: Interface mostra métricas em tempo real do sistema

## 🎨 Interface

### Características da UI

- **Design Responsivo**: Funciona em desktop, tablet e mobile
- **Material Design**: Seguindo as diretrizes do Material Design 3
- **Tema Claro**: Interface limpa e profissional
- **Feedback Visual**: Indicadores de status, loading states e notificações
- **Acessibilidade**: Suporte a leitores de tela e navegação por teclado

### Componentes Principais

1. **Header**: Título da aplicação e status geral do sistema
2. **Upload Section**: Área de upload com drag & drop
3. **Database Status**: Cards com métricas e status detalhado
4. **Chat Interface**: Chat em tempo real com o agente
5. **Footer**: Informações de copyright

## 🔄 Estados da Aplicação

- **Serviços Offline**: Interface mostra status offline e desabilita funcionalidades
- **Upload em Progresso**: Barra de progresso e botões desabilitados
- **Chat Desabilitado**: Overlay explicativo quando chat não está disponível
- **Chat Ativo**: Interface completa de chat com histórico e input

## 📱 Responsividade

- **Desktop**: Layout de duas colunas (upload + chat)
- **Tablet**: Layout adaptativo com cards empilhados
- **Mobile**: Layout de coluna única com navegação otimizada

## 🐛 Troubleshooting

### Problemas Comuns

1. **Serviços Offline**: Verificar se Load Service e NF Agent estão rodando
2. **Upload Falha**: Verificar tamanho e formato dos arquivos
3. **Chat Não Habilita**: Verificar se banco foi populado com sucesso
4. **Streaming Não Funciona**: Verificar configuração de proxy do Nginx

### Logs

```bash
# Logs do container UI
docker-compose logs ui

# Logs do Nginx
docker-compose exec ui tail -f /var/log/nginx/access.log
docker-compose exec ui tail -f /var/log/nginx/error.log
``` 