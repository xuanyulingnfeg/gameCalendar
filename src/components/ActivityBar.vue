<template>
  <div class="activity-bar" :class="'type-' + activity.type" :style="barStyle">
    <!-- $ 标记 -->
    <div class="dollar-sign" v-if="activity.hasDollarSign">$</div>

    <!-- 左侧角色图标 -->
    <div class="char-icon" v-if="activity.hasCharIcon">
      <div class="char-icon-inner"></div>
    </div>

    <!-- 活动名称 -->
    <div class="activity-name">{{ activity.name }}</div>

    <!-- 右侧图标区域 -->
    <div class="right-icons">
      <div class="icon-box" v-for="n in activity.icons" :key="n"></div>
      <div class="arrow-btn">
        <span>›</span>
      </div>
    </div>
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
  padding: 0 14px;
  margin-bottom: 14px;
  box-sizing: border-box;
  overflow: hidden;
}

.activity-bar.type-red {
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

.dollar-sign {
  position: absolute;
  top: 4px;
  left: 10px;
  background: #ffcc00;
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

.char-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 255, 255, 0.4);
  flex-shrink: 0;
  margin-right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.char-icon-inner {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #555, #999);
}

.activity-name {
  flex: 1;
  font-size: 14px;
  font-weight: bold;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.type-orange .activity-name {
  color: #333;
  text-shadow: none;
}

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
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid rgba(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
}
</style>
