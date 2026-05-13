/**
 * 日期计算工具
 * 以周四为一周的起始日（游戏维护日）
 * 当前周 = 包含今天的那一周（周四到周三）
 */

/**
 * 获取当前维护周期的起始日（周四）
 * 如果今天是周四，则当前周从今天开始
 * 否则找到最近的上一个周四
 */
export function getCurrentWeekStart(today = new Date()) {
  const date = new Date(today);
  date.setHours(0, 0, 0, 0);

  const dayOfWeek = date.getDay(); // 0=周日, 1=周一, ..., 4=周四, 6=周六

  // 计算距离上一个周四的天数
  // 周四=4, 如果今天是周四则差0天
  let daysToThursday;
  if (dayOfWeek >= 4) {
    daysToThursday = dayOfWeek - 4;
  } else {
    daysToThursday = dayOfWeek + 3; // (7 - 4 + dayOfWeek)
  }

  date.setDate(date.getDate() - daysToThursday);
  return date;
}

/**
 * 计算6个周期的起止日期
 * 返回数组，每项包含 { start: Date, end: Date, label: string, range: string }
 */
export function getWeeks(today = new Date()) {
  const weekStart = getCurrentWeekStart(today);
  const weeks = [];

  for (let i = 0; i < 6; i++) {
    const start = new Date(weekStart);
    start.setDate(start.getDate() + i * 7);

    const end = new Date(start);
    end.setDate(end.getDate() + 6);

    weeks.push({
      start: new Date(start),
      end: new Date(end),
      label: `第${numberToChinese(i + 1)}周`,
      range: `${formatDate(start)}-${formatDate(end)}`,
    });
  }

  return weeks;
}

/**
 * 计算今天在6周时间轴上的比例位置 (0~1)
 * 精确到天级别
 */
export function getTodayPosition(today = new Date()) {
  const weekStart = getCurrentWeekStart(today);
  const totalDays = 6 * 7; // 6周共42天

  const todayDate = new Date(today);
  todayDate.setHours(0, 0, 0, 0);

  const diffTime = todayDate.getTime() - weekStart.getTime();
  const diffDays = diffTime / (1000 * 60 * 60 * 24);

  return Math.min(Math.max(diffDays / totalDays, 0), 1);
}

/**
 * 计算当前时刻在6周时间轴上的精确比例位置 (0~1)
 * 精确到小时和分钟
 */
export function getPreciseTodayPosition(now = new Date()) {
  const weekStart = getCurrentWeekStart(now);
  const totalDays = 6 * 7; // 6周共42天

  const todayDate = new Date(now);
  todayDate.setHours(0, 0, 0, 0);

  const diffTime = todayDate.getTime() - weekStart.getTime();
  const fullDays = diffTime / (1000 * 60 * 60 * 24);

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

function numberToChinese(num) {
  const chinese = ["一", "二", "三", "四", "五", "六"];
  return chinese[num - 1] || num;
}
