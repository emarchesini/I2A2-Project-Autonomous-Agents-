<template>
  <v-app>
    <v-app-bar
      app
      color="primary"
      dark
      elevation="4"
    >
      <v-app-bar-title>
        <v-icon class="mr-2">mdi-file-document-multiple</v-icon>
        NF Agent - Sistema Integrado
      </v-app-bar-title>
      
      <v-spacer></v-spacer>
      
      <v-chip
        :color="systemStatus.color"
        :prepend-icon="systemStatus.icon"
        variant="outlined"
        class="mr-2"
      >
        {{ systemStatus.text }}
      </v-chip>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>

    <v-footer app color="grey-lighten-3" class="text-center">
      <div>
        © 2025 NF Agent System - Processamento Inteligente de Notas Fiscais
      </div>
    </v-footer>
  </v-app>
</template>

<script setup>
import { computed } from 'vue'
import { useSystemStore } from './stores/system'

const systemStore = useSystemStore()

const systemStatus = computed(() => {
  if (systemStore.loadServiceStatus && systemStore.agentServiceStatus) {
    return {
      color: 'success',
      icon: 'mdi-check-circle',
      text: 'Todos os Serviços Online'
    }
  } else if (systemStore.loadServiceStatus || systemStore.agentServiceStatus) {
    return {
      color: 'warning',
      icon: 'mdi-alert-circle',
      text: 'Serviços Parcialmente Online'
    }
  } else {
    return {
      color: 'error',
      icon: 'mdi-close-circle',
      text: 'Serviços Offline'
    }
  }
})

// Check services status on mount
systemStore.checkServicesStatus()
</script>

<style scoped>
.v-app-bar-title {
  font-weight: 500;
}
</style> 