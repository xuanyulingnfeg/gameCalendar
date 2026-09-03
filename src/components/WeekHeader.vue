<template>
  <div class="timeline-header">
    <div class="timeline-container">
      <!-- 周末背景 -->
      <span
        class="weekend-bg"
        v-for="day in weekendDays"
        :key="'w' + day.index"
        :style="{
          left: (day.index / totalDays) * 100 + '%',
          width: (1 / totalDays) * 100 + '%',
        }"
      ></span>
      <!-- 刻度线 -->
      <span
        class="tick"
        v-for="i in totalDays - 1"
        :key="i"
        :style="{ left: (i / totalDays) * 100 + '%' }"
      ></span>
      <!-- 日期标注 -->
      <span
        class="date-label"
        v-for="label in dateLabels"
        :key="label.day"
        :style="{ left: label.position + '%' }"
        >{{ label.text }}</span
      >
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  startDate: {
    type: String,
    required: true,
  },
  endDate: {
    type: String,
    required: true,
  },
  totalDays: {
    type: Number,
    required: true,
  },
});

// 每隔7天生成一个日期标注，首尾也标注
const dateLabels = computed(() => {
  const labels = [];
  const start = new Date(props.startDate);
  start.setHours(0, 0, 0, 0);

  for (let i = 0; i < props.totalDays; i += 7) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    labels.push({
      day: i,
      position: (i / props.totalDays) * 100,
      text: `${month}/${day}`,
    });
  }

  // 标注最后一天（endDate），如果不在7的倍数上
  const lastDayIndex = props.totalDays - 1;
  if (lastDayIndex % 7 !== 0) {
    const end = new Date(props.endDate);
    end.setHours(0, 0, 0, 0);
    const month = String(end.getMonth() + 1).padStart(2, "0");
    const day = String(end.getDate()).padStart(2, "0");
    labels.push({
      day: lastDayIndex,
      position: (lastDayIndex / props.totalDays) * 100,
      text: `${month}/${day}`,
    });
  }

  return labels;
});

// 计算周末天（周六和周日）
const weekendDays = computed(() => {
  const days = [];
  const start = new Date(props.startDate);
  start.setHours(0, 0, 0, 0);
  for (let i = 0; i < props.totalDays; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    const dayOfWeek = d.getDay(); // 0=Sunday, 6=Saturday
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      days.push({ index: i });
    }
  }
  return days;
});
</script>

<style scoped>
.timeline-header {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
  position: relative;
  background: rgba(255, 255, 255, 0.045);
}

.timeline-container {
  position: relative;
  height: 52px;
  width: 100%;
}

.tick {
  position: absolute;
  top: 34px;
  width: 1px;
  height: 8px;
  background: rgba(255, 255, 255, 0.18);
}

.date-label {
  position: absolute;
  top: 15px;
  padding-left: 9px;
  font-size: 11px;
  color: #9eb0c4;
  font-weight: 700;
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.weekend-bg {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.035);
}

@media (orientation: landscape) and (max-height: 600px) and (max-width: 1050px) {
  .timeline-header {
    border-radius: 10px;
  }

  .timeline-container {
    height: 42px;
  }

  .tick {
    top: 28px;
    height: 7px;
  }

  .date-label {
    top: 11px;
    padding-left: 7px;
    font-size: 10px;
  }
}
</style>
