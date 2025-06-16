import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'

export const useSystemStore = defineStore('system', () => {
  // State
  const loadServiceStatus = ref(false)
  const agentServiceStatus = ref(false)
  const databasePopulated = ref(false)
  const chatEnabled = ref(false)
  
  // Actions
  async function checkServicesStatus() {
    try {
      // Check Load Service - use absolute URL
      const loadResponse = await axios.get('http://localhost:8080/api/load/health', { timeout: 5000 })
      loadServiceStatus.value = loadResponse.status === 200
    } catch (error) {
      console.warn('Load Service offline:', error.message)
      loadServiceStatus.value = false
    }

    try {
      // Check Agent Service - use absolute URL
      const agentResponse = await axios.get('http://localhost:8080/api/agent/', { timeout: 5000 })
      agentServiceStatus.value = agentResponse.status === 200
    } catch (error) {
      console.warn('Agent Service offline:', error.message)
      agentServiceStatus.value = false
    }

    // Check if database is populated
    await checkDatabaseStatus()
  }

  async function checkDatabaseStatus() {
    try {
      const response = await axios.get('http://localhost:8080/api/load/status')
      databasePopulated.value = response.data.total_records > 0
      chatEnabled.value = databasePopulated.value && agentServiceStatus.value
    } catch (error) {
      console.warn('Could not check database status:', error.message)
      databasePopulated.value = false
      chatEnabled.value = false
    }
  }

  function enableChat() {
    chatEnabled.value = true
  }

  function disableChat() {
    chatEnabled.value = false
  }

  return {
    // State
    loadServiceStatus,
    agentServiceStatus,
    databasePopulated,
    chatEnabled,
    
    // Actions
    checkServicesStatus,
    checkDatabaseStatus,
    enableChat,
    disableChat
  }
}) 