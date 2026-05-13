<template>
  <div class="activity-bar" :class="'type-' + activity.type" :style="barStyle">
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
import { computed } from "vue";

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

  const marginLeft = (startHoursOffset / totalHours) * 100;
  const width = (durationHours / totalHours) * 100;

  if (props.absolute) {
    return {
      left: marginLeft + "%",
      width: width + "%",
    };
  }
  return {
    marginLeft: marginLeft + "%",
    width: width + "%",
  };
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
