<template>
  <div>
    <!-- File Drop Zone -->
    <v-card
      :class="[
        'file-drop-zone',
        { 'drag-over': isDragOver, 'disabled': disabled }
      ]"
      variant="outlined"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
      @click="!disabled && $refs.fileInput.click()"
    >
      <v-card-text class="text-center pa-8">
        <v-icon
          :color="disabled ? 'grey' : 'primary'"
          size="64"
          class="mb-4"
        >
          {{ isDragOver ? 'mdi-cloud-upload' : 'mdi-file-upload' }}
        </v-icon>
        
        <h3 class="text-h6 mb-2">
          {{ disabled ? 'Serviço Indisponível' : 'Arraste arquivos aqui ou clique para selecionar' }}
        </h3>
        
        <p class="text-body-2 text-medium-emphasis">
          {{ disabled ? 'O Load Service está offline' : 'Formatos aceitos: .zip (máx. 100MB)' }}
        </p>
        
        <input
          ref="fileInput"
          type="file"
          accept=".zip"
          style="display: none"
          @change="handleFileSelect"
          :disabled="disabled"
        />
      </v-card-text>
    </v-card>

    <!-- Selected Files List -->
    <v-list v-if="selectedFiles.length > 0" class="mt-4">
      <v-list-subheader>Arquivos Selecionados</v-list-subheader>
      <v-list-item
        v-for="(file, index) in selectedFiles"
        :key="index"
        :prepend-icon="getFileIcon(file.name)"
      >
        <v-list-item-title>{{ file.name }}</v-list-item-title>
        <v-list-item-subtitle>{{ formatFileSize(file.size) }}</v-list-item-subtitle>
        
        <template v-slot:append>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            @click="removeFile(index)"
            :disabled="uploading"
          />
        </template>
      </v-list-item>
    </v-list>

    <!-- Upload Controls -->
    <v-row v-if="selectedFiles.length > 0" class="mt-4">
      <v-col>
        <v-btn
          color="primary"
          :loading="uploading"
          :disabled="disabled"
          @click="uploadFiles"
          block
        >
          <v-icon class="mr-2">mdi-cloud-upload</v-icon>
          {{ uploading ? 'Enviando...' : 'Enviar Arquivo ZIP' }}
        </v-btn>
      </v-col>
      <v-col cols="auto">
        <v-btn
          variant="outlined"
          @click="clearFiles"
          :disabled="uploading"
        >
          Limpar
        </v-btn>
      </v-col>
    </v-row>

    <!-- Upload Progress -->
    <v-progress-linear
      v-if="uploading"
      :model-value="uploadProgress"
      color="primary"
      height="6"
      class="mt-4"
    />

    <!-- Upload Results -->
    <v-alert
      v-if="uploadResult"
      :type="uploadResult.type"
      class="mt-4"
      closable
      @click:close="uploadResult = null"
    >
      <div class="text-subtitle-2">{{ uploadResult.title }}</div>
      <div class="text-body-2">{{ uploadResult.message }}</div>
      
      <v-list v-if="uploadResult.details" dense class="mt-2">
        <v-list-item
          v-for="(detail, index) in uploadResult.details"
          :key="index"
          density="compact"
        >
          <v-list-item-title class="text-body-2">{{ detail }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-alert>
  </div>
</template>

<script setup>
import { ref, defineEmits, defineProps } from 'vue'
import axios from 'axios'

// Props
const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits(['upload-success', 'upload-error'])

// Reactive data
const selectedFiles = ref([])
const isDragOver = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref(null)

// Methods
function handleDragOver(event) {
  if (!props.disabled) {
    isDragOver.value = true
  }
}

function handleDragLeave(event) {
  isDragOver.value = false
}

function handleDrop(event) {
  if (props.disabled) return
  
  isDragOver.value = false
  const files = Array.from(event.dataTransfer.files)
  addFiles(files)
}

function handleFileSelect(event) {
  const files = Array.from(event.target.files)
  addFiles(files)
  event.target.value = '' // Reset input
}

function addFiles(files) {
  const validFiles = files.filter(file => {
    const isValidType = file.name.toLowerCase().endsWith('.zip')
    const isValidSize = file.size <= 100 * 1024 * 1024 // 100MB
    
    if (!isValidType) {
      showUploadResult('error', 'Arquivo Inválido', `${file.name}: Apenas arquivos .zip são aceitos`)
      return false
    }
    
    if (!isValidSize) {
      showUploadResult('error', 'Arquivo Muito Grande', `${file.name}: Tamanho máximo de 100MB`)
      return false
    }
    
    return true
  })
  
  // Only allow one file at a time since backend processes one ZIP file
  if (validFiles.length > 0) {
    selectedFiles.value = [validFiles[0]]
  }
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

function clearFiles() {
  selectedFiles.value = []
  uploadResult.value = null
}

function getFileIcon(filename) {
  if (filename.toLowerCase().endsWith('.zip')) {
    return 'mdi-folder-zip'
  }
  return 'mdi-file'
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

async function uploadFiles() {
  if (selectedFiles.value.length === 0) return
  
  uploading.value = true
  uploadProgress.value = 0
  uploadResult.value = null
  
  try {
    const formData = new FormData()
    if (selectedFiles.value.length > 0) {
      formData.append('file', selectedFiles.value[0])
    }
    
    const response = await axios.post('/api/load/upload-nfe-zip/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        uploadProgress.value = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
      }
    })
    
    const result = response.data
    
    showUploadResult(
      'success',
      'Upload Concluído',
      result.message || 'Arquivo processado com sucesso'
    )
    
    emit('upload-success', result)
    clearFiles()
    
  } catch (error) {
    console.error('Upload error:', error)
    
    let errorMessage = 'Erro desconhecido'
    if (error.response?.data?.detail) {
      errorMessage = error.response.data.detail
    } else if (error.message) {
      errorMessage = error.message
    }
    
    showUploadResult('error', 'Erro no Upload', errorMessage)
    emit('upload-error', errorMessage)
    
  } finally {
    uploading.value = false
    uploadProgress.value = 0
  }
}

function showUploadResult(type, title, message, details = null) {
  uploadResult.value = {
    type,
    title,
    message,
    details
  }
}
</script>

<style scoped>
.file-drop-zone {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px dashed #ccc;
}

.file-drop-zone:hover:not(.disabled) {
  border-color: #1976D2;
  background-color: rgba(25, 118, 210, 0.04);
}

.file-drop-zone.drag-over {
  border-color: #1976D2;
  background-color: rgba(25, 118, 210, 0.08);
}

.file-drop-zone.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style> 