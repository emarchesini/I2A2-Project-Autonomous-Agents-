<template>
  <div>
    <!-- Status Cards -->
    <v-row>
      <v-col cols="6">
        <v-card variant="outlined" class="text-center">
          <v-card-text>
            <v-icon
              :color="systemStore.databasePopulated ? 'success' : 'grey'"
              size="32"
              class="mb-2"
            >
              mdi-database
            </v-icon>
            <div class="text-h6">{{ totalRecords.toLocaleString() }}</div>
            <div class="text-caption">Registros Totais</div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <v-col cols="6">
        <v-card variant="outlined" class="text-center">
          <v-card-text>
            <v-icon
              :color="systemStore.chatEnabled ? 'success' : 'grey'"
              size="32"
              class="mb-2"
            >
              mdi-robot
            </v-icon>
            <div class="text-h6">{{ systemStore.chatEnabled ? 'ON' : 'OFF' }}</div>
            <div class="text-caption">Chat Agent</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Detailed Status -->
    <v-list class="mt-4">
      <v-list-item>
        <template v-slot:prepend>
          <v-icon
            :color="systemStore.loadServiceStatus ? 'success' : 'error'"
          >
            {{ systemStore.loadServiceStatus ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
        </template>
        
        <v-list-item-title>Load Service</v-list-item-title>
        <v-list-item-subtitle>
          {{ systemStore.loadServiceStatus ? 'Online' : 'Offline' }}
        </v-list-item-subtitle>
      </v-list-item>

      <v-list-item>
        <template v-slot:prepend>
          <v-icon
            :color="systemStore.agentServiceStatus ? 'success' : 'error'"
          >
            {{ systemStore.agentServiceStatus ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
        </template>
        
        <v-list-item-title>Agent Service</v-list-item-title>
        <v-list-item-subtitle>
          {{ systemStore.agentServiceStatus ? 'Online' : 'Offline' }}
        </v-list-item-subtitle>
      </v-list-item>

      <v-list-item>
        <template v-slot:prepend>
          <v-icon
            :color="systemStore.databasePopulated ? 'success' : 'warning'"
          >
            {{ systemStore.databasePopulated ? 'mdi-database-check' : 'mdi-database-alert' }}
          </v-icon>
        </template>
        
        <v-list-item-title>Banco de Dados</v-list-item-title>
        <v-list-item-subtitle>
          {{ systemStore.databasePopulated ? 'Populado' : 'Vazio' }}
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <!-- Database Details -->
    <v-expansion-panels v-if="databaseDetails" class="mt-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-chart-bar</v-icon>
          Detalhes do Banco
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row>
            <v-col cols="6">
              <v-card variant="outlined">
                <v-card-text class="text-center">
                  <div class="text-h6">{{ databaseDetails.notas_fiscais || 0 }}</div>
                  <div class="text-caption">Notas Fiscais</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="6">
              <v-card variant="outlined">
                <v-card-text class="text-center">
                  <div class="text-h6">{{ databaseDetails.itens_nota_fiscal || 0 }}</div>
                  <div class="text-caption">Itens</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
          
          <v-list density="compact" class="mt-2">
            <v-list-item v-if="databaseDetails.last_upload">
              <v-list-item-title>Último Upload</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatDate(databaseDetails.last_upload) }}
              </v-list-item-subtitle>
            </v-list-item>
            
            <v-list-item v-if="databaseDetails.total_value">
              <v-list-item-title>Valor Total</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatCurrency(databaseDetails.total_value) }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Refresh Button -->
    <v-btn
      variant="outlined"
      color="primary"
      :loading="refreshing"
      @click="refreshStatus"
      class="mt-4"
      block
    >
      <v-icon class="mr-2">mdi-refresh</v-icon>
      Atualizar Status
    </v-btn>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSystemStore } from '../stores/system'
import axios from 'axios'

const systemStore = useSystemStore()

// Reactive data
const refreshing = ref(false)
const databaseDetails = ref(null)

// Computed
const totalRecords = computed(() => {
  if (!databaseDetails.value) return 0
  return (databaseDetails.value.notas_fiscais || 0) + (databaseDetails.value.itens_nota_fiscal || 0)
})

// Methods
async function refreshStatus() {
  refreshing.value = true
  
  try {
    await systemStore.checkServicesStatus()
    await loadDatabaseDetails()
  } catch (error) {
    console.error('Error refreshing status:', error)
  } finally {
    refreshing.value = false
  }
}

async function loadDatabaseDetails() {
  try {
    const response = await axios.get('/api/load/status')
    databaseDetails.value = response.data
  } catch (error) {
    console.warn('Could not load database details:', error)
    databaseDetails.value = null
  }
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString('pt-BR')
}

function formatCurrency(value) {
  if (!value) return 'R$ 0,00'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value)
}

// Lifecycle
onMounted(() => {
  loadDatabaseDetails()
})
</script>

<style scoped>
.v-card {
  transition: all 0.3s ease;
}

.v-card:hover {
  transform: translateY(-2px);
}
</style> 