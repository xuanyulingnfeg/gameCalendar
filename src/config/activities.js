// 游戏类型列表
export const gameTypes = [
  { key: "zzz", name: "绝区零", bgImage: "/zzz/bg.png" },
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
        name: "普罗米娅/卢西娅 - 限时频段",
        startTime: "2026-05-07 10",
        endTime: "2026-05-28 04",
        type: "red",
        icons: 2,
        hasDollarSign: true,
        hasCharIcon: true,
        charIconLeft: "/zzz/puluomiya.png",
        charIconRight: "/zzz/luxiya.png",
      },
      {
        name: "星徽·比利/奥菲丝&「鬼火」- 限时频段",
        startTime: "2026-05-28 04",
        endTime: "2026-06-16 18",
        type: "red",
        icons: 2,
        hasDollarSign: true,
        hasCharIcon: true,
        charIconLeft: "/zzz/xinghuibili.png",
        charIconRight: "/zzz/aofeisi.png",
      },
      {
        name: "游乐岛拯救计划",
        startTime: "2026-05-07 10",
        endTime: "2026-06-15 04",
        type: "orange",
        icons: 4,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        name: "极限裁决试炼",
        startTime: "2026-05-13 10",
        endTime: "2026-06-01 04",
        type: "orange",
        icons: 2,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        name: "先遣赏金",
        startTime: "2026-05-20 04",
        endTime: "2026-05-25 04",
        type: "orange",
        icons: 2,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        name: "「灵魂」画手侧写簿",
        startTime: "2026-05-27 10",
        endTime: "2026-06-15 04",
        type: "gray",
        icons: 3,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        name: "走近丽都异闻",
        startTime: "2026-06-01 10",
        endTime: "2026-06-15 04",
        type: "gray",
        icons: 3,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        name: "数据悬赏",
        startTime: "2026-06-10 04",
        endTime: "2026-06-15 04",
        type: "orange",
        icons: 3,
        hasDollarSign: false,
        hasCharIcon: false,
      },
      {
        name: "早安，罗斯凯利法",
        startTime: "2026-06-06 10",
        endTime: "2026-06-17 06",
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
