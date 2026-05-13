<template>
  <div class="game-calendar">
    <!-- 游戏类型切换按钮 -->
    <div class="game-type-switcher">
      <button
        v-for="gameType in gameTypes"
        :key="gameType.key"
        :class="['game-type-btn', { active: currentGameType === gameType.key }]"
        :style="
          gameType.bgImage
            ? { backgroundImage: `url(${gameType.bgImage})` }
            : {}
        "
        @click="switchGameType(gameType.key)"
      >
        {{ gameType.name }}
      </button>
    </div>

    <div class="calendar-container" ref="calendarContainerEl">
      <div class="calendar-content">
        <!-- 今日指示器 -->
        <TodayIndicator
          :position="todayPosition"
          :height="todayHeight"
          :label="todayLabel"
        />

        <!-- 时间轴表头 -->
        <WeekHeader
          :startDate="currentConfig.startDate"
          :endDate="currentConfig.endDate"
          :totalDays="timelineInfo.totalDays"
        />

        <!-- 活动区域 -->
        <div class="activities-area">
          <!-- Red 活动条：同一行 -->
          <div class="activity-row red-row">
            <ActivityBar
              v-for="(activity, index) in redActivities"
              :key="index"
              :activity="activity"
              :calendarStartDate="currentConfig.startDate"
              :calendarEndDate="currentConfig.endDate"
              :totalDays="timelineInfo.totalDays"
              :absolute="true"
            />
          </div>

          <!-- 其他活动条：各自一行 -->
          <ActivityBar
            v-for="(activity, index) in otherActivities"
            :key="index"
            :activity="activity"
            :calendarStartDate="currentConfig.startDate"
            :calendarEndDate="currentConfig.endDate"
            :totalDays="timelineInfo.totalDays"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import WeekHeader from "./WeekHeader.vue";
import ActivityBar from "./ActivityBar.vue";
import TodayIndicator from "./TodayIndicator.vue";
import {
  getTimelineInfo,
  getPreciseTodayPosition,
  getTodayLabel,
} from "../utils/dateUtils.js";
import { gameTypes, gameData } from "../config/activities.js";

// 当前选中的游戏类型（优先读取localStorage记录）
const savedGameType = localStorage.getItem("currentGameType");
const currentGameType = ref(
  savedGameType && gameData[savedGameType] ? savedGameType : "zzz",
);

// 切换游戏类型并保存到localStorage
function switchGameType(key) {
  currentGameType.value = key;
  localStorage.setItem("currentGameType", key);
}

// 当前游戏类型的配置和活动
const currentConfig = computed(
  () => gameData[currentGameType.value].calendarConfig,
);
const currentActivities = computed(
  () => gameData[currentGameType.value].activities,
);

// 将活动分为两组：red类型（同行）和其他类型（各自一行）
const redActivities = computed(() => {
  const reds = currentActivities.value
    .filter((a) => a.type === "red")
    .map((a) => ({ ...a }));
  // 时间接续处理
  for (let i = 1; i < reds.length; i++) {
    if (reds[i].startTime > reds[i - 1].endTime) {
      reds[i].startTime = reds[i - 1].endTime;
    }
  }
  return reds;
});

const otherActivities = computed(() => {
  return currentActivities.value.filter((a) => a.type !== "red");
});

const today = new Date();
const timelineInfo = computed(() =>
  getTimelineInfo(currentConfig.value.startDate, currentConfig.value.endDate),
);

// 用于触发 todayPosition 定时更新的响应式时间戳
const now = ref(new Date());
const todayPosition = computed(() =>
  getPreciseTodayPosition(
    currentConfig.value.startDate,
    currentConfig.value.endDate,
    now.value,
  ),
);
const todayLabel = ref(getTodayLabel(today));
const calendarContainerEl = ref(null);

// 动态计算今日指示器高度，覆盖整个活动区域
const todayHeight = computed(() => {
  return calendarContainerEl?.value?.offsetHeight || 0;
});

let timer = null;

onMounted(() => {
  timer = setInterval(() => {
    now.value = new Date();
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
  background: url("../assets/background.jpg") no-repeat center center fixed;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  box-sizing: border-box;
  isolation: isolate;
}

.calendar-container {
  width: 100%;
  min-width: 1400px;
  max-width: 1600px;
  /* background: #2a2a2a; */
  border-radius: 40px;
  /* padding: 10px; */
  position: relative;
  /* 金属质感边框 - 使用多层实现 */
  border: 20px solid transparent;
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
  top: -20px;
  left: -20px;
  right: -20px;
  bottom: -20px;
  border-radius: 40px;
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
  height: 20px;
  top: 72px;
  width: 100%;
  pointer-events: none;
  background: linear-gradient(to right, #acacac, #6f6f6f);
}

.calendar-content {
  padding: 10px;
  position: relative;
  background: #2a2a2a;
  border-radius: 20px;
}

.activities-area {
  margin-top: 30px;
  padding: 10px 0;
  overflow: hidden;
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
}

.activities-area::-webkit-scrollbar {
  width: 6px;
}

.activities-area::-webkit-scrollbar-track {
  background: transparent;
}

.activities-area::-webkit-scrollbar-thumb {
  background: #acacac;
  border-radius: 3px;
}

.activity-row.red-row {
  position: relative;
  height: 54px;
  margin-bottom: 14px;
}

.red-row .activity-bar {
  position: absolute;
  top: 0;
  margin-bottom: 0;
}

.game-type-switcher {
  display: flex;
  gap: 15px;
  align-self: flex-start;
  width: 100%;
  min-width: 1400px;
  max-width: 1600px;
  margin: 0 auto 32px;
}

.game-type-btn {
  width: 160px;
  height: 80px;
  border: 3px solid #555;
  border-radius: 12px;
  background: #333;
  background-size: cover;
  background-position: center;
  color: #ccc;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}

.game-type-btn:hover {
  border-color: #888;
  color: #fff;
  transform: scale(1.05);
}

.game-type-btn.active {
  border-color: #e63946;
  box-shadow: 0 0 10px rgba(230, 57, 70, 0.5);
  color: #fff;
}
</style>
