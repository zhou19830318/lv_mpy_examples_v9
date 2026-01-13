# LVGL MicroPython Examples (v9)

本项目提供了一系列基于 LVGL v9 的 MicroPython 示例代码，旨在帮助开发者快速上手并在嵌入式设备（如搭载 GC9A01 显示屏的开发板）上实现丰富的图形界面。

## 项目简介

这些示例涵盖了从基础组件使用到高级布局和动画的各个方面。通过这些案例，您可以学习如何利用 LVGL 强大的功能来构建交互式 UI。

## 硬件配置

本项目默认配置基于 **GC9A01** 圆形显示屏。

- **驱动文件**: [display_driver.py](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/display_driver.py) 包含了 GC9A01 的初始化逻辑。
- **主要参数**:
  - 分辨率: 240x240
  - 接口: SPI
  - 颜色格式: RGB565

## 目录结构与案例说明

项目中的示例按功能分类存放在不同的文件夹中：

### 1. 入门示例 ([get_started/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/get_started))
- `lv_example_get_started_1.py`: 创建一个简单的按钮，点击时更新标签文字。
- `lv_example_get_started_2.py`: 基础布局与多对象操作。
- `lv_example_get_started_3.py`: 滑动条 (Slider) 与标签的联动。

### 2. 组件示例 ([widgets/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/widgets))
包含了 LVGL 绝大多数原生组件的使用方法：
- **Arc (弧形)**: 圆环进度显示。
- **Bar (条形图)**: 水平或垂直进度条。
- **Btn (按钮)**: 基础按钮及其各种状态。
- **Chart (图表)**: 折线图、柱状图等数据可视化。
- **Dropdown (下拉列表)**: 单选菜单。
- **Label (标签)**: 各种文本显示方式，支持换行和样式。
- **Meter (仪表盘)**: 模拟时速表或温度计效果。
- **Slider (滑动条)**: 数值调节。

### 3. 布局管理 ([layouts/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/layouts))
- **Flex (弹性布局)**: 自动排列子对象，支持行/列布局、对齐方式设置。
- **Grid (网格布局)**: 类似 Excel 的网格系统，可精确控制行列跨度。

### 4. 样式设计 ([styles/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/styles))
展示如何通过 `lv.style_t` 对象修改组件的外观：
- 圆角、阴影、渐变色、背景色、边框宽度、内边距等。

### 5. 动画效果 ([anim/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/anim))
- 基础动画：位置、大小、透明度的平滑过渡。
- 时间轴动画：多个动画按序或同步执行。

### 6. 事件处理 ([event/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/event))
- 展示如何捕获各种事件（点击、滑动、数值改变等）并触发回调函数。

### 7. 滚动操作 ([scroll/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/scroll))
- 展示 LVGL 的自动滚动特性，以及如何自定义滚动条行为。

### 8. 第三方库集成 ([libs/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/libs))
- **图片显示**: 支持 BMP, PNG, GIF 格式。
- **二维码**: 动态生成 QR Code。
- **FFmpeg**: 视频支持（需特定固件支持）。

## 如何运行

1. 确保您的 MicroPython 固件已集成 LVGL v9。
2. 将 `display_driver.py` 和所需的示例文件上传到开发板。
3. 运行示例脚本，例如：
   ```python
   import get_started.lv_example_get_started_1
   ```

## 基于 GC9A01 的简单示例

以下是一个最简化的示例，展示如何初始化 GC9A01 显示屏并显示一个“Hello World”标签。

```python
import lvgl as lv
from display_driver import init_display
import time

# 1. 初始化 LVGL
lv.init()

# 2. 初始化 GC9A01 显示屏
# 注意：确保 display_driver.py 中的引脚配置与您的硬件一致
display = init_display()
display.set_power(False)
display.init()
display.set_color_inversion(True)
display.set_rotation(lv.DISPLAY_ROTATION._180)
display.set_backlight(100)
# 3. 创建并显示内容
scr = lv.screen_active()
label = lv.label(scr)
label.set_text("Hello GC9A01!")
# 使用内置字体
label.set_style_text_font(lv.font_montserrat_16, 0)
label.center()

while True:
    lv.timer_handler() # v9 中使用 timer_handler
    time.sleep_ms(5)

```
