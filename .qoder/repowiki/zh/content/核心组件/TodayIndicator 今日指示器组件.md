# TodayIndicator 今日指示器组件

<cite>
**本文引用的文件**
- [TodayIndicator.vue](file://src/components/TodayIndicator.vue)
- [GameCalendar.vue](file://src/components/GameCalendar.vue)
- [dateUtils.js](file://src/utils/dateUtils.js)
- [WeekHeader.vue](file://src/components/WeekHeader.vue)
- [ActivityBar.vue](file://src/components/ActivityBar.vue)
- [activities.js](file://src/config/activities.js)
- [App.vue](file://src/App.vue)
- [main.js](file://src/main.js)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考量](#性能考量)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)
10. [附录：使用与集成指南](#附录使用与集成指南)

## 简介
TodayIndicator 是一个用于在6周时间轴上动态定位并标记“当前日期”的可视化组件。它通过接收两个关键属性：
- position：表示当前日期在6周时间轴上的相对位置（0~1之间的数值）
- label：用于显示“今天”信息的文本标签

组件的核心职责是：
- 将 position 转换为可视化的绝对定位偏移量，使指示器在时间轴上准确对齐
- 展示当前日期的友好标签文本
- 提供简洁、醒目的视觉提示，确保用户能快速识别当前日期所在位置

## 项目结构
该项目采用 Vue 3 单页应用结构，组件化组织清晰。TodayIndicator 作为子组件被 GameCalendar 使用，并通过 dateUtils 提供的工具函数计算 position 和 label。

```mermaid
graph TB
subgraph "应用入口"
APP["App.vue"]
MAIN["main.js"]
end
subgraph "主界面"
GC["GameCalendar.vue"]
WI["TodayIndicator.vue"]
WH["WeekHeader.vue"]
AB["ActivityBar.vue"]
end
subgraph "工具与配置"
DU["dateUtils.js"]
ACT["activities.js"]
end
APP --> GC
MAIN --> APP
GC --> WI
GC --> WH
GC --> AB
GC --> DU
AB --> ACT
```

图表来源
- [App.vue:1-29](file://src/App.vue#L1-L29)
- [main.js:1-5](file://src/main.js#L1-L5)
- [GameCalendar.vue:1-85](file://src/components/GameCalendar.vue#L1-L85)
- [TodayIndicator.vue:1-53](file://src/components/TodayIndicator.vue#L1-L53)
- [WeekHeader.vue:1-67](file://src/components/WeekHeader.vue#L1-L67)
- [ActivityBar.vue:1-164](file://src/components/ActivityBar.vue#L1-L164)
- [dateUtils.js:1-126](file://src/utils/dateUtils.js#L1-L126)
- [activities.js:1-53](file://src/config/activities.js#L1-L53)

章节来源
- [App.vue:1-29](file://src/App.vue#L1-L29)
- [main.js:1-5](file://src/main.js#L1-L5)
- [GameCalendar.vue:1-85](file://src/components/GameCalendar.vue#L1-L85)

## 核心组件
TodayIndicator 组件负责在时间轴上绘制“今日”指示器，包含以下关键点：
- 接收 position 和 label 两个必填属性
- 使用内联样式将 left 设置为 position × 100%，实现水平方向的百分比定位
- 渲染一个带标签的垂直线，形成“竖线+标签”的视觉指示器

该组件的定位策略基于父容器的宽度，通过百分比 left 实现与时间轴刻度的同步对齐。

章节来源
- [TodayIndicator.vue:1-53](file://src/components/TodayIndicator.vue#L1-L53)

## 架构总览
TodayIndicator 的工作流由 GameCalendar 驱动，后者负责：
- 计算6周时间范围（以周四为一周起始）
- 计算当前时刻在6周时间轴上的精确位置（position）
- 生成“今天”标签文本（label）
- 每分钟刷新 position，保持指示器实时移动

```mermaid
sequenceDiagram
participant GC as "GameCalendar.vue"
participant DU as "dateUtils.js"
participant TI as "TodayIndicator.vue"
GC->>DU : "调用 getPreciseTodayPosition()"
DU-->>GC : "返回 position (0~1)"
GC->>TI : "传递 { position, label }"
TI-->>TI : "left = position * 100%"
TI-->>GC : "渲染指示器"
```

图表来源
- [GameCalendar.vue:23-53](file://src/components/GameCalendar.vue#L23-L53)
- [dateUtils.js:78-94](file://src/utils/dateUtils.js#L78-L94)
- [TodayIndicator.vue:1-6](file://src/components/TodayIndicator.vue#L1-L6)

章节来源
- [GameCalendar.vue:23-53](file://src/components/GameCalendar.vue#L23-L53)
- [dateUtils.js:78-94](file://src/utils/dateUtils.js#L78-L94)

## 详细组件分析

### TodayIndicator 组件
- 属性定义
  - position: Number，必填，表示当前日期在6周时间轴上的相对位置（0~1）
  - label: String，必填，显示“今天”的友好文本
- 视觉设计
  - 容器采用绝对定位，顶部偏移至 -28px，z-index 保证层级高于内容
  - 使用 transform: translateX(-50%) 实现水平居中
  - 标签背景色为品牌红，白色文字，圆角，字号适中
  - 垂直线宽 2px，长度 600px，颜色与标签一致，从顶部 26px 开始延伸到底部
- 动态定位
  - 通过内联样式 left: position * 100% 实现水平定位
  - position 为 0 表示时间轴最左侧，1 表示最右侧

```mermaid
classDiagram
class TodayIndicator {
+prop position : Number
+prop label : String
+render() "left = position * 100%"
+style "absolute, transform, flex, red line"
}
```

图表来源
- [TodayIndicator.vue:1-53](file://src/components/TodayIndicator.vue#L1-L53)

章节来源
- [TodayIndicator.vue:1-53](file://src/components/TodayIndicator.vue#L1-L53)

### 位置计算算法（position）
position 的计算逻辑如下：
- 以“周四”为一周的起始日，确定当前维护周期的起始日
- 6周总时长为 6×7=42 天
- 对于“精确位置”，在“完整天数”基础上加上“当天已过时间占比”
  - 当天已过时间占比 = (小时×60 + 分钟) / (24×60)
- 最终 position = clamp(精确天数 / 42, 0, 1)

```mermaid
flowchart TD
Start(["开始"]) --> WS["获取本周起始日(周四)"]
WS --> FD["计算到起始日的完整天数"]
FD --> DF["计算当天已过时间占比"]
DF --> PD["精确天数 = 完整天数 + 已过占比"]
PD --> POS["position = clamp(精确天数 / 42, 0, 1)"]
POS --> End(["结束"])
```

图表来源
- [dateUtils.js:78-94](file://src/utils/dateUtils.js#L78-L94)

章节来源
- [dateUtils.js:78-94](file://src/utils/dateUtils.js#L78-L94)

### 标签生成（label）
TodayIndicator 的 label 由外部传入，GameCalendar 通过工具函数生成“今天”友好文本，格式包含“月份/日期 + 星期几”。该文本直接传递给 TodayIndicator，组件不做二次处理。

章节来源
- [GameCalendar.vue:38-38](file://src/components/GameCalendar.vue#L38-L38)
- [dateUtils.js:99-114](file://src/utils/dateUtils.js#L99-L114)

### 与时间轴的对齐
- 时间轴由 WeekHeader 渲染，包含6个单元格，每个单元格代表一周
- TodayIndicator 的 left 为 position × 100%，与 WeekHeader 的单元格宽度成比例
- transform: translateX(-50%) 确保指示器中心与时间轴刻度对齐

```mermaid
graph LR
TH["WeekHeader<br/>6个单元格"] --> TI["TodayIndicator<br/>left = position*100%"]
TI --> LBL["标签"]
TI --> LINE["竖线"]
```

图表来源
- [WeekHeader.vue:1-67](file://src/components/WeekHeader.vue#L1-L67)
- [TodayIndicator.vue:1-6](file://src/components/TodayIndicator.vue#L1-L6)

章节来源
- [WeekHeader.vue:1-67](file://src/components/WeekHeader.vue#L1-L67)
- [TodayIndicator.vue:1-6](file://src/components/TodayIndicator.vue#L1-L6)

### 与活动条的协作
- ActivityBar 通过计算 startWeek 和 endWeek 在6周时间轴上绘制活动区间
- TodayIndicator 与 ActivityBar 共享同一时间轴基准（以“周四”为起点的6周）
- 二者通过相同的 week 计算逻辑保持视觉一致性

章节来源
- [ActivityBar.vue:38-49](file://src/components/ActivityBar.vue#L38-L49)
- [dateUtils.js:35-55](file://src/utils/dateUtils.js#L35-L55)

## 依赖关系分析
TodayIndicator 的依赖链路清晰且低耦合：
- 直接依赖：GameCalendar（父组件）传递 position 和 label
- 间接依赖：dateUtils（提供 position 和 label 的计算逻辑）
- 视觉依赖：WeekHeader（提供时间轴布局参考）

```mermaid
graph TB
GC["GameCalendar.vue"] --> TI["TodayIndicator.vue"]
GC --> DU["dateUtils.js"]
GC --> WH["WeekHeader.vue"]
TI --> DU
```

图表来源
- [GameCalendar.vue:23-33](file://src/components/GameCalendar.vue#L23-L33)
- [TodayIndicator.vue:1-6](file://src/components/TodayIndicator.vue#L1-L6)
- [dateUtils.js:1-126](file://src/utils/dateUtils.js#L1-L126)
- [WeekHeader.vue:1-67](file://src/components/WeekHeader.vue#L1-L67)

章节来源
- [GameCalendar.vue:23-33](file://src/components/GameCalendar.vue#L23-L33)

## 性能考量
- 位置更新频率：GameCalendar 每分钟更新一次 position，避免高频重绘带来的性能开销
- 精确度平衡：使用“精确位置”算法兼顾了日级和小时级的精度需求
- 视觉成本：指示器仅包含少量 DOM 节点，样式简单，渲染开销极低
- 响应式：position 为百分比，随容器宽度自适应，无需额外计算

## 故障排查指南
- 指示器不显示或位置异常
  - 检查父容器是否正确设置为相对定位（GameCalendar 的容器具备相对定位）
  - 确认 position 是否在 0~1 范围内（getPreciseTodayPosition 已做 clamp）
- 标签不显示
  - 确认 label 属性已正确传入
  - 检查样式中是否有覆盖导致的隐藏
- 更新不生效
  - 确认 GameCalendar 的定时器是否正常运行（每分钟更新一次）
  - 检查组件生命周期钩子是否正确挂载和卸载

章节来源
- [GameCalendar.vue:42-53](file://src/components/GameCalendar.vue#L42-L53)
- [TodayIndicator.vue:1-6](file://src/components/TodayIndicator.vue#L1-L6)

## 结论
TodayIndicator 通过简洁的 API 设计和高效的计算逻辑，在6周时间轴上实现了高精度的“今日”定位。其视觉设计突出、易于理解，配合 GameCalendar 的定时更新机制，确保用户始终能准确识别当前日期在时间轴中的相对位置。组件结构清晰、依赖明确，便于扩展与维护。

## 附录：使用与集成指南

### 如何使用 TodayIndicator
- 在父组件中计算 position 和 label
  - 使用 getPreciseTodayPosition(now) 获取当前位置
  - 使用 getTodayLabel(today) 获取标签文本
- 将结果作为 props 传递给 TodayIndicator
- 确保父容器具有相对定位，以便绝对定位的指示器能正确对齐

章节来源
- [GameCalendar.vue:35-46](file://src/components/GameCalendar.vue#L35-L46)
- [dateUtils.js:78-114](file://src/utils/dateUtils.js#L78-L114)

### 与时间轴的对齐建议
- 保持 WeekHeader 的单元格数量与 totalWeeks 一致（默认6周）
- 使用相同的“周四起始周”规则，确保与 ActivityBar 的区间计算一致
- 若需自定义时间范围，需同步调整 position 的分母（总天数）

章节来源
- [WeekHeader.vue:1-67](file://src/components/WeekHeader.vue#L1-L67)
- [ActivityBar.vue:32-49](file://src/components/ActivityBar.vue#L32-L49)
- [dateUtils.js:35-55](file://src/utils/dateUtils.js#L35-L55)

### 视觉与交互优化
- 颜色与品牌一致：指示器的红色与主题色保持一致
- 文本可读性：标签使用对比度高的配色，避免遮挡活动条
- 动画建议：可在 position 变化时添加过渡动画，提升体验（可选）
- 响应式：position 为百分比，自动适配不同屏幕尺寸

章节来源
- [TodayIndicator.vue:21-51](file://src/components/TodayIndicator.vue#L21-L51)