<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { promptApi } from '../api/client'

const prompts = ref<any[]>([])
const selectedPrompt = ref<any>(null)
const selectedVersion = ref<any>(null)
const newName = ref('')
const newContent = ref('')
const loading = ref(false)

const loadPrompts = async () => {
  const res = await promptApi.list()
  prompts.value = res.data
}

const selectPrompt = async (name: string) => {
  const res = await promptApi.get(name)
  selectedPrompt.value = res.data.prompt
  selectedVersion.value = res.data.version
}

const addPrompt = async () => {
  if (!newName.value.trim() || !newContent.value.trim()) return
  loading.value = true
  try {
    await promptApi.save({ name: newName.value, content: newContent.value })
    newName.value = ''
    newContent.value = ''
    await loadPrompts()
  } finally {
    loading.value = false
  }
}

const deletePrompt = async (name: string) => {
  await promptApi.delete(name)
  if (selectedPrompt.value?.name === name) {
    selectedPrompt.value = null
    selectedVersion.value = null
  }
  await loadPrompts()
}

onMounted(loadPrompts)
</script>

<template>
  <div class="prompt-view">
    <h1>Prompts</h1>

    <h2>Add Prompt</h2>
    <div class="add-form">
      <input v-model="newName" placeholder="Prompt name" />
      <textarea v-model="newContent" placeholder="Prompt content..." rows="3"></textarea>
      <button @click="addPrompt" :disabled="loading">Save</button>
    </div>

    <div class="content-layout">
      <div class="prompt-list">
        <h2>Templates ({{ prompts.length }})</h2>
        <div
          v-for="p in prompts" :key="p.id"
          class="prompt-item"
          :class="{ active: selectedPrompt?.name === p.name }"
          @click="selectPrompt(p.name)"
        >
          <span class="prompt-name">{{ p.name }}</span>
          <span class="prompt-ver">v{{ p.latest_version }}</span>
          <button class="delete-btn" @click.stop="deletePrompt(p.name)">×</button>
        </div>
        <p v-if="!prompts.length" class="empty">No prompts.</p>
      </div>

      <div class="prompt-detail" v-if="selectedVersion">
        <h3>{{ selectedPrompt.name }} <span class="ver">v{{ selectedVersion.version }}</span></h3>
        <pre class="prompt-content">{{ selectedVersion.content }}</pre>
        <div v-if="selectedVersion.variables?.length" class="variables">
          <strong>Variables:</strong> {{ selectedVersion.variables.join(', ') }}
        </div>
        <div v-if="selectedVersion.score" class="score">
          <strong>Score:</strong> {{ selectedVersion.score }}/5
        </div>
      </div>
      <div class="prompt-detail empty" v-else>
        <p>Select a prompt to view details.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.prompt-view { max-width: 1000px; margin: 0 auto; }
.add-form { display: flex; flex-direction: column; gap: 0.5rem; margin: 1rem 0; }
.add-form input, .add-form textarea { padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; font-family: inherit; }
.add-form button { padding: 0.5rem 1rem; background: #16a34a; color: white; border: none; border-radius: 4px; cursor: pointer; align-self: flex-start; }
.content-layout { display: grid; grid-template-columns: 250px 1fr; gap: 1.5rem; margin-top: 1rem; }
.prompt-list { border-right: 1px solid #eee; padding-right: 1rem; }
.prompt-item { padding: 0.75rem; border-bottom: 1px solid #eee; cursor: pointer; display: flex; gap: 0.5rem; align-items: center; }
.prompt-item:hover { background: #f9fafb; }
.prompt-item.active { background: #e0e7ff; }
.prompt-name { flex: 1; font-weight: 500; }
.prompt-ver { color: #666; font-size: 0.85rem; }
.delete-btn { background: none; border: none; color: #dc2626; font-size: 1.2rem; cursor: pointer; }
.prompt-detail { padding: 1rem; }
.prompt-content { background: #f5f5f5; padding: 1rem; border-radius: 4px; white-space: pre-wrap; font-size: 0.9rem; overflow-x: auto; }
.variables { margin-top: 0.75rem; color: #555; }
.score { margin-top: 0.5rem; color: #555; }
.ver { color: #666; font-weight: normal; }
.empty { color: #999; font-style: italic; }
</style>
