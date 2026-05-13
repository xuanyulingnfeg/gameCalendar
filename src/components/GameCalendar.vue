<template>
  <div class="game-calendar">
    <div class="calendar-container">
      <div class="calendar-content">
        <!-- 今日指示器 -->
        <TodayIndicator :position="todayPosition" :label="todayLabel" />

        <!-- 周次表头 -->
        <WeekHeader :weeks="weeks" />

        <!-- 活动区域 -->
        <div class="activities-area">
          <ActivityBar
            v-for="activity in activities"
            :key="activity.id"
            :activity="activity"
            :totalWeeks="6"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import WeekHeader from "./WeekHeader.vue";
import ActivityBar from "./ActivityBar.vue";
import TodayIndicator from "./TodayIndicator.vue";
import {
  getWeeks,
  getPreciseTodayPosition,
  getTodayLabel,
} from "../utils/dateUtils.js";
import { activities } from "../config/activities.js";

const today = new Date();
const weeks = ref(getWeeks(today));
const todayPosition = ref(getPreciseTodayPosition(new Date()));
const todayLabel = ref(getTodayLabel(today));

let timer = null;

onMounted(() => {
  timer = setInterval(() => {
    todayPosition.value = getPreciseTodayPosition(new Date());
  }, 60000); // 每分钟更新一次
});

onUnmounted(() => {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
});
</script>

<style scoped>
.game-calendar {
  min-height: 100vh;
  background: #1a1a1a;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  box-sizing: border-box;
  isolation: isolate;
}

.calendar-container {
  width: 100%;
  max-width: 1100px;
  background: #2a2a2a;
  border-radius: 14px;
  padding: 50px 24px 30px;
  position: relative;
  /* 金属质感边框 - 使用多层实现 */
  border: 4px solid transparent;
  border-top-color: #b8b8b8;
  border-left-color: #a8a8a8;
  border-bottom-color: #5a5a5a;
  border-right-color: #6a6a6a;
  box-shadow:
    /* 最外层暗色轮廓 */
    0 0 0 2px #1a1a1a,
    0 0 0 3px #444,
    /* 外部投影增强立体感 */ 0 4px 12px rgba(0, 0, 0, 0.7),
    0 2px 4px rgba(0, 0, 0, 0.5),
    /* 内部顶部高光线 */ inset 0 1px 0 0 rgba(255, 255, 255, 0.15),
    inset 1px 0 0 0 rgba(255, 255, 255, 0.08),
    /* 内部底部暗线 */ inset 0 -1px 0 0 rgba(0, 0, 0, 0.4),
    inset -1px 0 0 0 rgba(0, 0, 0, 0.3),
    /* 内部整体微弱内阴影 */ inset 0 0 8px rgba(0, 0, 0, 0.3);
}

.calendar-container::before {
  content: "";
  position: absolute;
  top: -6px;
  left: -6px;
  right: -6px;
  bottom: -6px;
  border-radius: 18px;
  background: linear-gradient(
    135deg,
    #9a9a9a 0%,
    #c0c0c0 15%,
    #b0b0b0 30%,
    #858585 50%,
    #6a6a6a 70%,
    #7a7a7a 85%,
    #5a5a5a 100%
  );
  z-index: -1;
  box-shadow:
    0 0 0 2px #333,
    inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.calendar-container::after {
  content: "";
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  bottom: -1px;
  border-radius: 11px;
  border: 1px solid rgba(0, 0, 0, 0.5);
  pointer-events: none;
}

.calendar-content {
  position: relative;
}

.activities-area {
  margin-top: 20px;
  padding: 10px 0;
}
</style>
