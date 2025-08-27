# 🏢 Sistema de Processamento VR MENSAL com IA

Sistema inteligente especializado no processamento automático da planilha **VR MENSAL**, combinando regras estáticas de negócio com análise avançada via LLM (Large Language Models) para descoberta e aplicação de regras customizadas baseadas em observações textuais.

## 🎯 Visão Geral

Este sistema processa dados de RH de múltiplas planilhas Excel e gera automaticamente a **planilha VR MENSAL preenchida** com:
- ✅ **Regras Estáticas**: Aplicação automática de todas as regras de negócio tradicionais
- 🤖 **IA Integrada**: Análise inteligente de observações usando Ollama/LLM para descobrir regras customizadas
- 📊 **Validações Automáticas**: Aba de validações com check de todas as regras aplicadas
- 🔍 **Transparência Total**: Documentação completa de todas as decisões e ajustes realizados

## 🚀 Funcionalidades Principais

### 🧠 **Inteligência Artificial Integrada**
- **Análise de Observações**: LLM processa observações textuais das planilhas
- **Descoberta de Regras**: Identifica automaticamente padrões e regras customizadas
- **Operações Inteligentes**: Aplica exclusões, ajustes de valor e correções de dias
- **Múltiplos Modelos**: Suporte a llama2, llama3, codellama, mistral via Ollama

### ⚡ **Regras Estáticas Avançadas**
- **Exclusões Inteligentes**: Afastamentos, férias, desligados, estagiários, aprendizes, diretores
- **Cálculos por Sindicato**: Valores dinâmicos extraídos da planilha base
- **Regras Temporais**: Admissões em abril (integral) vs maio (proporcional)  
- **Regras por Data**: Desligados até dia 15 (exclusão) vs após dia 15 (proporcional)

### 📊 **Geração Especializada**
- **VR MENSAL Completo**: Planilha principal com todos os cálculos aplicados
- **Aba Validações**: Check automático de todas as regras (estáticas + IA)
- **Aba Regras Customizadas**: Documentação detalhada das regras aplicadas pela IA
- **Auditoria Total**: Rastreabilidade completa de todos os ajustes realizados

## 🚀 Como executar

### ⚙️ Pré-requisitos

Para usar as funcionalidades de IA, você precisa ter o **Ollama** instalado e configurado:

```bash
# Instalar Ollama (Linux/Mac)
curl -fsSL https://ollama.ai/install.sh | sh

# Baixar modelo (exemplo: llama2)
ollama pull llama2

# Iniciar servidor Ollama
ollama serve
```

### 🐳 Usando Docker Compose (Recomendado)

```bash
# Clonar/baixar os arquivos do projeto
cd i2a2_desafio4

# Construir e executar o serviço (com rebuild forçado para garantir mudanças)
docker compose build --no-cache
docker compose up --build

# Para executar em background
docker compose up -d --build
```

### 🔧 Configuração do Ollama

#### Ollama Local (padrão)
```bash
# O sistema usa automaticamente: http://localhost:11434
docker compose up --build
```

#### Ollama Remoto
```bash
# Definir servidor remoto via parâmetros da API
# Exemplo: ?ollama_host=http://servidor:11434&ollama_model=llama3
```

### 🚀 Execução Local (para desenvolvimento)

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar Ollama (opcional)
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_MODEL=llama2

# Executar o servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🌐 Acessar o serviço

Após executar, acesse:

- **Interface Web**: http://localhost:8000
- **Documentação da API**: http://localhost:8000/docs
- **Documentação alternativa**: http://localhost:8000/redoc
- **Status de saúde**: http://localhost:8000/health

## 📁 Planilhas de Entrada

O arquivo ZIP deve conter as seguintes planilhas Excel:

### 📊 **Planilhas Obrigatórias**
- `VR MENSAL 05.2025.xlsx` - **Template principal** (será preenchido automaticamente)
- `ATIVOS.xlsx` - Funcionários ativos elegíveis para VR
- `ADMISSÃO ABRIL.xlsx` - Novos funcionários (recebem VR integral em maio)
- `Base sindicato x valor.xlsx` - **Valores dinâmicos por região/sindicato**

### 🚫 **Planilhas de Exclusão**  
- `AFASTAMENTOS.xlsx` - Afastamentos/licenças (exclusão total + análise de observações)
- `FÉRIAS.xlsx` - Funcionários em férias (exclusão total)
- `DESLIGADOS.xlsx` - Desligamentos (regra por data: ≤15 = exclusão, >15 = proporcional)
- `ESTÁGIO.xlsx` - Estagiários (exclusão total - não recebem VR)
- `APRENDIZ.xlsx` - Aprendizes (exclusão total - não recebem VR)
- `EXTERIOR.xlsx` - Funcionários no exterior (exclusão/ajuste + análise IA)

### 📅 **Planilhas de Apoio**
- `Base dias uteis.xlsx` - Calendário de dias úteis (referência)

## 🎯 VR MENSAL Processado (Resultado Final)

A **planilha VR MENSAL processada** gerada contém:

### 🏠 **Aba Principal: "VR MENSAL 05.2025"**
- **Funcionários Válidos**: Apenas funcionários que devem receber VR
- **Valores Calculados**: VR total, custo empresa (80%), desconto funcionário (20%)
- **Dias Trabalhados**: Cálculo automático baseado em data de admissão
- **Sindicatos**: Valores regionais extraídos dinamicamente da planilha base

### ✅ **Aba "Validações"**
- **Check Automático**: Verificação visual (✅/⚠️/⏸️) de todas as regras aplicadas
- **Regras Estáticas**: Afastamentos, férias, desligados, estagiários, etc.
- **Regras LLM**: Regras customizadas descobertas pela IA
- **Estatísticas**: Contadores de registros afetados por cada regra

### 🤖 **Aba "Regras_Customizadas_Aplicadas"**
- **Regras Aplicadas**: Documentação detalhada de ações efetivas da IA
- **Regras Não Aplicadas**: Tentativas da IA com motivos de não aplicação
- **Transparência Total**: ID da regra, justificativa, confiança, planilha origem
- **Observações Originais**: Conteúdo textual que originou cada regra

### 📋 **Tipos de Ajustes da IA**
| Operação | Descrição | Exemplo de Trigger |
|----------|-----------|-------------------|
| **🚫 excluir** | Remove funcionário completamente | "demitido", "não recebe VR", "removido" |
| **💰 ajustar_valor** | Modifica valor do VR | "DIF DE VR... VALOR: R$ 450,00" |
| **📅 ajustar_dias** | Corrige dias trabalhados | "(+) 5 dias por licença não computada" |
| **⚪ nenhuma** | Apenas informativo | Totais, estatísticas, cabeçalhos |

## 🔧 API Endpoints

### POST `/processar-planilhas`

Processa um arquivo ZIP com planilhas Excel e retorna a **planilha VR MENSAL preenchida**.

**Request:**
- Content-Type: `multipart/form-data`
- Body: arquivo ZIP com planilhas Excel

**Parâmetros Opcionais:**
- `ollama_host` (query): URL do servidor Ollama remoto (ex: `http://servidor:11434`)
- `ollama_model` (query): Modelo LLM a usar (ex: `llama2`, `llama3`, `codellama`, `mistral`)

**Exemplo:**
```bash
# Upload com configuração customizada de IA
curl -X POST "http://localhost:8000/processar-planilhas?ollama_host=http://servidor:11434&ollama_model=llama3" \
  -F "file=@planilhas_rh.zip" \
  -o "VR_MENSAL_processado.xlsx"
```

**Response:**
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Body: Planilha VR MENSAL 05.2025 preenchida com 3 abas (Principal + Validações + Regras IA)

### GET `/health`

Verifica o status de saúde do serviço.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-XX",
  "service": "Processador de Dados de RH",
  "version": "2.0.0"
}
```

### GET `/info`

Informações detalhadas sobre o serviço e arquivos esperados.

### GET `/`

Interface web para upload de arquivos ZIP com funcionalidades:
- **Upload intuitivo** com drag-and-drop
- **Configuração de IA** via interface web
- **Download automático** do resultado processado

## 📝 Como usar

### 🎯 **Fluxo de Processamento**

1. **📂 Preparar dados**: Coloque todas as planilhas Excel em um arquivo ZIP
2. **🤖 Configurar IA** (opcional): Defina servidor Ollama e modelo via parâmetros
3. **⬆️ Upload**: Acesse http://localhost:8000 e faça upload do ZIP  
4. **⏳ Aguardar**: Processamento inteligente (pode levar alguns minutos)
   - Aplicação de regras estáticas
   - Análise de observações pela IA
   - Geração de validações e auditoria
5. **⬇️ Download**: Baixe a **planilha VR MENSAL preenchida** com 3 abas

### 🔍 **Verificação dos Resultados**

1. **Aba Principal**: Verifique os funcionários incluídos e valores calculados
2. **Aba Validações**: Confirme quais regras foram aplicadas (✅/⚠️/⏸️)
3. **Aba Regras IA**: Analise as decisões inteligentes tomadas pela IA

## ⚙️ Configuração

### 🌐 **Variáveis de Ambiente**

#### **Sistema**
- `PYTHONUNBUFFERED=1`: Output imediato dos logs
- `TZ=America/Sao_Paulo`: Timezone para logs

#### **Ollama/LLM**
- `OLLAMA_HOST`: URL do servidor Ollama (padrão: `http://localhost:11434`)
- `OLLAMA_MODEL`: Modelo LLM padrão (padrão: `llama2`)
- `OLLAMA_DEFAULT_MODEL`: Modelo fallback se OLLAMA_MODEL não definido

#### **Exemplo de Configuração**
```bash
export OLLAMA_HOST=http://servidor-ia:11434
export OLLAMA_MODEL=llama3
docker compose up --build
```

### 🔧 **Recursos do Docker**

- **Memória limite**: 2GB (processamento de planilhas)
- **Memória reservada**: 512MB 
- **Health check**: Verifica saúde a cada 30s
- **Rebuild forçado**: `--no-cache` para aplicar mudanças no código

## 🏗️ Arquitetura Modular

```
i2a2_desafio4/
├── main.py                        # 🚀 API FastAPI
├── processador_vr_mensal.py       # ⚡ Motor principal de processamento VR
├── llm_custom_rules.py            # 🤖 Módulo de IA/Regras customizadas  
├── validacoes_manager.py          # ✅ Gerador de validações automáticas
├── processador_rh.py              # 📊 Processador geral de dados RH
├── processamento_dados_rh.py      # 📋 Análise exploratória de dados
├── requirements.txt               # 📦 Dependências Python
├── Dockerfile                     # 🐳 Configuração Docker
├── docker-compose.yml             # 🎯 Orquestração Docker
├── .dockerignore                  # 🚫 Arquivos ignorados no build
├── README.md                      # 📚 Este arquivo
├── docs/                          # 📖 Documentação técnica detalhada
└── Desafio 4 - Dados/            # 💾 Dados de exemplo (desenvolvimento)
```

### 🧩 **Módulos Principais**

| Módulo | Responsabilidade | Funções Principais |
|--------|------------------|-------------------|
| **processador_vr_mensal.py** | 🎯 Processamento especializado VR | `executar_processamento_vr_completo()` |
| **llm_custom_rules.py** | 🤖 Inteligência artificial | `check_for_custom_rules()`, `extrair_observacoes_planilhas()` |
| **validacoes_manager.py** | ✅ Auditoria e validações | `gerar_aba_validacoes_completa()` |
| **main.py** | 🌐 API e interface web | `processar_planilhas()`, interface HTML |

## 🐛 Troubleshooting

### 🚫 **Problemas de Inicialização**

#### Serviço não inicia
```bash
# Verificar logs detalhados
docker compose logs -f

# Verificar status dos containers
docker compose ps

# Reiniciar forçado com rebuild
docker compose down
docker compose build --no-cache
docker compose up --build
```

#### Erro de dependências Python
```bash
# Rebuild completo das imagens
docker compose build --no-cache --pull
```

### 🤖 **Problemas de IA/Ollama**

#### Ollama não conecta
```bash
# Verificar se Ollama está rodando
curl http://localhost:11434/api/tags

# Testar modelo específico
ollama run llama2 "teste"

# Logs com foco em conexões LLM
docker compose logs | grep "🤖\|Ollama\|LLM"
```

#### Modelo não encontrado
```bash
# Baixar modelo necessário
ollama pull llama2
ollama pull llama3

# Verificar modelos disponíveis
ollama list
```

#### IA não aplica regras
- ✅ **Normal**: Se não houver observações relevantes, IA retorna "nenhuma ação"
- ⚠️ **Verificar**: Aba "Regras_Customizadas_Aplicadas" documenta todas as tentativas
- 🔍 **Debug**: Procurar logs `🚨 CRÍTICO DEBUG` para análise detalhada

### 💾 **Problemas de Dados**

#### Erro de upload
```bash
# Verificar arquivo ZIP
unzip -t arquivo.zip

# Verificar planilhas dentro do ZIP
unzip -l arquivo.zip | grep "\.xlsx"

# Tamanho máximo: verificar configuração do servidor
```

#### Planilhas não processadas
- ✅ Verificar se todas as **planilhas obrigatórias** estão no ZIP
- ⚠️ Nomes devem ser **exatos** (inclusive acentos)
- 🔍 Ver logs: `📁 Iniciando carregamento das planilhas...`

#### Valores incorretos nos sindicatos
```bash
# Verificar planilha "Base sindicato x valor.xlsx"
# O sistema extrai valores dinamicamente das colunas SP, RJ, RS, PR
# Se falhar, usa fallback R$ 37,50

# Ver logs: "🗺️ Processando valores por sindicato..."
docker compose logs | grep "sindicato\|SINDPD\|SINDPPD\|SITEPD"
```

### 🔧 **Problemas de Performance**

#### Erro de memória
```bash
# Aumentar limite no docker-compose.yml
mem_limit: 4G
mem_reservation: 1G

# Ou processar arquivos menores (< 100MB)
```

#### Processamento muito lento
- **IA habilitada**: Processamento pode levar 5-15 minutos (análise de observações)
- **IA desabilitada**: Processamento em 1-3 minutos (apenas regras estáticas)
- **Otimização**: Usar modelos LLM menores (llama2 vs llama3)

### 📊 **Validação de Resultados**

#### Como verificar se processamento foi correto
1. **Aba "Validações"**: Todas as regras devem ter ✅ ou ⏸️
2. **Aba "Regras IA"**: Ver regras aplicadas vs não aplicadas
3. **Logs de resumo**: `💰 Total Custo Empresa` deve ser > 0
4. **Contadores**: Verificar `Total de exclusões aplicadas`

## 📄 **Logs e Monitoramento**

### 📍 Localização dos Logs
- **Container**: `/app/logs/vr_mensal_YYYYMMDD.log`
- **Host** (se volume montado): `./logs/`
- **Console**: Logs em tempo real via `docker compose logs -f`

### 🔍 Logs Importantes
```bash
# Processamento principal
docker compose logs | grep "🚀 INICIANDO PROCESSAMENTO"

# Regras estáticas aplicadas
docker compose logs | grep "exclusões aplicadas\|funcionários restantes"

# Análise da IA
docker compose logs | grep "🤖 Aplicando regras customizadas\|regras aplicadas pela LLM"

# Resultado final
docker compose logs | grep "🎉 PROCESSAMENTO.*CONCLUÍDO"
```

## 🔄 **Atualizações e Manutenção**

### Atualizar o serviço
```bash
# Parar serviços
docker compose down

# Reconstruir com cache limpo (recomendado para aplicar mudanças)
docker compose build --no-cache

# Reiniciar com rebuild forçado
docker compose up --build -d
```

### Limpeza de sistema
```bash
# Remover containers e volumes órfãos
docker system prune -f

# Remover imagens não utilizadas
docker image prune -f
```

## 🆘 **Suporte Avançado**

### 🔬 Debug Detalhado
Para análise aprofundada, ativar logs DEBUG:
```python
# Temporariamente em processador_vr_mensal.py
self.logger.setLevel(logging.DEBUG)
```

### 📞 Cenários Críticos
1. **Processamento falha**: Verificar logs + validar ZIP + testar Ollama
2. **Resultados incorretos**: Comparar abas Validações + Regras IA  
3. **Performance lenta**: Verificar memória + modelo LLM + tamanho arquivos
4. **IA não funciona**: Testar Ollama standalone + verificar conectividade

### 📋 **Checklist de Diagnóstico**
- ✅ Ollama está rodando e acessível
- ✅ Modelo LLM baixado e funcional
- ✅ ZIP contém todas as planilhas obrigatórias
- ✅ Nomes das planilhas estão corretos (com acentos)
- ✅ Memória do container é suficiente (≥2GB)
- ✅ Logs não mostram erros críticos

---

## 🔧 **Especificações Técnicas**

### 📊 **Capacidades do Sistema**
- **Funcionários processados**: Até 10.000+ funcionários simultaneamente
- **Planilhas suportadas**: 11 planilhas de entrada + template VR
- **Tamanho máximo ZIP**: 500MB (configurável)
- **Modelos LLM suportados**: llama2, llama3, codellama, mistral, gemma
- **Tempo de processamento**: 1-3 min (sem IA) | 5-15 min (com IA)

### 🏗️ **Stack Tecnológica**
- **Backend**: Python 3.11+ com FastAPI
- **Processamento**: pandas, numpy, openpyxl
- **IA**: Ollama client para integração LLM
- **Container**: Docker + Docker Compose
- **Interface**: HTML5 + CSS3 + JavaScript vanilla

### 📈 **Versioning**
- **v1.0**: Sistema básico de processamento de planilhas
- **v2.0**: **ATUAL** - Integração completa com IA/LLM + Validações automáticas + Arquitetura modular
- **v2.1**: Planejado - Interface web aprimorada + Mais modelos LLM

### 🛡️ **Segurança e Privacidade**
- **Dados locais**: Todo processamento é local, dados não saem do ambiente
- **IA local**: Ollama roda localmente, sem envio de dados para nuvem
- **Logs seguros**: Logs não incluem dados sensíveis dos funcionários
- **Temporários**: Arquivos temporários são automaticamente limpos

### 🚀 **Roadmap**
- **[ ]** Interface web com preview das planilhas
- **[ ]** Suporte a mais formatos (CSV, ODS)
- **[ ]** API para processamento em lote
- **[ ]** Dashboard web para monitoramento
- **[ ]** Integração com mais modelos LLM (Claude, GPT-4)

---

## 📚 **Documentação Adicional**

Para documentação técnica detalhada, consulte:
- **📖 `/docs`**: Documentação técnica completa
- **🔍 `/docs/regras.md`**: Detalhes das regras de negócio
- **🤖 `/docs/configuracao_ollama_remoto.md`**: Setup avançado Ollama
- **📊 `/docs/aba_validacoes_completa.md`**: Documentação das validações
- **🧠 `/docs/logica_dinamica_observacoes_implementada.md`**: Como a IA analisa observações

---

**🏢 Sistema de Processamento VR MENSAL com IA v2.0**  
*Desenvolvido para automação inteligente de processamento de Vale Refeição*

**⚡ Processamento rápido • 🤖 IA integrada • 📊 Validações automáticas • 🔍 Auditoria completa**
