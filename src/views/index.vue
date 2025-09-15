<template>
  <div class="pageContent">
    <div class="title">{{ dayjs().format("M") }}月大事件</div>
    <div class="contentWrap">
      <!-- 日曆模塊 -->
      <div class="contentLeft">
        <noteBg class="calendarBg" color="rgba(135, 173, 255, 0.5)">
          <div class="calendarContent">
            <div class="calendarTitle calendarRow">
              <!-- 週一到週日 -->
              <div class="calendarDayItem">週一</div>
              <div class="calendarDayItem">週二</div>
              <div class="calendarDayItem">週三</div>
              <div class="calendarDayItem">週四</div>
              <div class="calendarDayItem">週五</div>
              <div class="calendarDayItem">週六</div>
              <div class="calendarDayItem">週日</div>
            </div>
            <div class="calendarDays calendarRow">
              <template v-for="dayItem in dayList">
                <div
                  class="calendarDayItem"
                  :class="[{ isPre: dayItem.isPre, isNext: dayItem.isNext }]"
                >
                  <div class="bgs">
                    <div
                      class="bgItem"
                      v-for="(bgItem, bgIndex) in dayItem.bgImgs"
                      :style="setBgImg(bgItem, bgIndex, dayItem.bgImgs.length)"
                    ></div>
                  </div>
                  <div
                    class="dayNum"
                    :class="[
                      {
                        active:
                          dayjs(dayItem.day).format('MMDD') ==
                          dayjs().format('MMDD'),
                      },
                    ]"
                  >
                    {{ dayjs(dayItem.day).format("DD") }}
                  </div>
                  <div class="describe" v-if="dayItem.events.length">
                    <div class="events" v-for="eventItem in dayItem.events">
                      ※{{ eventItem }}
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </noteBg>
      </div>

      <!-- 近期信息 -->
      <div class="contentRight">
        <noteBg color="rgba(255, 255, 255, 0.5)"
          ><div class="recentlyInfo">
            <div class="gameChoose">
              <div
                class="gameItem"
                :class="[{ active: showGameList.includes(gameItem.key) }]"
                v-for="gameItem in gameList"
                :key="gameItem.key"
                @click="chooseGame(gameItem.key)"
              >
                <div class="gameIcon"></div>
                <div class="gameName">{{ gameItem.name }}</div>
              </div>
            </div>
          </div></noteBg
        >
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
type jsonType = {
  [key: string]: any;
};

import { ref, onMounted } from "vue";
import dayjs from "dayjs";

import noteBg from "../components/noteBg.vue";

const eventsData: jsonType = {};

const dayList: any = ref([]);

const gameList: any = ref([
  {
    name: "绝区零",
    key: "zzz",
    bgImg: "/static/images/zzz.png",
  },
  {
    name: "鸣潮",
    key: "mc",
    bgImg: "/static/images/mc.png",
  },
]);

const showGameList: any = ref(["zzz", "mc"]);

onMounted(() => {
  let path =
    import.meta.env.VITE_ENV == "development"
      ? "../static/config.json"
      : "./static/config.json";
  importFile(path).then((res) => {
    eventsData.value = res;
    creatDayList();
  });
});

async function importFile(path: string) {
  const data = await import(path);
  return data;
}

function setBgImg(bgSrc: string, bgIndex: number, length: number) {
  let style = "display: none";
  if (length === 1) {
    style = `background-image: url('${bgSrc}')`;
  } else if (length === 2) {
    if (bgIndex === 0) {
      style = `background-image: url('${bgSrc}'); left: -25%`;
    } else {
      style = `background-image: url('${bgSrc}');clip-path: polygon(10% 0, 100% 0, 100% 100%, 40% 100%);right: -25%`;
    }
  } else if (length === 3) {
    if (bgIndex === 0) {
      style = `background-image: url('${bgSrc}'); left: -33%; z-index: 2`;
    } else if (bgIndex === 1) {
      style = `background-image: url('${bgSrc}');clip-path: polygon(20% 0, 80% 0, 65% 100%, 35% 100%); z-index: 3`;
    } else {
      style = `background-image: url('${bgSrc}');right: -33%; z-index: 1`;
    }
  }
  return style;
}

// 生成當前頁面數據
function creatDayList() {
  let monthFirstDay = dayjs().startOf("month").format("YYYY-MM-DD"); // 當前月份第一天
  let monthLastDayNunber = Number(dayjs().endOf("month").format("D")); // 當前月份天數
  let firstDayWeek = Number(dayjs().startOf("month").day());
  let lastDayWeek = Number(dayjs().endOf("month").day());

  let list = [];

  // 補充月份前面日期
  firstDayWeek = firstDayWeek == 0 ? 7 : firstDayWeek;
  let preLen = firstDayWeek == 1 ? 7 : firstDayWeek - 1;
  for (let i = preLen; i != 0; i--) {
    let day = dayjs(monthFirstDay).subtract(i, "day").format("YYYY-MM-DD");
    list.push({
      day: day,
      isPre: true,
      isNext: false,
      events: [] as any[],
      bgImgs: [] as any[],
    });
  }

  // 遍歷當前月份日期
  for (let i = 1; i <= monthLastDayNunber; i++) {
    list.push({
      day: dayjs(monthFirstDay)
        .add(i - 1, "day")
        .format("YYYY-MM-DD"),
      isPre: false,
      isNext: false,
      events: [] as any[],
      bgImgs: [] as any[],
    });
  }

  // 補充月份後面日期
  lastDayWeek = lastDayWeek == 0 ? 7 : lastDayWeek;
  let nextLen = lastDayWeek == 7 ? 7 : 7 - lastDayWeek;
  for (let i = 1; i <= nextLen; i++) {
    let day = dayjs().endOf("month").add(i, "day").format("YYYY-MM-DD");
    list.push({
      day: day,
      isNext: true,
      isPre: false,
      events: [] as any[],
      bgImgs: [] as any[],
    });
  }

  // 設置日期內事件、背景
  // 遍歷當前顯示日期
  list.forEach((dayItem) => {
    // 遍歷遊戲
    showGameList.value.forEach((gameKey: string) => {
      let gameItem = gameList.value.find((item: any) => item.key == gameKey);
      // 當前遊戲下的存在日期事件
      let eventItem: any = eventsData.value[gameKey][dayItem.day];
      if (!!eventItem) {
        dayItem.events.push(...eventItem.events);
        dayItem.bgImgs.push(eventItem.img || gameItem.bgImg);
      }
    });
  });

  dayList.value = list;
}

function chooseGame(key: string) {
  if (showGameList.value.includes(key)) {
    showGameList.value = showGameList.value.filter(
      (item: string) => item != key
    );
  } else {
    showGameList.value.push(key);
  }

  creatDayList();
}
</script>

<style scoped lang="scss">
.pageContent {
  width: 100vw;
  height: 100vh;
  background-image: url("/static/images/bg.jpg");
  background-size: cover;
  color: #ffffff;

  .title {
    font-family: "biantaoti";
    font-weight: bold;
    font-size: 80px;
    letter-spacing: 24px;
    text-shadow: 0 0 20px #000;
  }

  .contentWrap {
    height: calc(100% - 180px);
    display: flex;
    padding: 30px 60px;

    .contentLeft {
      flex: 1;
      min-width: 1200px;
      display: flex;
      align-items: center;

      .calendarBg {
        .calendarContent {
          width: 100%;
          margin: 0 50px;
          border: 1px solid #045a85;

          .calendarRow {
            display: flex;
            flex-wrap: wrap;

            .calendarDayItem {
              width: calc(100% / 7);
              box-sizing: border-box;
              overflow: hidden;
            }

            &.calendarTitle .calendarDayItem {
              text-align: center;
              font-size: 40px;
              font-weight: 600;
              -webkit-text-stroke: 1px #045a85;
              border: 1px solid #1160a5;
            }

            &.calendarDays .calendarDayItem {
              font-family: "biantaoti";
              position: relative;
              font-weight: bolder;
              font-size: 30px;
              height: 100px;
              border: 1px solid #1160a5;

              .dayNum {
                position: absolute;
                width: max-content;
                bottom: 0px;
                right: 10px;
                -webkit-text-stroke: 2px black;

                // 外发光，红色
                &.active {
                  -webkit-text-stroke: 2px red;
                }
              }

              .describe {
                text-align: left;
                position: absolute;
                width: 100%;
                top: 0px;
                left: 5px;
                font-size: 18px;
                line-height: 25px;
                -webkit-text-stroke: 1px black;
              }

              .bgs {
                width: 100%;
                height: 100%;
                position: relative;

                .bgItem {
                  width: 100%;
                  height: 100%;
                  position: absolute;
                  background-size: cover;
                  background-position: center;
                  background-repeat: no-repeat, no-repeat;
                }
              }

              &.isPre,
              &.isNext {
                .dayNum {
                  opacity: 0.5;
                }
              }
            }
          }
        }
      }
    }

    .contentRight {
      min-width: 460px;
      width: 25%;
      display: flex;
      align-items: center;

      .recentlyInfo {
        width: 100%;
        height: 662px;
        margin: 0 50px;
        background-color: #2b2224;

        .gameChoose {
          display: flex;
          justify-content: center;
          padding: 20px 0;

          .gameItem {
            width: 100px;
            padding: 10px;
            margin: 0 10px;
            border-radius: 10px;
            border: 2px solid rgba(255, 255, 255, 0.5);
            cursor: pointer;

            &.active {
              border-color: #1160a5;
            }
          }
        }
      }
    }
  }
}
</style>
