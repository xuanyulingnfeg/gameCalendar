<template>
  <div class="today-indicator" :style="{ left: position * 100 + '%' }">
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
  top: -50px;
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
  width: 3px;
  background: #e63946;
  position: absolute;
  top: 20px;
  bottom: 0;
}
</style>
