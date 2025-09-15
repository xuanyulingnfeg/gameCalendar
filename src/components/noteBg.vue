<template>
  <div class="noteBg">
    <div class="bgContent">
      <div>
        <div class="quarterCircle" :style="bgColorStyle(2, 'left top')"></div>
        <div class="cylinder" :style="bgColorStyle(1)"></div>
        <div class="quarterCircle" :style="bgColorStyle(2, 'right top')"></div>
      </div>
      <div>
        <div class="bgCenterLeft" :style="bgColorStyle(1)"></div>
        <div class="bgCenterCenter" :style="bgColorStyle(1)"></div>
        <div class="bgCenterRight" :style="bgColorStyle(1)"></div>
      </div>
      <div>
        <div
          class="quarterCircle"
          :style="bgColorStyle(2, 'left bottom')"
        ></div>
        <div class="cylinder" :style="bgColorStyle(1)"></div>
        <div
          class="quarterCircle"
          :style="bgColorStyle(2, 'right bottom')"
        ></div>
      </div>
    </div>
    <div class="noteContent">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps(["color"]);

function bgColorStyle(type: number = 1, direction?: string) {
  switch (type) {
    case 1:
      return `background-color: ${props.color || "rgba(135, 173, 255, 0.5)"}`;
    case 2:
      return `background-image: radial-gradient(
          circle at ${direction},
          transparent 0,
          transparent 40px,
          ${props.color || "rgba(135, 173, 255, 0.5)"} 20px
        );`;
  }
}
</script>

<style lang="scss" scoped>
.noteBg {
  width: 100%;
  height: 100%;
  position: relative;

  .bgContent {
    width: 100%;
    height: 100%;

    & > div {
      display: flex;
      height: calc(100% - 100px);

      &:first-child,
      &:last-child {
        width: 100%;
        height: 50px;

        & > div {
          height: 100%;
        }

        .quarterCircle {
          width: 50px;
        }

        .cylinder {
          flex: 1;
        }
      }

      .bgCenterLeft,
      .bgCenterRight {
        width: 50px;
      }

      .bgCenterCenter {
        flex: 1;
      }
    }
  }

  .noteContent {
    display: flex;
    top: 0;
    left: 0;
    position: absolute;
    width: 100%;
    height: 100%;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
  }
}
</style>
