<script>
  import { onMount } from 'svelte';
  import { navigating } from '$app/stores';
  import '../styles.css';

  let loading = true;
  
  onMount(() => {
    loading = false;
  });
</script>

<div class="app-container">
  <header>
    <div class="brand">
      <img src="/logo.svg" alt="Nexus AI Logo" />
      <h1>Nexus AI</h1>
    </div>
    <nav>
      <ul>
        <li><a href="/" class:active={$page.url.pathname === '/'}>Chat</a></li>
        <li><a href="/memory" class:active={$page.url.pathname === '/memory'}>Memory</a></li>
        <li><a href="/calendar" class:active={$page.url.pathname === '/calendar'}>Calendar</a></li>
        <li><a href="/settings" class:active={$page.url.pathname === '/settings'}>Settings</a></li>
      </ul>
    </nav>
  </header>

  <main>
    {#if $navigating || loading}
      <div class="loading-container">
        <div class="spinner"></div>
        <p>Loading...</p>
      </div>
    {:else}
      <slot />
    {/if}
  </main>

  <footer>
    <p>Nexus AI &copy; {new Date().getFullYear()} | Version 0.1.0</p>
  </footer>
</div>

<style>
  .app-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }
  
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background-color: var(--bs-body-bg);
    border-bottom: 1px solid var(--bs-border-color);
  }
  
  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  
  .brand img {
    height: 40px;
    width: auto;
  }
  
  .brand h1 {
    font-size: 1.5rem;
    margin: 0;
  }
  
  nav ul {
    display: flex;
    gap: 1rem;
    list-style: none;
    margin: 0;
    padding: 0;
  }
  
  nav a {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    text-decoration: none;
    color: var(--bs-secondary-color);
    transition: all 0.2s ease;
  }
  
  nav a:hover {
    background-color: var(--bs-tertiary-bg);
    color: var(--bs-body-color);
  }
  
  nav a.active {
    background-color: var(--bs-primary);
    color: white;
  }
  
  main {
    flex: 1;
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }
  
  footer {
    padding: 1rem;
    text-align: center;
    border-top: 1px solid var(--bs-border-color);
    font-size: 0.875rem;
    color: var(--bs-secondary-color);
  }
  
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 400px;
  }
  
  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(0, 0, 0, 0.1);
    border-radius: 50%;
    border-top-color: var(--bs-primary);
    animation: spin 1s ease-in-out infinite;
    margin-bottom: 1rem;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>