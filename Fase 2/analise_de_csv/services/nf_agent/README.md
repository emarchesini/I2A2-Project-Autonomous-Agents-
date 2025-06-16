# NF Agent Service

Serviço web para execução de tarefas complexas usando um sistema de agentes inteligentes especializados.

## Visão Geral

O NF Agent Service é uma aplicação FastAPI que coordena múltiplos agentes especializados para executar tarefas complexas de forma colaborativa. Cada agente tem capacidades específicas e trabalha em conjunto para resolver problemas que requerem diferentes tipos de expertise.

## Agentes Disponíveis

### 🤖 **main_agent** (Coordenador)
- **Função**: Coordena e distribui tarefas entre os demais agentes
- **Responsabilidades**: 
  - Recebe tarefas complexas do usuário
  - Divide em subtarefas menores
  - Distribui para agentes especializados
  - Monitora progresso e replaneja quando necessário
  - **Garante anonimização de dados sensíveis antes da entrega final**

### 📁 **file_manager** (Gerenciamento de Arquivos)
- **Função**: Operações no sistema de arquivos
- **Capacidades**:
  - Criação, edição e exclusão de arquivos
  - Manipulação de diretórios
  - Leitura e escrita de dados
- **Diretório padrão**: `/data`
- **Formato de tarefa**: `{agent:"file_manager",tarefa:"criar arquivo com dados X"}`

### 🗃️ **pg_agent** (Banco de Dados PostgreSQL)
- **Função**: Consultas e análises em banco de dados PostgreSQL
- **Capacidades**:
  - Execução de queries SQL
  - Consulta de metadados e schemas
  - Análise de dados de notas fiscais
  - Relatórios e estatísticas
- **Banco padrão**: `notasfiscais` (schema `public`)
- **Formato de tarefa**: `{agent:"pg_agent",tarefa:"consultar vendas por período"}`

### 🔒 **anon_agent** (Anonimização de Dados)
- **Função**: Anonimização de informações sensíveis
- **Capacidades**:
  - Identificação de dados pessoais (nomes, endereços, telefones, emails)
  - Substituição por marcadores genéricos
  - Preservação da estrutura e contexto dos dados
  - Documentação das substituições realizadas
- **Formato de tarefa**: `{agent:"anon_agent",tarefa:"anonimizar dados do relatório X"}`
- **Padrões de substituição**:
  - Nomes: `NOME1`, `NOME2`, etc.
  - Endereços: `ENDEREÇO1`, `ENDEREÇO2`, etc.
  - Telefones: `TELEFONE1`, `TELEFONE2`, etc.
  - Emails: `EMAIL1@dominio.com`, `EMAIL2@empresa.com.br`, etc.
- **Nota**: Atualmente funciona sem ferramentas MCP externas, usando apenas capacidades do LLM

### 📝 **summarize_agent** (Sumarização)
- **Função**: Resumo e síntese de conteúdo
- **Capacidades**:
  - Sumarização de textos longos
  - Extração de pontos principais
  - Síntese de informações
- **Limite**: Máximo 200 palavras por resumo
- **Formato de tarefa**: `{agent:"summarize",tarefa:"resumir documento X"}`

### 👤 **user_proxy** (Interação com Usuário)
- **Função**: Interface entre sistema e usuário
- **Capacidades**:
  - Solicita esclarecimentos quando necessário
  - Coleta informações adicionais
  - Facilita comunicação bidirecional

## Recursos Principais

### ✨ **Interação Bidirecional**
- Agentes podem solicitar input do usuário durante execução
- Interface web com modais para captura de input
- Polling automático para detectar solicitações de input
- Feedback visual em tempo real

### 🔄 **Streaming em Tempo Real**
- Acompanhamento da execução em tempo real
- Mensagens dos agentes transmitidas via WebSocket
- Interface responsiva com indicadores de progresso

### 📊 **Gerenciamento de Tarefas**
- Criação e monitoramento de tarefas
- Estados: `pending`, `running`, `completed`, `failed`, `waiting_for_input`
- Histórico completo de execução
- Capacidade de fornecer input durante execução

### 🔒 **Proteção de Dados Sensíveis**
- **Anonimização automática obrigatória** para dados pessoais
- Processo coordenado pelo `main_agent`
- Validação pelo `anon_agent` antes da entrega final
- Rastreabilidade das substituições realizadas

## API Endpoints

### Informações do Serviço
- `GET /` - Status e informações do serviço

### Gerenciamento de Tarefas
- `POST /tasks/` - Criar nova tarefa
- `GET /tasks/` - Listar todas as tarefas
- `GET /tasks/{task_id}` - Obter status de tarefa específica
- `DELETE /tasks/{task_id}` - Excluir tarefa

### Execução e Interação
- `POST /tasks/{task_id}/stream` - Stream de execução em tempo real
- `POST /tasks/{task_id}/input` - Fornecer input para tarefa aguardando

## Banco de Dados de Notas Fiscais

O `pg_agent` trabalha com um banco PostgreSQL contendo dados de Notas Fiscais Eletrônicas (NF-e):

### Tabelas Principais
- **`notasfiscais`**: Dados do cabeçalho das notas fiscais
- **`itensnotafiscal`**: Itens/produtos de cada nota fiscal

### Consultas Comuns
- Análises por emitente/destinatário
- Relatórios por período
- Estatísticas de produtos (NCM, CFOP)
- Análises fiscais (ICMS, IPI, PIS, COFINS)

## Interface Web

Acesse `http://localhost:8001` para usar a interface web que oferece:

- 📝 **Formulário de Criação**: Interface intuitiva para criar tarefas
- 📊 **Lista de Tarefas**: Visualização de todas as tarefas com status
- 🔴 **Streaming ao Vivo**: Acompanhamento em tempo real da execução
- 💬 **Modais de Input**: Captura de input quando solicitado pelos agentes
- ⚡ **Indicadores Visuais**: Status, progresso e feedback em tempo real

## Exemplos de Uso

### Análise de Dados Fiscais com Anonimização
```
"Analise as notas fiscais do mês de janeiro de 2024, identifique os principais emitentes por valor total e crie um relatório resumido anonimizado"
```

### Processamento de Arquivos + Banco + Proteção de Dados
```
"Leia o arquivo CSV na pasta /data, processe os dados e insira no banco de dados, depois gere um relatório de importação com dados anonimizados"
```

### Relatório Executivo com Proteção de Privacidade
```
"Gere um relatório executivo das vendas por região, incluindo análise de clientes, mas garanta que todos os dados pessoais sejam anonimizados"
```

### Anonimização de Documentos Existentes
```
"Leia o arquivo relatório_clientes.txt e crie uma versão anonimizada removendo todas as informações pessoais identificáveis"
```

### Análise Estatística de Produtos
```
"Analise os produtos mais vendidos por NCM no banco de dados e crie um resumo estatístico"
```

## Configuração

### Variáveis de Ambiente
- `OLLAMA_HOST`: Host do servidor Ollama (padrão: 192.168.0.120:11434)
- `POSTGRES_URL`: URL de conexão PostgreSQL
- `FS_DATA_PATH`: Caminho para dados do filesystem

### Dependências
- Docker e Docker Compose
- Servidor Ollama com modelo Mistral
- PostgreSQL com dados de notas fiscais
- Ferramentas MCP (filesystem, postgres)

## Instalação e Execução

```bash
# Via Docker Compose (recomendado)
docker-compose up nf_agent

# Acesso
# API: http://localhost:8001
# Interface Web: http://localhost:8001
# Documentação: http://localhost:8001/docs
```

## Arquitetura

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Interface     │    │   FastAPI        │    │   Agent         │
│   Web           │◄──►│   Server         │◄──►│   Manager       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌─────────────────────────────────┼─────────────────────────────────────────┐
                       │                                 │                                         │
                ┌──────▼──────┐  ┌──────────────┐  ┌────▼─────┐  ┌──────────────┐  ┌─────▼─────┐  ┌──────▼──────┐
                │   main      │  │   file       │  │   pg     │  │  summarize   │  │   anon    │  │ user_proxy  │
                │   agent     │  │  manager     │  │ agent    │  │   agent      │  │   agent   │  │             │
                └─────────────┘  └──────────────┘  └──────────┘  └──────────────┘  └───────────┘  └─────────────┘
                       │                │                │              │                │              │
                ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐  ┌────▼──────┐  ┌─────▼─────┐  ┌─────▼─────┐
                │   Ollama    │  │   Docker    │  │   MCP     │  │   Ollama  │  │   Ollama  │  │   Input   │
                │   LLM       │  │ Filesystem  │  │ Postgres  │  │   LLM     │  │   LLM     │  │ Callback  │
                └─────────────┘  └─────────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘
```

## Proteção de Dados e Privacidade

### 🔒 **Política de Anonimização**
- **Obrigatória**: Todos os dados pessoais devem ser anonimizados antes da entrega
- **Automática**: O `main_agent` coordena o processo de anonimização
- **Validada**: O `anon_agent` confirma a anonimização antes da finalização
- **Rastreável**: Documentação das substituições para auditoria

### 📋 **Tipos de Dados Protegidos**
- Nomes de pessoas físicas
- Endereços residenciais e comerciais
- Números de telefone e celular
- Endereços de email
- Documentos pessoais (CPF, RG, etc.)
- Informações comerciais sensíveis

### ⚠️ **Importante**
O sistema **NUNCA** retorna informações sensíveis sem anonimização. Todas as tarefas que envolvem dados pessoais passam obrigatoriamente pelo processo de anonimização antes da entrega final.

## Logs e Monitoramento

- Logs detalhados via FastAPI logging
- Rastreamento de execução de agentes
- Métricas de performance de tarefas
- Monitoramento de status em tempo real
- **Auditoria de anonimização** para compliance 