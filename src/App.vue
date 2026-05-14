<template>
  <GameCalendar />
</template>

<script setup>
import GameCalendar from "./components/GameCalendar.vue";
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
    Arial, "Noto Sans SC", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: #1a1a1a;
}

#app {
  width: 100%;
}

html,
body,
#app {
  height: 100%;
}
</style>
