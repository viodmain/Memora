<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'

const stats = ref({ memories: 0, documents: 0, prompts: 0 })
const recentMemories = ref<any[]>([])

const loadData = async () => {
  try {
    const [memRes, statsRes] = await Promise.all([
      api.get('/memory/', { params: { limit: 5 } }).catch(() => ({ data: [] })),
      api.get('/search/stats').catch(() => ({ data: { memories: 0, documents: 0, prompts: 0 } })),
    ])
    recentMemories.value = memRes.data
    stats.value = statsRes.data
  } catch (e) {
    console.error(e)
  }
}

onMounted(loadData)
</script>

<template>
  <div class="dashboard">
    <h1>Dashboard</h1>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-number">{{ stats.memories }}</div>
        <div class="stat-label">Memories</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.documents }}</div>
        <div class="stat-label">Documents</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.prompts }}</div>
        <div class="stat-label">Prompts</div>
      </div>
    </div>

    <h2>Recent Memories</h2>
    <div class="memory-list">
      <div v-for="m in recentMemories" :key="m.id" class="memory-item">
        <span class="memory-type">{{ m.memory_type }}</span>
        <span class="memory-content">{{ m.content }}</span>
      </div>
      <p v-if="!recentMemories.length" class="empty">No memories yet.</p>
    </div>
  </div>
</template>

<style scoped>
.dashboard { max-width: 900px; margin: 0 auto; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.5rem 0; }
.stat-card { background: #f5f5f5; border-radius: 8px; padding: 1.5rem; text-align: center; }
.stat-number { font-size: 2rem; font-weight: bold; color: #2563eb; }
.stat-label { color: #666; margin-top: 0.25rem; }
.memory-item { padding: 0.75rem; border-bottom: 1px solid #eee; display: flex; gap: 0.75rem; }
.memory-type { background: #e0e7ff; color: #3730a3; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; white-space: nowrap; }
.memory-content { color: #333; }
.empty { color: #999; font-style: italic; }
</style>
