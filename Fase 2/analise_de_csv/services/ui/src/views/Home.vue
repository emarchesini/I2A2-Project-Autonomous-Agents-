<template>
  <v-container fluid class="pa-6">
    <v-row>
      <!-- Upload Section -->
      <v-col cols="12" lg="6">
        <v-card elevation="3" class="mb-4">
          <v-card-title class="bg-primary text-white">
            <v-icon class="mr-2">mdi-cloud-upload</v-icon>
            Upload de Notas Fiscais
          </v-card-title>
          
          <v-card-text class="pa-6">
            <FileUpload 
              @upload-success="handleUploadSuccess"
              @upload-error="handleUploadError"
              :disabled="!systemStore.loadServiceStatus"
            />
          </v-card-text>
        </v-card>

        <!-- Database Status -->
        <v-card elevation="2">
          <v-card-title class="bg-info text-white">
            <v-icon class="mr-2">mdi-database</v-icon>
            Status do Banco de Dados
          </v-card-title>
          
          <v-card-text>
            <DatabaseStatus />
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Chat Section -->
      <v-col cols="12" lg="6">
        <v-card elevation="3" style="height: 100%;">
          <AgentChat 
            :enabled="systemStore.chatEnabled"
            :key="chatKey"
          />
        </v-card>
      </v-col>
    </v-row>

    <!-- Success Snackbar -->
    <v-snackbar
      v-model="showSuccessSnackbar"
      color="success"
      timeout="5000"
      location="top"
    >
      <v-icon class="mr-2">mdi-check-circle</v-icon>
      {{ successMessage }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="showSuccessSnackbar = false"
        >
          Fechar
        </v-btn>
      </template>
    </v-snackbar>

    <!-- Error Snackbar -->
    <v-snackbar
      v-model="showErrorSnackbar"
      color="error"
      timeout="8000"
      location="top"
    >
      <v-icon class="mr-2">mdi-alert-circle</v-icon>
      {{ errorMessage }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="showErrorSnackbar = false"
        >
          Fechar
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSystemStore } from '../stores/system'
import FileUpload from '../components/FileUpload.vue'
import DatabaseStatus from '../components/DatabaseStatus.vue'
import AgentChat from '../components/AgentChat.vue'

const systemStore = useSystemStore()

// Reactive data
const showSuccessSnackbar = ref(false)
const showErrorSnackbar = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const chatKey = ref(0)

// Methods
function handleUploadSuccess(data) {
  successMessage.value = `Upload realizado com sucesso! ${data.processed_files} arquivo(s) processado(s).`
  showSuccessSnackbar.value = true
  
  // Refresh database status and enable chat if successful
  setTimeout(async () => {
    await systemStore.checkDatabaseStatus()
    if (systemStore.chatEnabled) {
      chatKey.value++ // Force chat component refresh
    }
  }, 2000)
}

function handleUploadError(error) {
  errorMessage.value = `Erro no upload: ${error}`
  showErrorSnackbar.value = true
}

// Lifecycle
onMounted(() => {
  systemStore.checkServicesStatus()
})
</script>

<style scoped>
.v-card-title {
  font-weight: 500;
}

.v-container {
  min-height: calc(100vh - 128px);
}
</style> 