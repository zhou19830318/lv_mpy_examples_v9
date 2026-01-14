# LVGL v9 MicroPython 示例工程

本项目是一个基于 **LVGL v9** 的 MicroPython 示例集合，特别针对 **GC9A01** 圆形显示屏进行了优化和配置。它涵盖了从基础控件到复杂布局、动画及第三方库集成的全方位案例。

---

## 🚀 快速开始

### 1. 硬件配置 (GC9A01 & CST816S)
项目核心驱动位于 `display_driver.py`。默认配置如下：
- **屏幕型号**: GC9A01 (240x240 圆形屏)
- **显示接口**: SPI (主机 ID: 2, 频率: 80MHz)
- **触摸芯片**: CST816S (I2C 接口)
- **引脚定义**:
  - **显示屏 (SPI)**: SCK: Pin 7, MOSI: Pin 6, DC: Pin 4, CS: Pin 3, RST: Pin 5
  - **触摸屏 (I2C)**: SCL: Pin 8, SDA: Pin 9, RST: Pin 11
  - **背光 (Backlight)**: Pin 2 (低电平点亮)

### 2. 环境依赖
- 已烧录集成 LVGL v9 的 MicroPython 固件。
- 包含 `gc9a01` 和 `lcd_bus` 驱动模块。

---

## 📂 目录结构与详细案例说明

### 🏁 入门指南 ([get_started/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/get_started))
- **基础按钮**: `lv_example_get_started_1.py` - 学习如何创建按钮、设置大小及绑定点击事件回调。
- **对象样式**: `lv_example_get_started_2.py` - 演示如何通过代码动态修改对象的背景色、圆角和阴影等外观属性。
- **交互控制**: `lv_example_get_started_3.py` - 实现滑动条（Slider）与文本标签（Label）的实时数值联动，展示基本的交互逻辑。

### 🧩 核心组件 ([widgets/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/widgets))
展示了 LVGL 丰富的 UI 控件及其高级用法：
- **基础显示**: 
  - `label`: 展示各种文本对齐、长文本滚动及着色模式。
  - `img`: 演示图像缩放、旋转及从不同源（如文件、SRAM）加载图片。
  - `line`, `led`: 基础绘图与状态指示。
- **数值输入**: 
  - `slider`, `arc`: 弧形与直线滑动条，支持范围限制和值改变事件。
  - `roller`, `spinbox`: 滚轮选择器和数字微调框，适用于受限的数值输入。
- **进度/状态**: 
  - `bar`, `meter`: 进度条和多功能仪表盘，支持刻度自定义和动态指针。
  - `spinner`: 用于等待加载的圆环旋转动画。
  - `switch`: 经典的开关控件，支持自定义开关状态下的颜色。
- **复杂交互**: 
  - `calendar`: 全功能日历插件，支持日期高亮和下拉月份选择。
  - `list`, `table`: 列表项点击响应和多行多列的数据展示。
  - `btnmatrix`: 按钮矩阵，高效管理多个相关联的按钮。
  - `dropdown`: 带有弹出列表的下拉选择框，支持自定义箭头图标。
- **高级容器**: 
  - `tabview`, `tileview`: 标签页导航和平铺视图，支持流畅的滑动切换效果。
  - `win`, `msgbox`: 标准窗口布局和模态对话框，用于提示重要信息。

### 📐 布局管理 ([layouts/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/layouts))
- **Flex (弹性布局)**: 模仿 CSS Flexbox，提供强大的自适应排列能力。
  - 展示了如何实现自动换行、权重生长（Grow）、水平垂直对齐等。
- **Grid (网格布局)**: 模仿 CSS Grid，适用于精确的单元格定位。
  - 展示了如何跨行跨列布局、网格内对齐以及响应式调整列宽。

### ✨ 动画效果 ([anim/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/anim))
- **路径与缓动**: 演示了线性、正弦、回弹等 10+ 种缓动函数（Easing functions）。
- **组合动画**: 展示如何让一个物体同时发生位置移动、透明度变化和缩放。
- **时间轴控制**: `lv_example_anim_timeline_1.py` 提供了一种可视化的方式管理多个动画的启动与持续时间。

### 🎨 样式系统 ([styles/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/styles))
- 深入浅出地介绍了 LVGL 的层叠样式表思想：
  - **背景**: 纯色、渐变色、透明度。
  - **边框与阴影**: 宽度、颜色、扩散范围、偏移量。
  - **内边距与外边距**: 调整元素间的精确间距。
  - **文本**: 字体选择、颜色、字间距。

### 🖱️ 滚动控制 ([scroll/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/scroll))
- 演示了复杂的滚动行为，包括：
  - 弹性回弹效果、滚动条显示策略、滚动方向限制以及著名的“磁贴捕捉（Snap）”功能。

### 🖼️ 扩展功能 ([libs/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/libs))
- **第三方库集成**: 
  - `qrcode`: 动态生成二维码，方便手机扫码交互。
  - `gif`, `png`, `bmp`: 演示如何集成各种格式的解码器以支持更丰富的视觉资源。

---

## ⌚ 综合案例：智能手表应用 ([smartwatch_app.py](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/smartwatch_app.py))

本项目包含一个功能完整的智能手表原型，它是学习 LVGL 实战的最佳入口。

### 🌟 核心功能
- **多界面切换**: 采用手势识别系统，左右滑动可在时间、天气、设置页面间无缝切换。
- **网络同步**:
  - **NTP 对时**: 自动连接 WiFi 并通过网络校准本地实时时钟。
  - **实时天气**: 对接知心天气（Seniverse）API，获取气温、天气状况及对应图标。
- **中文化支持**: 集成了中文字库，支持城市名称、日期及天气描述的完美汉化。
- **个性化设置**: 内置中国主流城市下拉选择框，支持切换后自动同步更新天气和对应时区。

### 📱 界面内容展示
1.  **时间主屏 (Time Screen)**:
    - 巨大的数字时钟显示，包含秒针动态更新。
    - 实时日期与星期显示。
    - **多时区支持**: 屏幕内上下滑动可切换北京、东京、伦敦、纽约等全球主要城市时间。
2.  **天气详情页 (Weather Screen)**:
    - 动态天气图标（晴、阴、雨、霾等）。
    - 实时温度数值显示。
    - 城市名称及详细天气文字描述。
3.  **系统设置页 (Settings Screen)**:
    - 城市选择下拉菜单：带自定义箭头图标，可选择中国各大城市。
    - “保存”按钮：具备黑色醒目文字提示，点击后触发全局数据更新。

### 🛠️ 技术亮点
- **手势防抖优化**: 针对触摸屏灵敏度进行了软件过滤，防止连跳页面。
- **圆形屏适配**: 所有 UI 元素均针对 GC9A01 圆形边缘进行了避让和圆弧化处理。
- **资源管理**: 采用高效的二进制图片加载与内存缓存机制，确保在嵌入式设备上运行流畅。

## 📝 注意事项
- **显存占用**: GC9A01 分辨率为 240x240，RGB565 模式下全屏刷新对内存有一定要求。
- **字体加载**: 使用 `assets/font/` 下的外部字体时，请确保已初始化 `fs_driver` 以支持文件系统读取。
- **圆形屏适配**: 设计 UI 时，请注意圆形边缘可能裁剪内容，建议将关键信息放在屏幕中心区域。
