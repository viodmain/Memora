<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { memoryApi } from '../api/client'

const memories = ref<any[]>([])
const query = ref('')
const searchResults = ref<any[]>([])
const newContent = ref('')
const newType = ref('fact')
const loading = ref(false)

const loadMemories = async () => {
  const res = await memoryApi.list({ limit: 50 })
  memories.value = res.data
}

const search = async () => {
  if (!query.value.trim()) { searchResults.value = []; return }
  loading.value = true
  try {
    const res = await memoryApi.recall(query.value, 10)
    searchResults.value = res.data
  } finally {
    loading.value = false
  }
}

const addMemory = async () => {
  if (!newContent.value.trim()) return
  await memoryApi.save({ content: newContent.value, memory_type: newType.value, source: 'web' })
  newContent.value = ''
  await loadMemories()
}

const deleteMemory = async (id: string) => {
  await memoryApi.delete(id)
  await loadMemories()
}

onMounted(loadMemories)
</script>

<template>
  <div class="memory-view">
    <h1>Memories</h1>

    <div class="search-bar">
      <input v-model="query" placeholder="Search memories..." @keyup.enter="search" />
      <button @click="search" :disabled="loading">{{ loading ? '...' : 'Search' }}</button>
    </div>

    <div v-if="searchResults.length" class="search-results">
      <h3>Search Results</h3>
      <div v-for="m in searchResults" :key="m.id" class="memory-item">
        <span class="memory-type">{{ m.memory_type }}</span>
        <span>{{ m.content }}</span>
      </div>
    </div>

    <h2>Add Memory</h2>
    <div class="add-form">
      <select v-model="newType">
        <option value="fact">Fact</option>
        <option value="preference">Preference</option>
        <option value="decision">Decision</option>
        <option value="experience">Experience</option>
      </select>
      <input v-model="newContent" placeholder="Memory content..." @keyup.enter="addMemory" />
      <button @click="addMemory">Add</button>
    </div>

    <h2>All Memories ({{ memories.length }})</h2>
    <div class="memory-list">
      <div v-for="m in memories" :key="m.id" class="memory-item">
        <span class="memory-type">{{ m.memory_type }}</span>
        <span class="memory-content">{{ m.content }}</span>
        <button class="delete-btn" @click="deleteMemory(m.id)">×</button>
      </div>
      <p v-if="!memories.length" class="empty">No memories.</p>
    </div>
  </div>
</template>

<style scoped>
.memory-view { max-width: 900px; margin: 0 auto; }
.search-bar { display: flex; gap: 0.5rem; margin: 1rem 0; }
.search-bar input { flex: 1; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
.search-bar button { padding: 0.5rem 1rem; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; }
.add-form { display: flex; gap: 0.5rem; margin: 1rem 0; }
.add-form select, .add-form input { padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
.add-form input { flex: 1; }
.add-form button { padding: 0.5rem 1rem; background: #16a34a; color: white; border: none; border-radius: 4px; cursor: pointer; }
.memory-item { padding: 0.75rem; border-bottom: 1px solid #eee; display: flex; gap: 0.75rem; align-items: center; }
.memory-type { background: #e0e7ff; color: #3730a3; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; white-space: nowrap; }
.memory-content { flex: 1; color: #333; }
.delete-btn { background: none; border: none; color: #dc2626; font-size: 1.2rem; cursor: pointer; }
.empty { color: #999; font-style: italic; }
</style>
