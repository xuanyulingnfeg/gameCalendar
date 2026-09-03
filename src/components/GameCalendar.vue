<template>
  <div class="game-calendar">
    <div class="page-shell">
      <header class="page-header">
        <div class="title-group">
          <span class="eyebrow">GAME SCHEDULE</span>
          <h1>游戏活动日历</h1>
          <p>限时卡池、版本活动一览</p>
        </div>

        <nav class="game-type-switcher" aria-label="选择游戏">
          <button
            v-for="gameType in gameTypes"
            :key="gameType.key"
            :class="[
              'game-type-btn',
              { active: currentGameType === gameType.key },
            ]"
            :aria-pressed="currentGameType === gameType.key"
            @click="switchGameType(gameType.key)"
          >
            <span
              class="game-cover"
              :style="
                gameType.bgImage
                  ? { backgroundImage: `url(${gameType.bgImage})` }
                  : {}
              "
            ></span>
            <span class="game-name">{{ gameType.name }}</span>
            <span class="selected-dot" aria-hidden="true"></span>
          </button>
        </nav>
      </header>

      <main
        class="calendar-container"
        ref="calendarContainerEl"
        v-if="!loading && currentConfig.startDate"
      >
        <div class="calendar-toolbar">
          <div>
            <span class="toolbar-kicker">当前版本</span>
            <div class="date-range">{{ formattedDateRange }}</div>
          </div>

          <div class="calendar-summary">
            <div class="summary-item">
              <strong>{{ currentActivities.length }}</strong>
              <span>全部活动</span>
            </div>
            <div class="summary-divider"></div>
            <div class="summary-item">
              <strong>{{ ongoingCount }}</strong>
              <span>正在进行</span>
            </div>
          </div>

          <div class="legend" aria-label="活动类型图例">
            <span><i class="legend-dot banner"></i>限时卡池</span>
            <span><i class="legend-dot event"></i>版本活动</span>
            <span><i class="legend-dot bonus"></i>奖励活动</span>
          </div>
        </div>

        <div class="calendar-scroll">
          <div class="calendar-content">
            <!-- 今日指示器 -->
            <TodayIndicator
              :position="todayPosition"
              :height="todayHeight"
              :label="todayLabel"
            />

            <!-- 鼠标悬浮指示器 -->
            <div
              class="mouse-indicator"
              :class="{ visible: showMouseIndicator }"
              :style="{ left: mouseIndicatorX + 'px' }"
              aria-hidden="true"
            >
              <div class="mouse-indicator-label">{{ mouseIndicatorLabel }}</div>
              <div class="mouse-indicator-line"></div>
            </div>

            <!-- 时间轴表头 -->
            <WeekHeader
              :startDate="currentConfig.startDate"
              :endDate="currentConfig.endDate"
              :totalDays="timelineInfo.totalDays"
            />

            <!-- 活动区域 -->
            <div
              class="activities-area"
              @mousemove="onActivitiesMouseMove"
              @mouseleave="onActivitiesMouseLeave"
              ref="activitiesAreaEl"
            >
              <!-- Red 活动条：按行分组，重叠的分行显示 -->
              <div
                class="activity-row red-row"
                v-for="(row, rowIndex) in redActivityRows"
                :key="'red-row-' + rowIndex"
              >
                <ActivityBar
                  v-for="(activity, index) in row"
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
      </main>

      <div class="loading-state" v-else-if="loading">正在整理活动日程…</div>
      <div class="loading-state" v-else>暂时没有可显示的日程</div>
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

// 响应式数据
const gameTypes = ref([]);
const gameData = ref({});
const loading = ref(true);

// 加载配置
async function loadConfig() {
  try {
    const res = await fetch("./config/activities.json");
    const data = await res.json();
    gameTypes.value = data.gameTypes;
    gameData.value = data.gameData;
    loading.value = false;
  } catch (e) {
    console.error("Failed to load activities config:", e);
    loading.value = false;
  }
}

// 当前选中的游戏类型（优先读取localStorage记录）
const savedGameType = localStorage.getItem("currentGameType");
const currentGameType = ref(savedGameType || "zzz");

// 切换游戏类型并保存到localStorage
function switchGameType(key) {
  currentGameType.value = key;
  localStorage.setItem("currentGameType", key);
}

// 当前游戏类型的配置和活动
const currentConfig = computed(() => {
  const data = gameData.value[currentGameType.value];
  return data ? data.calendarConfig : { startDate: "", endDate: "" };
});

// 解析活动时间字符串
function parseActivityTime(timeStr, isEnd = false) {
  const parts = timeStr.split(" ");
  const [year, month, day] = parts[0].split("-");
  let hour = isEnd ? 24 : 0;
  if (parts.length > 1) {
    hour = parseInt(parts[1]);
  }
  return new Date(year, month - 1, day, hour, 0, 0, 0);
}

// 用于触发定时更新的响应式时间戳
const now = ref(new Date());

const currentActivities = computed(() => {
  const data = gameData.value[currentGameType.value];
  if (!data) return [];
  // 过滤掉结束时间小于当前时间的活动（red类型固定显示）
  return data.activities.filter((a) => {
    if (a.type === "red") return true;
    const endTime = parseActivityTime(a.endTime, true);
    return endTime > now.value;
  });
});

// 将red活动按时间重叠分行
const redActivityRows = computed(() => {
  const reds = currentActivities.value
    .filter((a) => a.type === "red")
    .map((a) => ({ ...a }));
  // 时间接续处理
  for (let i = 1; i < reds.length; i++) {
    if (reds[i].startTime > reds[i - 1].endTime) {
      reds[i].startTime = reds[i - 1].endTime;
    }
  }
  // 贪心分行：时间重叠的放不同行
  const rows = [];
  for (const act of reds) {
    const actStart = parseActivityTime(act.startTime, false);
    const actEnd = parseActivityTime(act.endTime, true);
    let placed = false;
    for (const row of rows) {
      const hasOverlap = row.some((existing) => {
        const exStart = parseActivityTime(existing.startTime, false);
        const exEnd = parseActivityTime(existing.endTime, true);
        return actStart < exEnd && actEnd > exStart;
      });
      if (!hasOverlap) {
        row.push(act);
        placed = true;
        break;
      }
    }
    if (!placed) {
      rows.push([act]);
    }
  }
  return rows;
});

const otherActivities = computed(() => {
  return currentActivities.value.filter((a) => a.type !== "red");
});

const formattedDateRange = computed(() => {
  if (!currentConfig.value.startDate) return "";
  const format = (value) => {
    const date = new Date(value);
    return `${String(date.getMonth() + 1).padStart(2, "0")}月${String(date.getDate()).padStart(2, "0")}日`;
  };
  return `${format(currentConfig.value.startDate)} — ${format(currentConfig.value.endDate)}`;
});

const ongoingCount = computed(() => {
  return currentActivities.value.filter((activity) => {
    const start = parseActivityTime(activity.startTime, false);
    const end = parseActivityTime(activity.endTime, true);
    return start <= now.value && end > now.value;
  }).length;
});

const today = new Date();
const timelineInfo = computed(() =>
  getTimelineInfo(currentConfig.value.startDate, currentConfig.value.endDate),
);

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

// 鼠标指示器
const activitiesAreaEl = ref(null);
const showMouseIndicator = ref(false);
const mouseIndicatorX = ref(0);
const mouseIndicatorLabel = ref("");

function onActivitiesMouseMove(e) {
  const rect = activitiesAreaEl.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  // 指示器现在在 calendar-content 层级，需加上 calendar-content 的 padding(10px)
  mouseIndicatorX.value = x + 10;
  showMouseIndicator.value = true;

  // 计算鼠标位置对应的日历时间
  const ratio = x / rect.width;
  const calStart = new Date(currentConfig.value.startDate);
  calStart.setHours(0, 0, 0, 0);
  const totalMs = timelineInfo.value.totalDays * 24 * 60 * 60 * 1000;
  const targetDate = new Date(calStart.getTime() + ratio * totalMs);
  const month = targetDate.getMonth() + 1;
  const day = targetDate.getDate();
  const hour = targetDate.getHours();
  mouseIndicatorLabel.value = `${month}月${day}日 ${hour.toString().padStart(2, "0")}:00`;
}

function onActivitiesMouseLeave() {
  showMouseIndicator.value = false;
}

let timer = null;

onMounted(() => {
  loadConfig();
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
  height: 100%;
  background: url("/config/background.jpg") no-repeat center center fixed;
  background-size: cover;
  padding: clamp(24px, 4vw, 56px);
  box-sizing: border-box;
  isolation: isolate;
  position: relative;
  overflow: hidden;
}

.game-calendar::before {
  content: "";
  position: fixed;
  inset: 0;
  background:
    linear-gradient(
      120deg,
      rgba(9, 17, 30, 0.76),
      rgba(18, 28, 43, 0.35) 48%,
      rgba(8, 15, 27, 0.72)
    ),
    linear-gradient(180deg, rgba(5, 11, 20, 0.08), rgba(5, 11, 20, 0.66));
  z-index: -1;
}

.page-shell {
  width: 100%;
  max-width: 1500px;
  height: 100%;
  min-height: 0;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  flex: 0 0 auto;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
}

.title-group {
  color: #f8fafc;
}

.eyebrow,
.toolbar-kicker {
  display: block;
  color: #9aadc3;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.18em;
}

.title-group h1 {
  margin-top: 7px;
  font-size: clamp(30px, 3.4vw, 46px);
  line-height: 1.08;
  letter-spacing: -0.045em;
}

.title-group p {
  margin-top: 10px;
  color: rgba(226, 232, 240, 0.76);
  font-size: 14px;
}

.game-type-switcher {
  display: flex;
  gap: 10px;
  padding: 6px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 18px;
  background: rgba(9, 17, 29, 0.62);
  box-shadow: 0 16px 40px rgba(2, 8, 20, 0.24);
  backdrop-filter: blur(18px);
}

.game-type-btn {
  position: relative;
  width: 156px;
  height: 64px;
  padding: 0;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 13px;
  background: #111c2b;
  color: rgba(255, 255, 255, 0.78);
  cursor: pointer;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease;
}

.game-cover {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: saturate(0.65) brightness(0.58);
  transition:
    filter 180ms ease,
    transform 300ms ease;
}

.game-type-btn::after {
  content: "";
  position: absolute;
  inset: 0;
}

.game-name {
  position: absolute;
  left: 14px;
  bottom: 12px;
  z-index: 1;
  font-size: 14px;
  font-weight: 800;
}

.selected-dot {
  position: absolute;
  right: 12px;
  top: 12px;
  z-index: 1;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: transparent;
}

.game-type-btn:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.28);
}

.game-type-btn:hover .game-cover,
.game-type-btn.active .game-cover {
  filter: saturate(1) brightness(0.76);
  transform: scale(1.04);
}

.game-type-btn.active {
  border-color: rgba(255, 255, 255, 0.7);
  color: #fff;
  box-shadow: 0 8px 26px rgba(0, 0, 0, 0.28);
}

.game-type-btn.active .selected-dot {
  background: #ff667d;
  box-shadow: 0 0 0 4px rgba(255, 102, 125, 0.18);
}

.calendar-container {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 24px;
  background: rgba(9, 18, 31, 0.1);
  box-shadow:
    0 30px 80px rgba(1, 7, 18, 0.42),
    inset 0 1px rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(14px) saturate(1.08);
}

.calendar-toolbar {
  flex: 0 0 auto;
  min-height: 92px;
  padding: 20px 24px;
  display: grid;
  grid-template-columns: minmax(190px, 1fr) auto minmax(320px, 1fr);
  align-items: center;
  gap: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}

.date-range {
  margin-top: 6px;
  color: #f5f8fc;
  font-size: 18px;
  font-weight: 750;
  letter-spacing: -0.01em;
}

.calendar-summary {
  display: flex;
  align-items: center;
  gap: 22px;
}

.summary-item {
  display: flex;
  align-items: baseline;
  gap: 7px;
}

.summary-item strong {
  color: #fff;
  font-size: 24px;
  line-height: 1;
}

.summary-item span,
.legend span {
  color: #91a3b8;
  font-size: 12px;
}

.summary-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.1);
}

.legend {
  display: flex;
  justify-content: flex-end;
  gap: 20px;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  white-space: nowrap;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 3px;
}

.legend-dot.banner {
  background: #ff7188;
}
.legend-dot.event {
  background: #f1bd62;
}
.legend-dot.bonus {
  background: #7893b2;
}

.calendar-scroll {
  flex: 1 1 auto;
  height: auto;
  min-height: 0;
  overflow: hidden;
}

.calendar-content {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  padding: 20px 24px 24px;
  display: grid;
  grid-template-rows: auto minmax(200px, 1fr);
  gap: 14px;
}

.activities-area {
  height: auto;
  position: relative;
  margin-top: 0;
  padding: 4px 0 14px;
  overflow-x: clip;
  overflow-y: auto;
  min-height: 200px;
  max-height: none;
  background: repeating-linear-gradient(
    90deg,
    transparent 0,
    transparent calc(7.142857% - 1px),
    rgba(255, 255, 255, 0.035) calc(7.142857% - 1px),
    rgba(255, 255, 255, 0.035) 7.142857%
  );
}

.activities-area::-webkit-scrollbar {
  width: 6px;
}

.activities-area::-webkit-scrollbar-track {
  background: transparent;
}

.activities-area::-webkit-scrollbar-thumb {
  background: #40536b;
  border-radius: 3px;
}

.activity-row.red-row {
  position: relative;
  height: 50px;
  margin-bottom: 10px;
}

.red-row .activity-bar {
  position: absolute;
  top: 0;
  margin-bottom: 0;
}

.mouse-indicator {
  position: absolute;
  top: 20px;
  bottom: auto;
  height: calc(100% - 44px);
  width: 1px;
  z-index: 10;
  transform: translateX(-50%);
  pointer-events: none;
  overflow: visible;
  opacity: 0;
  visibility: hidden;
  transition: opacity 80ms ease;
}

.mouse-indicator.visible {
  opacity: 1;
  visibility: visible;
}

.mouse-indicator-label {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  background: #eef4fb;
  box-shadow: 0 5px 18px rgba(0, 0, 0, 0.22);
  color: #142033;
  font-size: 12px;
  font-weight: 750;
  padding: 5px 9px;
  border-radius: 7px;
  white-space: nowrap;
}

.mouse-indicator-line {
  position: absolute;
  top: 27px;
  bottom: 0;
  left: 50%;
  width: 1px;
  background: rgba(226, 232, 240, 0.48);
}

.loading-state {
  flex: 1;
  display: grid;
  place-items: center;
  min-height: 420px;
  color: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 24px;
  background: rgba(11, 20, 33, 0.74);
  backdrop-filter: blur(20px);
}

@media (max-width: 1050px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .calendar-toolbar {
    grid-template-columns: 1fr auto;
  }

  .legend {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .game-calendar {
    padding: 18px 14px;
  }
  .page-shell {
    gap: 16px;
  }
  .title-group p {
    display: none;
  }
  .game-type-switcher {
    width: 100%;
  }
  .game-type-btn {
    flex: 1;
    width: auto;
  }
  .calendar-container {
    border-radius: 18px;
  }
  .calendar-toolbar {
    padding: 18px;
    gap: 16px;
  }
  .calendar-summary {
    gap: 12px;
  }
  .summary-item {
    display: block;
  }
  .summary-item span {
    display: block;
    margin-top: 4px;
  }
  .legend {
    gap: 12px;
    overflow-x: auto;
  }
}
</style>
