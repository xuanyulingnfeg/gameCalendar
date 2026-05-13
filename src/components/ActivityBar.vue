<template>
  <div class="activity-bar" :class="'type-' + activity.type" :style="barStyle">
    <!-- $ 标记 -->
    <div class="dollar-sign" v-if="activity.hasDollarSign">
      <img src="../assets/starIcon.png" />
      <span class="dollar-sign-text">S</span>
    </div>

    <!-- 左侧角色图标 -->
    <div class="char-icon" v-if="activity.hasCharIcon">
      <div
        class="char-left"
        :style="{
          backgroundImage: activity.charIconLeft
            ? `url(${activity.charIconLeft})`
            : '',
        }"
      ></div>
      <div
        class="char-right"
        :style="{
          backgroundImage: activity.charIconRight
            ? `url(${activity.charIconRight})`
            : '',
        }"
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
  totalWeeks: {
    type: Number,
    default: 6,
  },
});

const barStyle = computed(() => {
  const startPercent =
    ((props.activity.startWeek - 1) / props.totalWeeks) * 100;
  const widthPercent =
    ((props.activity.endWeek - props.activity.startWeek + 1) /
      props.totalWeeks) *
    100;
  return {
    marginLeft: startPercent + "%",
    width: widthPercent + "%",
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

.char-left {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  clip-path: polygon(0 0, 60% 0, 40% 100%, 0 100%);
  background-color: #444;
  background-size: cover;
  background-position: center;
}

.char-right {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  clip-path: polygon(60% 0, 100% 0, 100% 100%, 40% 100%);
  background-color: #555;
  background-size: cover;
  background-position: center;
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
