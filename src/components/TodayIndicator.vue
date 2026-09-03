<template>
  <div
    class="today-indicator"
    :style="{ left: `calc(10px + ${position * 100}% * (1 - 20px / 100%))` }"
  >
    <div class="today-label">{{ label }}</div>
    <div class="today-line" :style="{ height: height - 10 + 'px' }"></div>
  </div>
</template>

<script setup>
defineProps({
  position: {
    type: Number,
    required: true,
  },
  height: {
    type: Number,
    required: true,
  },
  label: {
    type: String,
    required: true,
  },
});
</script>

<style scoped>
.today-indicator {
  position: absolute;
  top: 3px;
  z-index: 12;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}

.today-label {
  background: #ff607a;
  box-shadow: 0 6px 18px rgba(255, 76, 107, 0.28);
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  padding: 5px 10px;
  border-radius: 7px;
  white-space: nowrap;
  margin-bottom: 0;
}

.today-line {
  width: 2px;
  background: linear-gradient(#ff607a 0%, rgba(255, 96, 122, 0.55) 70%, transparent 100%);
  position: absolute;
  top: 22px;
  bottom: 0;
}
</style>
