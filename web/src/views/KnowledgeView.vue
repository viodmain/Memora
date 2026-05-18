<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '../api/client'

const documents = ref<any[]>([])
const query = ref('')
const searchResults = ref<any[]>([])
const ingestPath = ref('')
const loading = ref(false)

const loadDocuments = async () => {
  const res = await knowledgeApi.listDocuments()
  documents.value = res.data
}

const search = async () => {
  if (!query.value.trim()) { searchResults.value = []; return }
  loading.value = true
  try {
    const res = await knowledgeApi.search(query.value, 10)
    searchResults.value = res.data
  } finally {
    loading.value = false
  }
}

const ingest = async () => {
  if (!ingestPath.value.trim()) return
  loading.value = true
  try {
    await knowledgeApi.ingest(ingestPath.value)
    ingestPath.value = ''
    await loadDocuments()
  } finally {
    loading.value = false
  }
}

const deleteDoc = async (id: string) => {
  await knowledgeApi.deleteDocument(id)
  await loadDocuments()
}

onMounted(loadDocuments)
</script>

<template>
  <div class="knowledge-view">
    <h1>Knowledge Base</h1>

    <div class="search-bar">
      <input v-model="query" placeholder="Search documents..." @keyup.enter="search" />
      <button @click="search" :disabled="loading">{{ loading ? '...' : 'Search' }}</button>
    </div>

    <div v-if="searchResults.length" class="search-results">
      <h3>Search Results</h3>
      <div v-for="c in searchResults" :key="c.id" class="chunk-item">
        <span class="chunk-idx">Chunk {{ c.chunk_index }}</span>
        <span>{{ c.content }}</span>
      </div>
    </div>

    <h2>Ingest Document</h2>
    <div class="ingest-form">
      <input v-model="ingestPath" placeholder="File path (e.g. /home/user/docs/api.md)" @keyup.enter="ingest" />
      <button @click="ingest" :disabled="loading">Ingest</button>
    </div>

    <h2>Documents ({{ documents.length }})</h2>
    <div class="doc-list">
      <div v-for="d in documents" :key="d.id" class="doc-item">
        <span class="doc-type">{{ d.file_type }}</span>
        <span class="doc-title">{{ d.title }}</span>
        <span class="doc-chunks">{{ d.chunk_count }} chunks</span>
        <button class="delete-btn" @click="deleteDoc(d.id)">×</button>
      </div>
      <p v-if="!documents.length" class="empty">No documents ingested.</p>
    </div>
  </div>
</template>

<style scoped>
.knowledge-view { max-width: 900px; margin: 0 auto; }
.search-bar { display: flex; gap: 0.5rem; margin: 1rem 0; }
.search-bar input { flex: 1; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
.search-bar button { padding: 0.5rem 1rem; background: #2563eb; color: white; border: none; border-radius: 4px; cursor: pointer; }
.ingest-form { display: flex; gap: 0.5rem; margin: 1rem 0; }
.ingest-form input { flex: 1; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
.ingest-form button { padding: 0.5rem 1rem; background: #16a34a; color: white; border: none; border-radius: 4px; cursor: pointer; }
.chunk-item { padding: 0.75rem; border-bottom: 1px solid #eee; display: flex; gap: 0.75rem; }
.chunk-idx { background: #fef3c7; color: #92400e; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; white-space: nowrap; }
.doc-item { padding: 0.75rem; border-bottom: 1px solid #eee; display: flex; gap: 0.75rem; align-items: center; }
.doc-type { background: #dbeafe; color: #1e40af; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }
.doc-title { flex: 1; color: #333; }
.doc-chunks { color: #666; font-size: 0.85rem; }
.delete-btn { background: none; border: none; color: #dc2626; font-size: 1.2rem; cursor: pointer; }
.empty { color: #999; font-style: italic; }
</style>
