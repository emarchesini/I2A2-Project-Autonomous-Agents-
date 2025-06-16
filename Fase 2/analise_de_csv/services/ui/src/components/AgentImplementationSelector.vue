<template>
  <div class="agent-implementation-selector">
    <div class="selector-container">
      <label for="implementation-select">Agent Organization:</label>
      <select 
        id="implementation-select" 
        v-model="selectedImplementation"
        @change="handleImplementationChange"
        :disabled="isLoading"
      >
        <option v-for="impl in implementations" :key="impl" :value="impl">
          {{ impl === 'default' ? 'SWARM' : impl === 'sel_group' ? 'SELECTOR_GROUP' : impl === 'graph_flow' ? 'GRAPH_FLOW' : impl }}
        </option>
      </select>
      <div v-if="isLoading" class="loading">Switching implementation...</div>
      <div v-if="error" class="error">{{ error }}</div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'AgentImplementationSelector',
  setup() {
    const implementations = ref([])
    const selectedImplementation = ref('')
    const isLoading = ref(false)
    const error = ref('')

    const fetchImplementations = async () => {
      try {
        const response = await axios.get('/api/agent/agent-implementations')
        implementations.value = response.data.implementations
        selectedImplementation.value = response.data.current
      } catch (err) {
        error.value = 'Failed to fetch agent implementations'
        console.error('Error fetching implementations:', err)
      }
    }

    const handleImplementationChange = async () => {
      if (!selectedImplementation.value) return

      isLoading.value = true
      error.value = ''

      try {
        await axios.post(`/api/agent/agent-implementations/${selectedImplementation.value}`)
        // Emit event to notify parent components
        window.dispatchEvent(new CustomEvent('agent-implementation-changed', {
          detail: { implementation: selectedImplementation.value }
        }))
      } catch (err) {
        error.value = 'Failed to switch implementation'
        console.error('Error switching implementation:', err)
        // Revert selection
        await fetchImplementations()
      } finally {
        isLoading.value = false
      }
    }

    onMounted(fetchImplementations)

    return {
      implementations,
      selectedImplementation,
      isLoading,
      error,
      handleImplementationChange
    }
  }
}
</script>

<style scoped>
.agent-implementation-selector {
  margin: 1rem 0;
  padding: 1rem;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.selector-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

label {
  font-weight: bold;
  min-width: 150px;
}

select {
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background-color: white;
  min-width: 200px;
}

.loading {
  color: #666;
  font-style: italic;
}

.error {
  color: #dc3545;
  margin-top: 0.5rem;
}
</style> 