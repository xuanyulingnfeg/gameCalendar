<template>
  <div class="today-indicator" :style="{ left: position * 100 + '%' }">
    <div class="today-label">{{ label }}</div>
    <div class="today-line"></div>
  </div>
</template>

<script setup>
defineProps({
  position: {
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
  top: -28px;
  z-index: 10;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}

.today-label {
  background: #e63946;
  color: #fff;
  font-size: 13px;
  font-weight: bold;
  padding: 3px 12px;
  border-radius: 4px;
  white-space: nowrap;
  margin-bottom: 0;
}

.today-line {
  width: 2px;
  background: #e63946;
  position: absolute;
  top: 26px;
  bottom: 0;
  height: 600px;
}
</style>
