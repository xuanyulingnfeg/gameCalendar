<template>
  <div class="week-header">
    <div class="week-cell" v-for="(week, index) in weeks" :key="index">
      <div class="week-label">{{ week.label }}</div>
      <div class="week-range">{{ week.range }}</div>
      <div class="week-ticks">
        <span
          class="tick"
          v-for="d in 6"
          :key="d"
          :style="{ left: (d / 7) * 100 + '%' }"
        ></span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  weeks: {
    type: Array,
    required: true,
  },
});
</script>

<style scoped>
.week-header {
  display: flex;
  background: #f0f0f0;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #ccc;
}

.week-cell {
  flex: 1;
  padding: 8px 10px;
  text-align: left;
  border-right: 1px solid #ccc;
  position: relative;
}

.week-cell:last-child {
  border-right: none;
}

.week-label {
  font-size: 13px;
  font-weight: bold;
  color: #333;
}

.week-range {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.week-ticks {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 6px;
}

.tick {
  position: absolute;
  top: 0;
  width: 1px;
  height: 100%;
  background: #999;
}
</style>
