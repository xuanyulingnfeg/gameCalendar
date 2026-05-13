// 游戏类型列表
export const gameTypes = [
  { key: "zzz", name: "绝区零", bgImage: "" },
  { key: "mc", name: "鸣潮", bgImage: "" },
];

// 各游戏类型的配置和活动
export const gameData = {
  zzz: {
    calendarConfig: {
      startDate: "2026/05/07",
      endDate: "2026/06/17",
    },
    activities: [
      {
        id: 1,
        name: "普罗米娅/卢西娅 - 限时频段",
        startTime: "2026-05-07 10",
        endTime: "2026-05-28 04",
        type: "red",
        icons: 2,
        hasDollarSign: true,
        hasCharIcon: true,
        charIconLeft: "",
        charIconRight: "",
      },
      {
        id: 2,
        name: "星徽·比利/奥菲丝&「鬼火」- 限时频段",
        startTime: "2026-05-28 04",
        endTime: "2026-06-17 04",
        type: "red",
        icons: 2,
        hasDollarSign: true,
        hasCharIcon: true,
        charIconLeft: "",
        charIconRight: "",
      },
      {
        id: 3,
        name: "游乐岛拯救计划",
        startTime: "2026-05-07 10",
        endTime: "2026-06-02 04",
        type: "orange",
        icons: 4,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        id: 4,
        name: "极限裁决试炼",
        startTime: "2026-05-14 10",
        endTime: "2026-05-28 04",
        type: "orange",
        icons: 2,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        id: 5,
        name: "「灵魂」画手侧写簿",
        startTime: "2026-05-21 10",
        endTime: "2026-06-02 04",
        type: "gray",
        icons: 3,
        hasDollarSign: false,
        hasCharIcon: false,
      },
    ],
  },
  mc: {
    calendarConfig: {
      startDate: "2026/05/07",
      endDate: "2026/06/17",
    },
    activities: [],
  },
};
