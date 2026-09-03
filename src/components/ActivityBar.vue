<template>
  <div
    class="activity-bar"
    :class="[
      'type-' + activity.type,
      { 'is-completed': completed },
    ]"
    :style="barStyle"
    @mouseenter="showTooltip = true"
    @mousemove="onBarMouseMove"
    @mouseleave="showTooltip = false"
  >
    <!-- 悬浮提示 -->
    <Teleport to="body">
      <div
        class="activity-tooltip"
        :class="{ 'tooltip-left': tooltipFlipped }"
        v-if="showTooltip"
        :style="{ left: tooltipFixedX + 'px', top: tooltipFixedY + 'px' }"
      >
        <div class="tooltip-heading">
          <span class="tooltip-status" :class="`status-${activityStatus.key}`">
            <i></i>{{ activityStatus.label }}
          </span>
          <span class="tooltip-remaining">{{ activityStatus.description }}</span>
        </div>
        <div class="tooltip-divider"></div>
        <dl class="tooltip-times">
          <div>
            <dt>开始</dt>
            <dd>{{ formattedStartTime }}</dd>
          </div>
          <div>
            <dt>结束</dt>
            <dd>{{ formattedEndTime }}</dd>
          </div>
        </dl>
      </div>
    </Teleport>

    <!-- $ 标记 -->
    <div class="dollar-sign" v-if="activity.hasDollarSign">
      <img src="../assets/starIcon.png" />
      <span class="dollar-sign-text">S</span>
    </div>

    <!-- 角色图标区域 -->
    <div
      class="char-icon"
      v-if="
        activity.hasCharIcon &&
        activity.charIcons &&
        activity.charIcons.length > 0
      "
      :style="{ width: activity.charIcons.length * 56 + 'px' }"
    >
      <div
        v-for="(icon, idx) in activity.charIcons"
        :key="idx"
        class="char-segment"
        :style="getSegmentStyle(idx, activity.charIcons.length, icon)"
      ></div>
    </div>

    <!-- 活动名称 -->
    <div class="activity-name">{{ activity.name }}</div>

    <label
      v-if="completable"
      class="completion-toggle"
      :title="completed ? '标记为未完成' : '标记为已完成'"
      @click.stop
    >
      <input
        type="checkbox"
        :checked="completed"
        :aria-label="`${activity.name}：${completed ? '已完成' : '未完成'}`"
        @change="$emit('toggle-completed')"
      />
      <span class="checkmark" aria-hidden="true"></span>
    </label>

    <!-- 右侧图标区域 -->
    <!-- <div class="right-icons">
      <div class="icon-box" v-for="n in activity.icons" :key="n"></div>
      <div class="arrow-btn">
        <span>›</span>
      </div>
    </div> -->
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  activity: {
    type: Object,
    required: true,
  },
  calendarStartDate: {
    type: String,
    required: true,
  },
  calendarEndDate: {
    type: String,
    required: true,
  },
  totalDays: {
    type: Number,
    required: true,
  },
  absolute: {
    type: Boolean,
    default: false,
  },
  completable: {
    type: Boolean,
    default: false,
  },
  completed: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["toggle-completed"]);

const showTooltip = ref(false);
const tooltipFixedX = ref(0);
const tooltipFixedY = ref(0);
const tooltipFlipped = ref(false);

function onBarMouseMove(e) {
  const bar = e.currentTarget;
  const barRect = bar.getBoundingClientRect();

  // 使用视口坐标定位（fixed）
  tooltipFixedX.value = e.clientX;
  tooltipFixedY.value = barRect.bottom + 4;

  // 检查提示是否会超出活动区域右侧
  const activitiesArea = bar.closest(".activities-area");
  const areaRight = activitiesArea
    ? activitiesArea.getBoundingClientRect().right
    : window.innerWidth;
  const tooltipWidth = 280;
  const rightSpace = areaRight - e.clientX;
  tooltipFlipped.value = rightSpace < tooltipWidth;
}

const activityStatus = computed(() => {
  const now = new Date();
  const actStart = parseTime(props.activity.startTime, false);
  const actEnd = parseTime(props.activity.endTime, true);

  if (props.completed) {
    return { key: "completed", label: "已完成", description: "已标记完成" };
  }

  if (now >= actEnd) {
    return { key: "ended", label: "已结束", description: "活动已经结束" };
  }

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  if (now < actStart) {
    const startDay = new Date(
      actStart.getFullYear(),
      actStart.getMonth(),
      actStart.getDate(),
    );
    const diffDays = Math.ceil((startDay - todayStart) / (1000 * 60 * 60 * 24));
    return {
      key: "upcoming",
      label: "未开始",
      description: `${diffDays} 天后开始`,
    };
  } else {
    const endDay = new Date(
      actEnd.getFullYear(),
      actEnd.getMonth(),
      actEnd.getDate(),
    );
    const diffDays = Math.ceil((endDay - todayStart) / (1000 * 60 * 60 * 24));
    return {
      key: "ongoing",
      label: "进行中",
      description: `剩余 ${diffDays} 天`,
    };
  }
});

function formatDisplayTime(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  return `${year}/${month}/${day} ${hour}:00`;
}

const formattedStartTime = computed(() =>
  formatDisplayTime(parseTime(props.activity.startTime, false)),
);

const formattedEndTime = computed(() =>
  formatDisplayTime(parseTime(props.activity.endTime, true)),
);

function parseTime(timeStr, isEnd = false) {
  // timeStr 格式: "2026-05-07 10" 或 "2026-05-07"
  const parts = timeStr.split(" ");
  const [year, month, day] = parts[0].split("-");
  let hour = 0;
  if (parts.length > 1) {
    hour = parseInt(parts[1]);
  } else {
    // 无小时部分：开始默认00，结束默认24
    hour = isEnd ? 24 : 0;
  }
  return new Date(year, month - 1, day, hour, 0, 0, 0);
}

function getSegmentStyle(index, total, iconUrl) {
  const style = {
    position: "absolute",
    top: "0",
    bottom: "0",
    backgroundSize: "cover",
    backgroundPosition: "center",
  };

  if (iconUrl) {
    style.backgroundImage = `url(${iconUrl})`;
  }

  if (total === 1) {
    style.left = "0";
    style.width = "100%";
  } else {
    // 每个区域占据自己的位置，background-position:center 在段内居中
    const segWidth = 100 / total;
    style.left = index * segWidth + "%";
    style.width = segWidth + "%";

    // 斜线裁切，用段内坐标系（百分比相对于段自身宽度）
    const skew = 18;
    if (index === 0) {
      style.clipPath = `polygon(0 0, ${100 + skew}% 0, ${100 - skew}% 100%, 0 100%)`;
    } else if (index === total - 1) {
      style.clipPath = `polygon(${-skew}% 0, 100% 0, 100% 100%, ${skew}% 100%)`;
    } else {
      style.clipPath = `polygon(${-skew}% 0, ${100 + skew}% 0, ${100 - skew}% 100%, ${skew}% 100%)`;
    }
  }

  return style;
}

const barStyle = computed(() => {
  const calStart = new Date(props.calendarStartDate);
  calStart.setHours(0, 0, 0, 0);
  const calEnd = new Date(props.calendarEndDate);
  calEnd.setHours(23, 59, 59, 999);

  const totalHours = props.totalDays * 24;

  const actStart = parseTime(props.activity.startTime, false);
  const actEnd = parseTime(props.activity.endTime, true);

  const startHoursOffset = (actStart - calStart) / (1000 * 60 * 60);
  const durationHours = (actEnd - actStart) / (1000 * 60 * 60);

  let left = (startHoursOffset / totalHours) * 100;
  let width = (durationHours / totalHours) * 100;

  // 裁剪到可视范围内
  let clippedLeft = false;
  let clippedRight = false;
  if (left < 0) {
    width += left;
    left = 0;
    clippedLeft = true;
  }
  if (left + width > 100) {
    width = 100 - left;
    clippedRight = true;
  }

  const style = {};
  if (props.absolute) {
    style.left = left + "%";
    style.width = width + "%";
  } else {
    style.marginLeft = left + "%";
    style.width = width + "%";
  }

  // 被裁剪侧去掉圆弧
  if (clippedLeft && clippedRight) {
    style.borderRadius = "0";
  } else if (clippedLeft) {
    style.borderTopLeftRadius = "0";
    style.borderBottomLeftRadius = "0";
  } else if (clippedRight) {
    style.borderTopRightRadius = "0";
    style.borderBottomRightRadius = "0";
  }

  return style;
});
</script>

<style scoped>
.activity-bar {
  position: relative;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  margin-bottom: 10px;
  box-sizing: border-box;
  border: 1px solid rgba(255, 255, 255, 0.12);
  container-type: inline-size;
  transition: filter 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.activity-bar:hover {
  z-index: 5;
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.activity-tooltip {
  position: fixed;
  margin-top: 0;
  background: #f4f7fb;
  box-shadow: 0 10px 28px rgba(2, 8, 20, 0.34);
  color: #182437;
  width: 272px;
  padding: 12px 14px;
  border: 1px solid rgba(19, 34, 53, 0.1);
  border-radius: 12px;
  z-index: 100;
  pointer-events: none;
}

.activity-tooltip.tooltip-left {
  transform: translateX(-100%);
}

.tooltip-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tooltip-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #22324a;
  font-size: 12px;
  font-weight: 800;
}

.tooltip-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #7d8da2;
}

.tooltip-status.status-ongoing i { background: #e39c3f; }
.tooltip-status.status-upcoming i { background: #668dbb; }
.tooltip-status.status-completed i { background: #698578; }
.tooltip-status.status-ended i { background: #8993a0; }

.tooltip-remaining {
  color: #65758a;
  font-size: 11px;
  font-weight: 650;
}

.tooltip-divider {
  height: 1px;
  margin: 10px 0;
  background: #e2e8f0;
}

.tooltip-times {
  display: grid;
  gap: 7px;
  margin: 0;
}

.tooltip-times div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.tooltip-times dt {
  color: #8a99ab;
  font-size: 11px;
}

.tooltip-times dd {
  margin: 0;
  color: #26374f;
  font-size: 11px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}

.activity-bar.type-red {
  padding: 0 10px 0 5px;
  background: linear-gradient(105deg, rgba(194, 66, 91, 0.94), rgba(231, 98, 117, 0.9));
  box-shadow: 0 7px 20px rgba(131, 32, 54, 0.2);
}

.activity-bar.type-orange {
  background: linear-gradient(105deg, rgba(178, 119, 50, 0.94), rgba(218, 166, 84, 0.9));
  box-shadow: 0 7px 20px rgba(106, 69, 21, 0.18);
}

.activity-bar.type-gray {
  background: linear-gradient(105deg, rgba(72, 91, 115, 0.94), rgba(91, 115, 143, 0.9));
  box-shadow: 0 7px 20px rgba(7, 17, 31, 0.2);
}

.activity-bar.type-green {
  background: linear-gradient(105deg, #347d70, #51a18f);
  box-shadow: 0 7px 20px rgba(20, 78, 67, 0.2);
}

.activity-bar::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    linear-gradient(180deg, rgba(255,255,255,.13), transparent 45%),
    linear-gradient(90deg, rgba(255,255,255,.07), transparent 32%);
  pointer-events: none;
  border-radius: inherit;
}

.dollar-sign {
  position: absolute;
  top: 4px;
  left: 10px;
  /* background: #ffcc00; */
  color: #142033;
  font-weight: bold;
  font-size: 11px;
  width: 18px;
  height: 18px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}

.dollar-sign img {
  width: 30px;
  position: relative;
  left: -6px;
  top: -6px;
}

.dollar-sign-text {
  position: absolute;
  font-size: 20px;
  top: -11.5px;
  left: -3px;
  font-weight: 900;
  font-style: italic;
  color: #182033;
}

.activity-bar.is-completed {
  background: linear-gradient(105deg, rgba(73, 82, 96, 0.9), rgba(94, 105, 120, 0.84));
  border-color: rgba(255, 255, 255, 0.09);
  box-shadow: 0 5px 16px rgba(3, 9, 18, 0.16);
}

.activity-bar.is-completed .activity-name {
  color: rgba(235, 240, 247, 0.68);
}

.char-icon {
  width: 112px;
  height: 40px;
  border-radius: 9px;
  border: 2px solid rgba(255, 255, 255, 0.74);
  flex-shrink: 0;
  margin-right: 10px;
  position: relative;
  overflow: hidden;
  background: #172437;
  box-shadow: 0 3px 10px rgba(2, 8, 20, 0.26);
}

.char-segment {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-size: cover;
}

.activity-name {
  flex: 1;
  font-size: 14px;
  font-weight: 750;
  line-height: 1;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.16);
}

@container (max-width: 230px) {
  .activity-name {
    font-size: 12px;
    letter-spacing: -0.01em;
  }
}

@container (max-width: 180px) {
  .activity-name {
    font-size: 10px;
    letter-spacing: -0.02em;
  }
}

@container (max-width: 130px) {
  .activity-name {
    font-size: 9px;
  }
}

@media (orientation: landscape) and (max-height: 600px) and (max-width: 1050px) {
  .activity-bar {
    height: 44px;
    margin-bottom: 8px;
    padding-right: 10px;
    padding-left: 10px;
    border-radius: 10px;
  }

  .activity-bar.type-red {
    padding-left: 4px;
  }

  .char-icon {
    height: 36px;
    margin-right: 8px;
    border-radius: 8px;
  }

  .completion-toggle {
    margin-left: 8px;
  }
}

.completion-toggle {
  width: 28px;
  height: 28px;
  margin-left: 12px;
  flex: 0 0 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 160ms ease;
}

.completion-toggle:hover {
  background: rgba(255, 255, 255, 0.1);
}

.completion-toggle input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.checkmark {
  position: relative;
  width: 19px;
  height: 19px;
  border: 1.5px solid rgba(255, 255, 255, 0.72);
  border-radius: 6px;
  background: rgba(8, 16, 28, 0.18);
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.06);
  transition: background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
}

.completion-toggle:hover .checkmark {
  border-color: #fff;
  transform: scale(1.05);
}

.completion-toggle input:focus-visible + .checkmark {
  outline: 2px solid rgba(255, 255, 255, 0.92);
  outline-offset: 3px;
}

.completion-toggle input:checked + .checkmark {
  border-color: #d8e0eb;
  background: #d8e0eb;
}

.completion-toggle input:checked + .checkmark::after {
  content: "";
  position: absolute;
  left: 6px;
  top: 3px;
  width: 4px;
  height: 8px;
  border: solid #344154;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

/* .type-orange .activity-name {
  color: #333;
  text-shadow: none;
} */

.right-icons {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  margin-left: 10px;
}

.icon-box {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.arrow-btn {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background-color: black;
  border: 4px solid #313131;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 34px;
  font-weight: bold;

  span {
    /* 文字颜色从上到下渐变 */
    background: linear-gradient(180deg, #fff, #333);
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
    position: relative;
    top: -4.5px;
    left: 1px;
  }
}
</style>
