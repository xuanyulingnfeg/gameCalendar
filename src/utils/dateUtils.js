/**
 * 日期计算工具
 * 根据配置的起始日期和结束日期，按天均分时间轴
 */

/**
 * 计算时间轴信息
 * 接收 startDate 和 endDate 字符串
 * 返回 { totalDays, startDate, endDate }
 */
export function getTimelineInfo(startDate, endDate) {
  const start = new Date(startDate);
  start.setHours(0, 0, 0, 0);
  const end = new Date(endDate);
  end.setHours(0, 0, 0, 0);

  const totalDays =
    Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;

  return {
    totalDays,
    startDate,
    endDate,
  };
}

/**
 * 计算当前时刻在时间轴上的精确比例位置 (0~1)
 * 接收 startDate 和 endDate 字符串
 * 计算 (当前时刻 - startDate) / (endDate - startDate + 1天)
 */
export function getPreciseTodayPosition(startDate, endDate, now = new Date()) {
  const start = new Date(startDate);
  start.setHours(0, 0, 0, 0);
  const end = new Date(endDate);
  end.setHours(0, 0, 0, 0);

  const totalMs = end.getTime() - start.getTime() + 24 * 60 * 60 * 1000; // endDate - startDate + 1天
  const totalDays = totalMs / (1000 * 60 * 60 * 24);

  const todayDate = new Date(now);
  todayDate.setHours(0, 0, 0, 0);

  const fullDays =
    (todayDate.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);

  // 当天已过时间比例
  const dayFraction = (now.getHours() * 60 + now.getMinutes()) / (24 * 60);

  const preciseDays = fullDays + dayFraction;
  console.log(preciseDays);

  return Math.min(Math.max(preciseDays / totalDays, 0), 1);
}

/**
 * 获取今天的显示文本
 */
export function getTodayLabel(today = new Date()) {
  const weekDays = [
    "星期日",
    "星期一",
    "星期二",
    "星期三",
    "星期四",
    "星期五",
    "星期六",
  ];
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  const weekDay = weekDays[today.getDay()];

  return `今天 ${month}/${day} ${weekDay}`;
}

function formatDate(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${month}/${day}`;
}
