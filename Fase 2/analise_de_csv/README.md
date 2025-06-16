# Sistema Integrado NF Agent

Sistema completo para processamento e análise inteligente de Notas Fiscais Eletrônicas, composto por três serviços integrados que proporcionam uma solução end-to-end para upload, processamento e análise de dados fiscais.

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        NF Agent System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │             │    │             │    │             │         │
│  │   UI Web    │◄──►│ Load Service│◄──►│  NF Agent   │         │
│  │ (Vue.js 3)  │    │  (FastAPI)  │    │ (AutoGen)   │         │
│  │             │    │             │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                   │                   │               │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             │                                   │
│                ┌─────────────────┐                              │
│                │                 │                              │
│                │   PostgreSQL    │                              │
│                │   Database      │                              │
│                │                 │                              │
│                └─────────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Serviços

### 1. UI Web Service (Porto 8080)
**Interface web moderna desenvolvida com Vue.js 3 e Vuetify 3**

- **Upload de Arquivos**: Interface drag & drop para arquivos XML/ZIP
- **Chat Inteligente**: Interação em tempo real com o NF Agent
- **Monitoramento**: Status dos serviços e métricas do banco de dados
- **Design Responsivo**: Funciona em desktop, tablet e mobile

**Tecnologias**: Vue.js 3, Vuetify 3, Pinia, Vite, Nginx

### 2. Load Service (Porto 8000)
**API FastAPI para processamento e carga de notas fiscais**

- **Upload de Arquivos**: Recebe arquivos XML e ZIP
- **Processamento**: Extrai e valida dados das notas fiscais
- **Persistência**: Armazena dados estruturados no PostgreSQL
- **APIs REST**: Endpoints para upload e consulta de status

**Tecnologias**: FastAPI, SQLAlchemy, PostgreSQL, Python

### 3. NF Agent Service (Porto 8001)
**Sistema de agentes inteligentes para análise de dados**

- **Organização de Agentes**: Suporta duas configurações de time (`SWARM` e `SELECTOR_GROUP`)
- **Agentes Especializados**: 3 agentes com funções específicas para coordenação, acesso ao banco de dados e sumarização.
- **Análise Inteligente**: Processamento de linguagem natural para responder perguntas sobre os dados fiscais.
- **Integração com Banco**: Consultas SQL automáticas geradas a partir de linguagem natural.
- **Streaming de Respostas**: Respostas são enviadas em tempo real via Server-Sent Events (SSE).

**Tecnologias**: AutoGen, FastAPI, Ollama, Python

## 🎯 Fluxo de Trabalho

1. **Upload**: Usuário faz upload de arquivos via interface web
2. **Processamento**: Load Service processa e armazena no banco
3. **Habilitação**: Chat é automaticamente habilitado
4. **Análise**: Usuário interage com agentes para análises
5. **Resultados**: Respostas inteligentes em tempo real

### Agentes Especializados
A organização de agentes utiliza um time principal composto por 3 agentes com responsabilidades bem definidas:

- **`main_agent`**: O coordenador do time. Recebe a tarefa do usuário, a decompõe em passos menores e delega para os outros agentes.
- **`pg_agent`**: O especialista em banco de dados. É responsável por traduzir requisições em linguagem natural para consultas SQL, executá-las no PostgreSQL e retornar os dados.
- **`summarize_agent`**: O especialista em sumarização. Consolida os dados retornados pelo `pg_agent` em uma resposta final clara e concisa para o usuário.

### Organização dos Agentes
O sistema permite alternar entre duas estratégias de organização dos agentes através da interface web:

- **SWARM (Padrão)**: Uma arquitetura mais simples onde os agentes interagem de forma mais livre. Ideal para tarefas que não seguem um fluxo rígido.
- **SELECTOR_GROUP**: Uma arquitetura mais estruturada onde um "agente seletor" escolhe qual agente deve atuar a seguir, baseado no contexto da conversa. Isso permite um fluxo de trabalho mais controlado e previsível.

## 🖥️ Interface e Uso

A interface web foi projetada para ser intuitiva e centralizar todas as operações do sistema, desde o upload de arquivos até a interação com os agentes inteligentes.

### Componentes Principais

1.  **Painel de Monitoramento (Dashboard)**:
    -   **Status dos Serviços**: Cards que exibem o status em tempo real de cada serviço (`UI`, `Load Service`, `NF Agent`).
    -   **Métricas do Banco de Dados**: Informações vitais sobre os dados processados, como o número total de notas fiscais, o valor total consolidado e a data da última atualização.

2.  **Área de Upload**:
    -   Um componente "Drag & Drop" que permite arrastar e soltar arquivos `.xml` ou `.zip` diretamente na janela.
    -   Fornece feedback visual durante o upload e exibe mensagens de sucesso ou erro após o processamento.

3.  **Terminal de Chat Inteligente**:
    -   **Seletor de Organização de Agentes**: Um menu dropdown que permite escolher a estratégia de colaboração dos agentes (`SWARM` ou `SELECTOR_GROUP`) antes de enviar uma tarefa.
    -   **Input de Tarefas**: O campo de texto principal onde você digita suas perguntas em linguagem natural para os agentes.
    -   **Histórico de Tarefas**: Uma lista das tarefas enviadas, que pode ser expandida para revelar detalhes como a resposta final, a contagem de tokens utilizados e os logs completos da execução.

### Passo a Passo de Utilização

1.  **Verifique o Status**: Ao carregar a página, confira o painel de monitoramento. Todos os serviços devem estar com o status "Online".
2.  **Faça o Upload dos Arquivos**: Arraste um arquivo `.zip` contendo notas fiscais em formato `.xml` (ou arquivos `.xml` individuais) para a área de upload. Aguarde a mensagem de sucesso.
3.  **Aguarde a Habilitação do Chat**: Após o processamento bem-sucedido dos arquivos, o terminal de chat será automaticamente habilitado.
4.  **Escolha a Organização dos Agentes**: No seletor "Agent Organization", escolha entre `SWARM` (padrão, mais flexível) ou `SELECTOR_GROUP` (mais estruturado).
5.  **Interaja com os Agentes**: Digite sua pergunta no campo de input. Exemplos:
    -   *"Qual o valor total das notas emitidas em maio de 2024?"*
    -   *"Liste os 5 produtos mais vendidos."*
    -   *"Quem foi o maior emitente de notas fiscais?"*
6.  **Analise os Resultados**: A sua pergunta aparecerá no histórico. Clique nela para expandir e ver:
    -   **Resposta Final**: A resposta direta e consolidada para sua pergunta.
    -   **Logs do Autogen**: Uma caixa de texto com rolagem contendo todo o diálogo entre os agentes. É útil para entender o "raciocínio" do time ou para depurar problemas.
    -   **Contagem de Tokens**: O custo computacional daquela tarefa específica.

## 🛠️ Configuração e Execução

### Pré-requisitos

- Docker e Docker Compose
- Ollama rodando em `192.168.0.120:11434`
- Imagens MCP: `mcp/filesystem` e `mcp/postgres`

### Execução Completa

```bash
# Clone o repositório
git clone <repository-url>
cd teste_fastapi

# Execute todos os serviços
docker-compose up -d

# Verifique os logs
docker-compose logs -f
```

### Acesso aos Serviços

- **Interface Web**: http://localhost:8080
- **Load Service API**: http://localhost:8000
- **NF Agent API**: http://localhost:8001
- **PostgreSQL**: localhost:5432

### Documentação das APIs

- **Load Service**: http://localhost:8000/docs
- **NF Agent**: http://localhost:8001/docs

## 📊 Funcionalidades Principais

### Upload e Processamento
- Suporte a arquivos XML e ZIP (até 100MB)
- Validação automática de estrutura
- Extração de dados de cabeçalho e itens
- Armazenamento estruturado no PostgreSQL

### Análise Inteligente
- **Consultas em Linguagem Natural**: "Quais os maiores emitentes?"
- **Relatórios Automáticos**: Análises por período, estado, produto
- **Anonimização**: Proteção automática de dados sensíveis
- **Sumarização**: Resumos executivos dos dados

## 🔧 Configuração Avançada

### Variáveis de Ambiente

#### UI Service
Configurado via proxy Nginx (sem variáveis diretas)

#### Load Service
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/notasfiscais
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_NAME=notasfiscais
UPLOAD_DIR=uploads
```

#### NF Agent Service
```env
OLLAMA_HOST=192.168.0.120:11434
OLLAMA_MODEL=mistral:latest
POSTGRES_URL=postgresql://postgres:postgres@host.docker.internal:5432/notasfiscais
FILESYSTEM_MOUNT_PATH=/home/enzo/dev/autogen/fs
MAX_MESSAGES=50
```

#### Modelo Ollama
Altere `OLLAMA_MODEL` no arquivo `docker-compose.yml` para usar diferentes modelos. O padrão é `mistral:latest`.

#### Organização de Agentes
É possível modificar a lógica dos agentes ou criar novas organizações. Os arquivos principais para isso são:
- **`services/nf_agent/agent_manager.py`**: Define a lógica da organização `SWARM`.
- **`services/nf_agent/agent_manager_sel_group.py`**: Define a lógica da organização `SELECTOR_GROUP`.

Para alterar os *system messages* ou as ferramentas de cada agente, modifique os arquivos acima.

## 📈 Monitoramento

### Health Checks
- **UI**: http://localhost:8080/health
- **Load Service**: http://localhost:8000/health
- **NF Agent**: http://localhost:8001/

### Logs
```bash
# Todos os serviços
docker-compose logs -f

# Serviço específico
docker-compose logs -f ui
docker-compose logs -f api
docker-compose logs -f nf_agent
docker-compose logs -f db
```

### Métricas
A interface web mostra métricas em tempo real:
- Status dos serviços
- Número de registros no banco
- Última atualização
- Valor total processado

## 🔒 Segurança

### Dados Sensíveis
- **Anonimização Automática**: Dados pessoais são automaticamente anonimizados
- **Workflow Obrigatório**: Processo de anonimização é mandatório
- **Validação**: Múltiplas camadas de validação de dados

### Rede
- **Proxy Reverso**: Nginx atua como proxy para os serviços
- **CORS**: Configurado adequadamente para comunicação entre serviços
- **Headers de Segurança**: CSP, XSS Protection, Frame Options

## 🔛 Troubleshooting

### Problemas Comuns

1. **Ollama Não Conecta**
   ```bash
   # Verificar se Ollama está rodando
   curl http://192.168.0.120:11434/api/tags
   ```

2. **Banco Não Conecta**
   ```bash
   # Verificar logs do PostgreSQL
   docker-compose logs db
   ```

3. **MCP Tools Não Funcionam**
   ```bash
   # Verificar se imagens MCP existem
   docker images | grep mcp
   ```

4. **Upload Falha**
   - Verificar tamanho do arquivo (máx. 100MB)
   - Verificar formato (apenas .xml e .zip)
   - Verificar logs do Load Service

### Reset Completo
```bash
# Parar todos os serviços
docker-compose down

# Remover volumes (CUIDADO: apaga dados)
docker-compose down -v

# Rebuild e restart
docker-compose up -d --build
```

## 📚 Documentação Adicional

- [Load Service README](services/load_service/README.md)
- [NF Agent README](services/nf_agent/README.md)
- [UI Service README](services/ui/README.md)

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

## 🆘 Suporte

Para suporte e dúvidas:
- Abra uma issue no GitHub
- Consulte a documentação dos serviços individuais
- Verifique os logs para diagnóstico 