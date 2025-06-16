<template>
  <v-card>
    <v-card-title class="bg-success text-white">
      <v-icon class="mr-2">mdi-robot</v-icon>
      Chat com NF Agent
      <v-spacer></v-spacer>
      <v-btn
        icon
        variant="text"
        size="small"
        @click="showTaskHistory = !showTaskHistory"
        class="mr-2"
      >
        <v-icon>mdi-history</v-icon>
      </v-btn>
      <v-btn
        icon
        variant="text"
        size="small"
        @click="resetAgents"
        :loading="resettingAgents"
        class="mr-2"
        title="Reiniciar time de agentes"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
      <v-chip
        v-if="systemStore"
        :color="systemStore.chatEnabled ? 'success' : 'error'"
        :prepend-icon="systemStore.chatEnabled ? 'mdi-check' : 'mdi-close'"
        variant="outlined"
        size="small"
      >
        {{ systemStore.chatEnabled ? 'Habilitado' : 'Desabilitado' }}
      </v-chip>
      <v-chip
        v-else
        color="grey"
        prepend-icon="mdi-help-circle-outline"
        variant="outlined"
        size="small"
      >
        Carregando...
      </v-chip>
    </v-card-title>
    <v-card-text class="pa-0" style="height: calc(100% - 64px);">
      <div class="chat-container">
        <!-- Agent Implementation Selector -->
        <AgentImplementationSelector class="mb-4" />

        <!-- Disabled State -->
        <div v-if="!enabled" class="disabled-overlay">
          <v-card class="text-center pa-6">
            <v-icon size="64" color="grey" class="mb-4">mdi-robot-off</v-icon>
            <h3 class="text-h6 mb-2">Chat Desabilitado</h3>
            <p class="text-body-2 text-medium-emphasis">
              Para habilitar o chat, primeiro faça upload de arquivos de notas fiscais
              e certifique-se de que o Agent Service esteja online.
            </p>
          </v-card>
        </div>

        <!-- Chat Interface -->
        <div v-else class="chat-interface">
          <!-- Messages Area -->
          <div ref="messagesContainer" class="messages-container">
            <div v-if="messages.length === 0" class="empty-state">
              <v-icon size="48" color="primary" class="mb-2">mdi-robot</v-icon>
              <h4 class="text-h6 mb-2">NF Agent Pronto!</h4>
              <p class="text-body-2 text-medium-emphasis">
                Digite uma pergunta sobre as notas fiscais ou solicite uma análise.
              </p>
            </div>

            <!-- Message List -->
            <div v-for="(message, index) in messages" :key="index" class="message-item">
              <v-card
                :class="[
                  'message-card',
                  message.type === 'user' ? 'user-message' : 'agent-message'
                ]"
                :color="message.type === 'user' ? 'primary' : 'grey-lighten-4'"
                variant="flat"
              >
                <v-card-text class="pa-3">
                  <div class="message-header">
                    <v-icon
                      :color="message.type === 'user' ? 'white' : 'primary'"
                      size="20"
                      class="mr-2"
                    >
                      {{ message.type === 'user' ? 'mdi-account' : 'mdi-robot' }}
                    </v-icon>
                    <span
                      :class="[
                        'text-caption',
                        message.type === 'user' ? 'text-white' : 'text-medium-emphasis'
                      ]"
                    >
                      {{ message.type === 'user' ? 'Você' : 'Agent Team (' + (message.source || 'unknown') + ')' }}
                    </span>
                    <v-spacer></v-spacer>
                    <span
                      :class="[
                        'text-caption',
                        message.type === 'user' ? 'text-white' : 'text-medium-emphasis'
                      ]"
                    >
                      {{ formatTime(message.timestamp) }}
                    </span>
                  </div>
                  
                  <div
                    :class="[
                      'message-content',
                      message.type === 'user' ? 'text-white' : 'text-black'
                    ]"
                    v-html="renderMarkdown(message.content)"
                  ></div>
                </v-card-text>
              </v-card>
            </div>

            <!-- Typing Indicator -->
            <div v-if="isProcessing" class="message-item">
              <v-card class="message-card agent-message" color="grey-lighten-4" variant="flat">
                <v-card-text class="pa-3">
                  <div class="typing-indicator">
                    <v-icon color="primary" size="20" class="mr-2">mdi-robot</v-icon>
                    <span class="text-caption text-medium-emphasis">
                      Agent Team está analisando... 
                      <v-icon size="16" class="ml-1 rotating">mdi-cog</v-icon>
                    </span>
                  </div>
                  <div class="text-caption text-medium-emphasis mt-1">
                    <em>Aguardando resposta de cada agente (tempo real)</em>
                  </div>
                </v-card-text>
              </v-card>
            </div>
          </div>

          <!-- Input Area -->
          <div class="input-area">
            <v-row no-gutters>
              <v-col>
                <v-textarea
                  v-model="newMessage"
                  placeholder="Digite sua pergunta sobre as notas fiscais..."
                  rows="2"
                  variant="outlined"
                  hide-details
                  @keydown.ctrl.enter="sendMessage"
                  :disabled="isProcessing"
                />
              </v-col>
              <v-col cols="auto" class="ml-2">
                <v-btn
                  color="primary"
                  size="large"
                  :loading="isProcessing"
                  :disabled="!newMessage.trim() || isProcessing"
                  @click="sendMessage"
                  style="height: 56px;"
                >
                  <v-icon>mdi-send</v-icon>
                </v-btn>
              </v-col>
            </v-row>
          </div>
        </div>

        <!-- Task History -->
        <v-card v-if="showTaskHistory" class="mt-4">
          <v-card-title class="d-flex justify-space-between align-center">
            <span>Histórico de Tarefas</span>
            <v-btn icon @click="showTaskHistory = false">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </v-card-title>
          
          <!-- Resumo de Estatísticas -->
          <v-card-subtitle v-if="taskHistory.length > 0" class="pb-2">
            <div class="d-flex justify-space-between align-center">
              <span>{{ taskHistory.length }} tarefas</span>
              <div class="d-flex align-center">
                <v-icon size="16" class="mr-1 text-info">mdi-counter</v-icon>
                <span class="text-info">{{ getTotalTokens() }} tokens total</span>
              </div>
            </div>
          </v-card-subtitle>
          
          <v-card-text>
            <v-list>
              <v-list-item v-for="task in taskHistory" :key="task.created_at" class="mb-2">
                <v-card class="w-100" variant="outlined">
                  <v-card-text>
                    <div class="d-flex justify-space-between align-center mb-2">
                      <strong>{{ task.task }}</strong>
                      <div class="d-flex align-center gap-2">
                        <!-- Chip de Tokens -->
                        <v-chip
                          v-if="task.total_tokens !== null && task.total_tokens !== undefined"
                          color="info"
                          size="small"
                          prepend-icon="mdi-counter"
                          variant="outlined"
                        >
                          {{ task.total_tokens }} tokens
                        </v-chip>
                        <!-- Chip de Status -->
                        <v-chip
                          :color="task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : 'warning'"
                          size="small"
                        >
                          {{ task.status }}
                        </v-chip>
                      </div>
                    </div>
                    
                    <!-- Logs do Autogen -->
                    <div class="mt-2">
                      <div class="text-caption mb-1">Logs do Autogen:</div>
                      <v-card variant="outlined" class="bg-grey-lighten-4">
                        <v-card-text class="py-2">
                          <div v-if="task.logs && task.logs.length > 0" class="logs-container">
                            <div v-for="(log, index) in task.logs" :key="index" class="text-caption font-family-monospace log-entry">
                              {{ log }}
                            </div>
                          </div>
                          <div v-else class="text-caption text-grey">Nenhum log registrado para esta tarefa.</div>
                        </v-card-text>
                      </v-card>
                    </div>

                    <!-- Resultado Final -->
                    <div v-if="task.result" class="mt-2">
                      <div class="text-caption mb-1">Resposta Final:</div>
                      <v-card variant="outlined" class="bg-grey-lighten-4">
                        <v-card-text class="py-2">
                          {{ task.result }}
                        </v-card-text>
                      </v-card>
                    </div>

                    <!-- Erro -->
                    <div v-if="task.error" class="mt-2">
                      <div class="text-caption mb-1 text-error">Erro:</div>
                      <v-card variant="outlined" class="bg-grey-lighten-4">
                        <v-card-text class="py-2 text-error">
                          {{ task.error }}
                        </v-card-text>
                      </v-card>
                    </div>

                    <!-- Estatísticas da Task -->
                    <div class="mt-2">
                      <div class="d-flex justify-space-between align-center">
                        <div class="text-caption">
                          {{ new Date(task.created_at).toLocaleString() }}
                        </div>
                        <div v-if="task.total_tokens !== null && task.total_tokens !== undefined" class="text-caption text-info">
                          <v-icon size="12" class="mr-1">mdi-counter</v-icon>
                          Total: {{ task.total_tokens }} tokens
                        </div>
                      </div>
                      <div v-if="task.completed_at" class="text-caption text-medium-emphasis">
                        Duração: {{ calculateDuration(task.created_at, task.completed_at) }}
                      </div>
                    </div>
                  </v-card-text>
                </v-card>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, nextTick, watch, defineProps, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useSystemStore } from '../stores/system'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import AgentImplementationSelector from './AgentImplementationSelector.vue'

// Configurar marked para usar opções seguras
marked.setOptions({
  breaks: true, // Quebras de linha são respeitadas
  gfm: true,    // Suporte a GitHub Flavored Markdown
  headerIds: false, // Desabilitar IDs automáticos nos headers
  mangle: false,    // Desabilitar mangling de emails
  sanitize: false   // Desabilitar sanitização (usaremos DOMPurify)
})

// Props
const props = defineProps({
  enabled: {
    type: Boolean,
    default: false
  }
})

// Reactive data
const messages = ref([])
const newMessage = ref('')
const isProcessing = ref(false)
const messagesContainer = ref(null)
const showTaskHistory = ref(false)
const loadingHistory = ref(false)
const taskHistory = ref([])
const systemStore = useSystemStore()
const resettingAgents = ref(false)

// Utility function to build API URLs correctly
function buildApiUrl(path) {
  // Ensure the path starts with /api/
  if (!path.startsWith('/api/')) {
    if (path.startsWith('api/')) {
      path = '/' + path
    } else {
      path = '/api/' + path.replace(/^\//, '')
    }
  }
  return path
}

// Methods
async function sendMessage() {
  if (!newMessage.value.trim() || isProcessing.value) return
  
  const message = newMessage.value.trim()
  newMessage.value = ''
  
  // Add user message
  addMessage('user', message)
  
  try {
    isProcessing.value = true
    
    // Create task
    const taskResponse = await axios.post('/api/agent/tasks/', {
      task: message,
      description: 'Chat message from UI'
    })
    
    // Start streaming
    await streamTask(taskResponse.data.task_id)
    
  } catch (error) {
    console.error('Error sending message:', error)
    addMessage('system', `Erro: ${error.response?.data?.detail || error.message}`)
  } finally {
    isProcessing.value = false
  }
}

async function streamTask(taskId) {
  try {
    console.log('[Chat] 🚀 Starting stream for task:', taskId)
    const response = await fetch('/api/agent/tasks/' + taskId + '/stream', {
      method: 'POST'
    })
    
    console.log('[Chat] 📡 Stream response status:', response.status)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let hasContent = false
    
    // Variables to accumulate agent messages
    let currentAgentMessage = null
    let lastMessageTime = null
    const MESSAGE_TIMEOUT = 1500 // 1.5s para aguardar fim da mensagem de cada agente individual
    
    // Function to finalize accumulated message
    function finalizeCurrentMessage() {
      if (currentAgentMessage && currentAgentMessage.content.trim()) {
        console.log('[Chat] 💬 FINALIZING AGENT MESSAGE:', currentAgentMessage.content.length, 'chars from', currentAgentMessage.sources.join(', '))
        // Usar o timestamp da primeira mensagem do grupo para preservar ordem cronológica
        const messageTimestamp = currentAgentMessage.firstMessageTime || Date.now()
        addMessageWithTimestamp('agent', currentAgentMessage.content.trim(), currentAgentMessage.sources.join(' → '), messageTimestamp)
        hasContent = true
        currentAgentMessage = null
      }
    }
    
    // Timer to finalize messages
    let messageTimer = null
    let chunkCount = 0
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        console.log('[Chat] 🏁 Stream ended, finalizing any pending message')
        // Finalize any pending message when stream ends
        finalizeCurrentMessage()
        break
      }
      
      chunkCount++
      const chunk = decoder.decode(value)
      console.log('[Chat] 📦 Received chunk', chunkCount, ':', chunk.substring(0, 200) + (chunk.length > 200 ? '...' : ''))
      
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const rawData = line.slice(6).trim()
          if (!rawData || rawData === '') {
            console.log('[Chat] ⚪ Empty data line, skipping')
            continue // Skip empty lines
          }
          
          console.log('[Chat] 📥 Processing data line:', rawData.substring(0, 100) + (rawData.length > 100 ? '...' : ''))
          
          // Try to parse as JSON first
          try {
            const data = JSON.parse(rawData)
            console.log('[Chat] 🔄 JSON STREAM DATA:', data)
            
            if (data.type === 'input_request') {
              // Handle input requests (JSON format) - finalize any pending message first
              console.log('[Chat] 🤖 INPUT REQUEST:', data.prompt)
              finalizeCurrentMessage()
              addMessage('system', `🤖 ${data.prompt}`, 'Agent')
              // Habilitar input do usuário
              isProcessing.value = false
              // Aguardar input do usuário
              const userInput = await new Promise(resolve => {
                const inputHandler = async () => {
                  if (newMessage.value.trim()) {
                    const input = newMessage.value.trim()
                    newMessage.value = ''
                    resolve(input)
                  }
                }
                // Adicionar listener para o botão de enviar
                const sendButton = document.querySelector('.input-area .v-btn')
                if (sendButton) {
                  sendButton.addEventListener('click', inputHandler)
                }
                // Adicionar listener para Ctrl+Enter
                document.addEventListener('keydown', (e) => {
                  if (e.ctrlKey && e.key === 'Enter') {
                    inputHandler()
                  }
                })
              })
              
              // Enviar input do usuário
              try {
                await axios.post('/api/agent/tasks/' + taskId + '/input', {
                  input: userInput
                })
                // Mostrar input do usuário no chat
                addMessage('user', userInput)
                isProcessing.value = true
              } catch (error) {
                console.error('Error sending user input:', error)
                addMessage('system', `❌ Erro ao enviar input: ${error.message}`)
              }
            } else if (data.type === 'completion') {
              console.log('[Chat] ✅ COMPLETION:', data.message)
              finalizeCurrentMessage() // Finalize before completion message
              addMessage('system', `✅ ${data.message}`)
              hasContent = true
            } else if (data.type === 'error') {
              console.log('[Chat] ❌ ERROR:', data.message)
              finalizeCurrentMessage() // Finalize before error message
              addMessage('system', `❌ ${data.message}`)
              hasContent = true
            } else if (data.type === 'token_update') {
              // Handle token updates - just log for now, could show in UI
              console.log('[Chat] 🪙 TOKEN UPDATE:', data.total_tokens)
              // Don't finalize message for token updates
              hasContent = true
            } else {
              // Handle other JSON messages - these should be accumulated
              let messageContent = data.content || data.message || JSON.stringify(data)
              let messageSource = data.source || 'unknown'
              
              console.log('[Chat] 💭 OTHER JSON MESSAGE:', messageContent, 'from:', messageSource)
              
              if (messageContent && messageContent.trim() && messageContent !== '{}') {
                console.log('[Chat] 💬 JSON AGENT MESSAGE PART:', messageContent, 'from:', messageSource)
                
                // Accumulate this message
                if (!currentAgentMessage) {
                  currentAgentMessage = {
                    content: '',
                    sources: [],
                    firstMessageTime: Date.now()
                  }
                }
                
                // Se mudou de agente, finalizar mensagem anterior primeiro
                if (currentAgentMessage.sources.length > 0 && !currentAgentMessage.sources.includes(messageSource)) {
                  console.log('[Chat] 🔄 SOURCE CHANGED, finalizing previous message')
                  finalizeCurrentMessage()
                  // Começar nova mensagem para novo agente
                  currentAgentMessage = {
                    content: '',
                    sources: [],
                    firstMessageTime: Date.now()
                  }
                }
                
                currentAgentMessage.content += messageContent + ' '
                if (!currentAgentMessage.sources.includes(messageSource)) {
                  currentAgentMessage.sources.push(messageSource)
                }
                
                lastMessageTime = Date.now()
                
                // Reset timer
                if (messageTimer) clearTimeout(messageTimer)
                messageTimer = setTimeout(finalizeCurrentMessage, MESSAGE_TIMEOUT)
              }
            }
          } catch (e) {
            // If JSON parsing fails, treat as simple text message
            console.log('[Chat] 📝 TEXT MESSAGE (not JSON):', rawData)
            
            // Extract source and content from simple text format like "[Agent] message"
            const match = rawData.match(/^\[([^\]]+)\]\s*(.*)$/)
            if (match) {
              const source = match[1]
              const content = match[2].trim()
              console.log('[Chat] 📝 PARSED TEXT MESSAGE:', content, 'from source:', source)
              if (content) {
                console.log('[Chat] 💬 TEXT AGENT MESSAGE PART:', content, 'from:', source)
                
                // Accumulate this message
                if (!currentAgentMessage) {
                  currentAgentMessage = {
                    content: '',
                    sources: [],
                    firstMessageTime: Date.now()
                  }
                }
                
                // Se mudou de agente, finalizar mensagem anterior primeiro
                if (currentAgentMessage.sources.length > 0 && !currentAgentMessage.sources.includes(source)) {
                  console.log('[Chat] 🔄 SOURCE CHANGED, finalizing previous message')
                  finalizeCurrentMessage()
                  // Começar nova mensagem para novo agente
                  currentAgentMessage = {
                    content: '',
                    sources: [],
                    firstMessageTime: Date.now()
                  }
                }
                
                currentAgentMessage.content += content + ' '
                if (!currentAgentMessage.sources.includes(source)) {
                  currentAgentMessage.sources.push(source)
                }
                
                lastMessageTime = Date.now()
                
                // Reset timer
                if (messageTimer) clearTimeout(messageTimer)
                messageTimer = setTimeout(finalizeCurrentMessage, MESSAGE_TIMEOUT)
              }
            } else {
              // Just treat the whole thing as a system message - finalize current first
              console.log('[Chat] 📝 UNPARSED TEXT MESSAGE:', rawData)
              if (rawData.length > 0) {
                finalizeCurrentMessage()
                addMessage('agent', rawData, 'System')
                hasContent = true
              }
            }
          }
        } else if (line.trim()) {
          console.log('[Chat] ⚠️ Non-data line, treating as continuation:', line)
          // Tratar linhas sem "data:" como continuação do conteúdo anterior
          if (line.trim().length > 0) {
            // Se temos uma mensagem sendo acumulada, adicionar esta linha a ela
            if (!currentAgentMessage) {
              currentAgentMessage = {
                content: '',
                sources: ['System'],
                firstMessageTime: Date.now()
              }
            }
            
            // Adicionar esta linha como continuação
            currentAgentMessage.content += line.trim() + '\n'
            lastMessageTime = Date.now()
            
            // Reset timer para aguardar mais conteúdo
            if (messageTimer) clearTimeout(messageTimer)
            messageTimer = setTimeout(finalizeCurrentMessage, MESSAGE_TIMEOUT)
          }
        }
      }
    }
    
    // Clean up timer
    if (messageTimer) clearTimeout(messageTimer)
    
    console.log('[Chat] 📊 Stream finished. Has content:', hasContent, 'Chunk count:', chunkCount)
    
    // If no content was received via streaming, fetch the final result
    if (!hasContent) {
      console.log('[Chat] ⚠️ NO CONTENT received via streaming, fetching final result as fallback') // Debug log
      await fetchTaskResult(taskId)
    } else {
      console.log('[Chat] ✅ Content was received via streaming, task completed') // Debug log
    }
    
  } catch (error) {
    console.error('Streaming error:', error)
    addMessage('system', `Erro no streaming: ${error.message}`)
    
    // Try to fetch the final result as fallback
    await fetchTaskResult(taskId)
  }
}

async function fetchTaskResult(taskId) {
  try {
    await new Promise(resolve => setTimeout(resolve, 2000))
    console.log('[Chat] fetchTaskResult - taskId:', taskId);
    const relativeApiUrl = buildApiUrl('agent/tasks/' + taskId + '/');
    const absoluteApiUrl = window.location.origin + relativeApiUrl;
    console.log('[Chat] fetchTaskResult - constructed absoluteApiUrl for fetch:', absoluteApiUrl);

    const response = await fetch(absoluteApiUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      }
    });

    console.log('[Chat] fetchTaskResult - fetch response status:', response.status);
    console.log('[Chat] fetchTaskResult - fetch response redirected:', response.redirected);
    console.log('[Chat] fetchTaskResult - fetch response url:', response.url);

    if (!response.ok) {
      // Log the response body if not ok, to see any error messages from server
      let errorText = 'Failed to fetch task result';
      try {
        errorText = await response.text();
      } catch (e) { /* ignore if cant read body */ }
      console.error('[Chat] fetchTaskResult - Fetch error response body:', errorText);
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}. Body: ${errorText}`);
    }

    const task = await response.json();
    console.log('[Chat] Task data from backend (using fetch):', JSON.stringify(task, null, 2));

    if (task.status === 'completed' ) {
      console.log('[Chat] Task completed with result. Adding to messages:', task.result)
      let resultMessage = task.result
      if (task.total_tokens) {
        resultMessage += '\n\nTotal de tokens utilizados: ' + task.total_tokens
      }
      addMessage('agent', resultMessage, 'Agent')
      // Atualizar o histórico após receber o resultado
      await fetchTaskHistory()
    } else if (task.status === 'failed' && task.error) {
      console.log('[Chat] Task failed. Adding error to messages:', task.error)
      addMessage('system', `❌ Erro: ${task.error}`)
      await fetchTaskHistory()
    } else if (task.status === 'processing') {
      console.log('[Chat] Task still processing. Will retry.')
      addMessage('system', '⏳ Tarefa ainda processando...')
      setTimeout(() => fetchTaskResult(taskId), 3000)
    } else {
      console.log('[Chat] Task in unexpected state or no result:', task.status)
    }
  } catch (error) {
    console.error('[Chat] Error fetching task result (using fetch):', error);
    addMessage('system', `Erro ao buscar resultado: ${error.message}`)
  }
}

function addMessage(type, content, source = null) {
  messages.value.push({
    type,
    content,
    source,
    timestamp: Date.now()
  })
  
  nextTick(() => {
    scrollToBottom()
  })
}

function addMessageWithTimestamp(type, content, source = null, timestamp = null) {
  messages.value.push({
    type,
    content,
    source,
    timestamp: timestamp || Date.now()
  })
  
  // Reordenar mensagens por timestamp para garantir ordem cronológica
  messages.value.sort((a, b) => a.timestamp - b.timestamp)
  
  nextTick(() => {
    scrollToBottom()
  })
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDateTime(timestamp) {
  return new Date(timestamp).toLocaleDateTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getTaskStatusColor(status) {
  switch (status) {
    case 'completed': return 'success'
    case 'processing': return 'warning'
    case 'created': return 'info'
    case 'failed':
    case 'error': return 'error'
    case 'waiting_for_input': return 'orange'
    default: return 'grey'
  }
}

function getTaskStatusIcon(status) {
  switch (status) {
    case 'completed': return 'mdi-check-circle'
    case 'processing': return 'mdi-loading mdi-spin'
    case 'created': return 'mdi-clock-outline'
    case 'failed':
    case 'error': return 'mdi-alert-circle'
    case 'waiting_for_input': return 'mdi-account-question'
    default: return 'mdi-help-circle'
  }
}

async function fetchTaskHistory() {
  try {
    console.log('[Chat] Attempting fetch to /api/agent/tasks/')
    const response = await fetch(buildApiUrl('agent/tasks/'))
    console.log('[Chat] Fetch response status:', response.status);
    if (!response.ok) {
      let errorBody = '';
      try {
        errorBody = await response.text();
      } catch (e) {}
      throw new Error(`HTTP error! status: ${response.status}, statusText: ${response.statusText}. Body: ${errorBody}`);
    }
    const text = await response.text();
    if (!text) {
      console.warn('[Chat] Resposta vazia do backend para histórico de tasks.');
      taskHistory.value = [];
      return;
    }
    const data = JSON.parse(text);
    console.log('[Chat] Fetch response data:', JSON.stringify(data, null, 2));
    taskHistory.value = (data || []).map(task => ({
      ...task,
      logs: Array.isArray(task.logs) ? task.logs : []
    }));
  } catch (error) {
    console.error('[Chat] Error fetching task history with fetch:', error);
    if (error.cause) {
      console.error('[Chat] Fetch error cause:', error.cause);
    }
  }
}

function renderMarkdown(text) {
  // Primeiro sanitize o texto para remover qualquer HTML malicioso
  const sanitized = DOMPurify.sanitize(text)
  // Depois converte o markdown para HTML
  return marked(sanitized)
}

function calculateDuration(startTime, endTime) {
  const start = new Date(startTime)
  const end = new Date(endTime)
  const diffMs = end - start
  
  if (diffMs < 1000) {
    return `${diffMs}ms`
  } else if (diffMs < 60000) {
    return `${Math.round(diffMs / 1000)}s`
  } else {
    const minutes = Math.floor(diffMs / 60000)
    const seconds = Math.round((diffMs % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }
}

function getTotalTokens() {
  return taskHistory.value.reduce((total, task) => total + (task.total_tokens || 0), 0)
}

// Watch for enabled changes to reset chat
watch(() => props.enabled, (newVal) => {
  if (newVal) {
    messages.value = []
    isProcessing.value = false
  }
})

// Listen for implementation changes
const handleImplementationChange = (event) => {
  // Clear messages when implementation changes
  messages.value = []
  // Reset any ongoing tasks
  isProcessing.value = false
  newMessage.value = ''
}

onMounted(() => {
  // ... existing onMounted code ...
  window.addEventListener('agent-implementation-changed', handleImplementationChange)
})

onUnmounted(() => {
  // ... existing onUnmounted code ...
  window.removeEventListener('agent-implementation-changed', handleImplementationChange)
})

// Chame fetchTaskHistory sempre que abrir o histórico
watch(showTaskHistory, (val) => {
  if (val) fetchTaskHistory()
})

async function resetAgents() {
  resettingAgents.value = true
  try {
    const response = await axios.post('/api/agent/restart-agents/')
    if (response.data.status === 'ok') {
      addMessage('system', '✅ Time de agentes reiniciado com sucesso.')
    } else {
      addMessage('system', `❌ Falha ao reiniciar agentes: ${response.data.message}`)
    }
  } catch (error) {
    addMessage('system', `❌ Erro ao reiniciar agentes: ${error.message}`)
  } finally {
    resettingAgents.value = false
  }
}
</script>

<style scoped>
.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.disabled-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.chat-interface {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  max-height: calc(100vh - 300px);
}

.empty-state {
  text-align: center;
  padding: 32px 16px;
}

.message-item {
  margin-bottom: 12px;
}

.message-card {
  max-width: 80%;
}

.user-message {
  margin-left: auto;
}

.agent-message {
  margin-right: auto;
}

.message-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.message-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.typing-indicator {
  display: flex;
  align-items: center;
}

.input-area {
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  background-color: #fafafa;
  position: relative;
  z-index: 1;
}

.input-area .v-btn {
  transition: all 0.3s ease;
}

.input-area .v-btn:not(:disabled) {
  transform: scale(1);
}

.input-area .v-btn:disabled {
  transform: scale(0.95);
  opacity: 0.7;
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.white-space-pre-wrap {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.font-family-monospace {
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Estilos para Markdown */
.message-content :deep(h1) {
  font-size: 1.5em;
  margin: 0.5em 0;
}

.message-content :deep(h2) {
  font-size: 1.3em;
  margin: 0.5em 0;
}

.message-content :deep(h3) {
  font-size: 1.1em;
  margin: 0.5em 0;
}

.message-content :deep(p) {
  margin: 0.5em 0;
}

.message-content :deep(ul), 
.message-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.message-content :deep(li) {
  margin: 0.25em 0;
}

.message-content :deep(code) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: monospace;
}

.message-content :deep(pre) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 1em;
  border-radius: 4px;
  overflow-x: auto;
  margin: 0.5em 0;
}

.message-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.message-content :deep(blockquote) {
  border-left: 4px solid rgba(0, 0, 0, 0.1);
  margin: 0.5em 0;
  padding-left: 1em;
  color: rgba(0, 0, 0, 0.6);
}

.message-content :deep(table) {
  border-collapse: collapse;
  margin: 0.5em 0;
  width: 100%;
}

.message-content :deep(th),
.message-content :deep(td) {
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 0.5em;
  text-align: left;
}

.message-content :deep(th) {
  background-color: rgba(0, 0, 0, 0.05);
}

.message-content :deep(a) {
  color: #1976d2;
  text-decoration: none;
}

.message-content :deep(a:hover) {
  text-decoration: underline;
}

.message-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 0.5em 0;
}

/* Ajustes para mensagens do usuário */
.user-message .message-content :deep(code) {
  background-color: rgba(255, 255, 255, 0.2);
}

.user-message .message-content :deep(pre) {
  background-color: rgba(255, 255, 255, 0.2);
}

.user-message .message-content :deep(blockquote) {
  border-left-color: rgba(255, 255, 255, 0.3);
  color: rgba(255, 255, 255, 0.8);
}

.user-message .message-content :deep(a) {
  color: #ffffff;
}

.user-message .message-content :deep(table) {
  border-color: rgba(255, 255, 255, 0.2);
}

.user-message .message-content :deep(th),
.user-message .message-content :deep(td) {
  border-color: rgba(255, 255, 255, 0.2);
}

.user-message .message-content :deep(th) {
  background-color: rgba(255, 255, 255, 0.1);
}

/* Animação para o indicador de processamento */
.rotating {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Container de logs com rolagem */
.logs-container {
  max-height: 200px;
  overflow-y: auto;
  padding: 4px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.log-entry {
  padding: 2px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  line-height: 1.4;
}

.log-entry:last-child {
  border-bottom: none;
}

/* Estilo personalizado da scrollbar para logs */
.logs-container::-webkit-scrollbar {
  width: 8px;
}

.logs-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.logs-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>