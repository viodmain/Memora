<script setup lang="ts">
</script>

<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-brand">Memora</div>
      <div class="nav-links">
        <router-link to="/">Dashboard</router-link>
        <router-link to="/memory">Memory</router-link>
        <router-link to="/knowledge">Knowledge</router-link>
        <router-link to="/prompt">Prompts</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1a1a1a; background: #fafafa; }
.navbar { background: #1e293b; color: white; padding: 0 1.5rem; display: flex; align-items: center; height: 50px; }
.nav-brand { font-size: 1.2rem; font-weight: bold; margin-right: 2rem; }
.nav-links { display: flex; gap: 1.25rem; }
.nav-links a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; }
.nav-links a:hover, .nav-links a.router-link-active { color: white; }
.main-content { padding: 1.5rem; }
</style>
