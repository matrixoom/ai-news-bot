# Trend Insight UI 设计系统

## 1. 视觉原则

- 数据优先：摘要、表格和图表先于装饰性内容。
- 开放布局：使用细边框、分区和留白，避免多层大圆角卡片。
- 中文优先：系统字体栈为 `Segoe UI / PingFang SC / Microsoft YaHei / system-ui`。
- 数字对齐：全局启用 `tabular-nums`。
- 动效克制：交互过渡为 `150-200ms`，并遵循 `prefers-reduced-motion`。

## 2. 语义令牌

令牌定义在 `frontend/src/index.css`，Tailwind 映射位于 `frontend/tailwind.config.ts`。

| 令牌 | 用途 |
| --- | --- |
| `canvas` | 应用背景 |
| `surface` | 主表面、侧栏、面板 |
| `surface-subtle` | 表头、筛选区、弱强调背景 |
| `line` | 分隔线和控件边框 |
| `ink` / `muted` | 主文字 / 次要文字 |
| `accent` / `accent-soft` | 选中态、主操作、导航指示 |
| `positive` / `negative` | A 股上涨 / 下跌 |
| `warning` | 警告状态 |

亮暗主题仅切换 CSS 变量，不覆盖 Tailwind 工具类。面板圆角为 `12px`，控件圆角为 `8px`。

## 3. 公共组件

- `.workbench-panel`：研究面板与数据容器。
- `.workbench-button` / `.workbench-button-primary`：次要和主要按钮。
- `.workbench-icon-button`：Heroicons 图标按钮。
- `.workbench-input`：输入框、日期和选择控件。
- `ModulePageFrame`：模块标题、说明、主区和侧栏。
- `PanelState`：加载、空白和异常状态。
- `ProfessionalPlaceholder`：未开放模块的专业占位态。

常规 UI 图标统一使用 `@heroicons/react`。

## 4. 图表规范

`frontend/src/shared/charts/use-workbench-chart-theme.ts` 提供 ECharts 亮暗主题：

- 坐标轴、网格线、图例和 tooltip 使用统一颜色。
- A 股 K 线使用红涨绿跌，并保留文字、箭头或图例辅助识别。
- 图表必须展示标题、单位、图例和状态。
- 图表容器监听主题变化并重新生成 option。

## 5. 响应式

- `>= 1024px`：桌面侧栏展开 `224px`，折叠 `72px`。
- `< 1024px`：侧栏改为抽屉，内容区不保留固定双列。
- 页面边距：移动端 `16px`，平板和桌面 `24px`。
- 表格在窄屏使用受控横向滚动或隐藏次要列，不压缩主标识和核心数值。

视觉回归至少检查 `375 / 768 / 1024 / 1440px`。
