<template>
  <div
    class="activity-bar"
    :class="'type-' + activity.type"
    :style="barStyle"
    @mouseenter="showTooltip = true"
    @mousemove="onBarMouseMove"
    @mouseleave="showTooltip = false"
  >
    <!-- 悬浮提示 -->
    <div
      class="activity-tooltip"
      :class="{ 'tooltip-left': tooltipFlipped }"
      v-if="showTooltip"
      :style="{ left: tooltipX + 'px' }"
    >
      {{ tooltipText }}
    </div>

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
});

const showTooltip = ref(false);
const tooltipX = ref(0);
const tooltipFlipped = ref(false);

function onBarMouseMove(e) {
  const bar = e.currentTarget;
  const barRect = bar.getBoundingClientRect();
  const x = e.clientX - barRect.left;
  tooltipX.value = x;

  // 检查提示是否会超出活动区域右侧（估算提示宽度约180px）
  const tooltipWidth = 180;
  const rightSpace = barRect.right - e.clientX;
  tooltipFlipped.value = rightSpace < tooltipWidth;
}

const tooltipText = computed(() => {
  const now = new Date();
  const actStart = parseTime(props.activity.startTime, false);
  const actEnd = parseTime(props.activity.endTime, true);

  // 计算自然日之差（只算日期部分）
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  if (now < actStart) {
    const startDay = new Date(actStart.getFullYear(), actStart.getMonth(), actStart.getDate());
    const diffDays = Math.ceil((startDay - todayStart) / (1000 * 60 * 60 * 24));
    return `距离活动开始还有：${diffDays}天`;
  } else {
    const endDay = new Date(actEnd.getFullYear(), actEnd.getMonth(), actEnd.getDate());
    const diffDays = Math.ceil((endDay - todayStart) / (1000 * 60 * 60 * 24));
    return `距离活动结束还有：${diffDays}天`;
  }
});

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
  height: 54px;
  border-radius: 27px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  margin-bottom: 14px;
  box-sizing: border-box;
  /* overflow: hidden; */
}

.activity-tooltip {
  position: absolute;
  top: 100%;
  margin-top: 4px;
  background: rgba(0, 0, 0, 0.85);
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  padding: 4px 10px;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 20;
  pointer-events: none;
}

.activity-tooltip.tooltip-left {
  transform: translateX(-100%);
}

.activity-bar.type-red {
  padding: 0 4px;
  background: linear-gradient(135deg, #ff4500, #ff8c00);
  box-shadow: 0 2px 8px rgba(255, 69, 0, 0.3);
}

.activity-bar.type-orange {
  background: linear-gradient(135deg, #ffa500, #ffcc00);
  box-shadow: 0 2px 8px rgba(255, 165, 0, 0.3);
}

.activity-bar.type-gray {
  background: linear-gradient(135deg, #666, #888);
  box-shadow: 0 2px 8px rgba(100, 100, 100, 0.3);
}

.activity-bar.type-green {
  background: linear-gradient(135deg, #008000, #00ff00);
  box-shadow: 0 2px 8px rgba(100, 100, 100, 0.3);
}

.activity-bar::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background:
    repeating-linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.1) 0px,
      rgba(255, 255, 255, 0.1) 1px,
      transparent 1px,
      transparent 5px
    ),
    repeating-linear-gradient(
      135deg,
      rgba(255, 255, 255, 0.1) 0px,
      rgba(255, 255, 255, 0.1) 1px,
      transparent 1px,
      transparent 5px
    );
  -webkit-mask-image: linear-gradient(to top, black 0%, transparent 50%);
  mask-image: linear-gradient(to top, black 0%, transparent 70%);
  pointer-events: none;
  border-radius: inherit;
}

.dollar-sign {
  position: absolute;
  top: 4px;
  left: 10px;
  /* background: #ffcc00; */
  color: #333;
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
  color: black;
}

.char-icon {
  width: 112px;
  height: 45px;
  border-radius: 21px;
  border: 3px solid black;
  flex-shrink: 0;
  margin-right: 10px;
  position: relative;
  overflow: hidden;
  background: #222;
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
  font-size: 18px;
  font-weight: 900;
  line-height: 1;
  color: black;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
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
