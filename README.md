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
- **基础按钮**: `lv_example_get_started_1.py` - 学习如何创建按钮并绑定点击事件。
- **对象样式**: `lv_example_get_started_2.py` - 演示如何通过代码动态修改对象外观。
- **交互控制**: `lv_example_get_started_3.py` - 滑动条与文本标签的联动示例。

### 🧩 核心组件 ([widgets/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/widgets))
这是本项目最庞大的部分，展示了 LVGL 丰富的 UI 控件：
| 类别 | 描述 | 关键示例 |
| :--- | :--- | :--- |
| **基础显示** | 标签、图像、线条、LED | `label_1`, `img_1`, `line_1`, `led_1` |
| **数值输入** | 滑动条、弧形、滚轮、数字输入框 | `slider_1`, `arc_1`, `roller_1`, `spinbox_1` |
| **进度/状态** | 进度条、仪表盘、等待动画、开关 | `bar_1`, `meter_1`, `spinner_1`, `switch_1` |
| **复杂交互** | 日历、列表、表格、按钮矩阵、下拉菜单 | `calendar_1`, `list_1`, `table_1`, `btnmatrix_1` |
| **高级容器** | 画布、选项卡、窗口、平铺视图 | `canvas_1`, `tabview_1`, `win_1`, `tileview_1` |
| **特殊功能** | 文本域、键盘、消息框、颜色选择器 | `textarea_1`, `keyboard_1`, `msgbox_1`, `colorwheel_1` |

### 📐 布局管理 ([layouts/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/layouts))
- **Flex (弹性布局)**: 类似 CSS Flexbox。
  - `flex_1` 到 `flex_6` 展示了行列排列、换行、对齐、生长因子 (Grow) 及从右向左 (RTL) 支持。
- **Grid (网格布局)**: 类似 CSS Grid。
  - `grid_1` 到 `grid_6` 展示了单元格跨度、对齐方式、拉伸效果及动态位置调整。

### ✨ 动画效果 ([anim/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/anim))
- **基础路径**: `lv_example_anim_1.py` - 演示线性、平滑、回弹等动画路径。
- **多重动画**: `lv_example_anim_2.py` - 同一对象执行多个动画（如位置与大小同时改变）。
- **时间轴**: `lv_example_anim_timeline_1.py` - 像视频剪辑一样精确控制多个对象的动画时序。

### 🎨 样式美化 ([styles/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/styles))
- 提供了 14 个示例，深度展示了如何自定义 UI：
  - 边框、阴影、背景渐变、透明度、圆角、内边距、外边距、文本样式等。

### 🖱️ 滚动控制 ([scroll/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/scroll))
- **自动滚动**: `scroll_1` 演示内容溢出时如何自动出现滚动条。
- **滚动捕捉 (Snap)**: `scroll_2` 演示如何让滚动停止在特定的对象中心。
- **嵌套滚动**: `scroll_6` 演示容器内外滚动的嵌套处理。

### 🖼️ 资源与扩展 ([libs/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/libs) & [assets/](file:///c:/Users/Administrator/Downloads/lv_mpy_examples_v9/assets))
- **多媒体**: 支持 BMP, PNG (需要 `lodepng`), GIF 动画及 QR Code 生成。
- **字体库**: `assets/font/` 目录下包含了多种尺寸的 Montserrat 字体及 SimSun 中文字体支持。
- **图片资源**: 提供了一系列 PNG 图片（如齿轮、星星、按钮背景）用于美化界面。

---

## 🛠️ GC9A01 专属示例代码

这是一个完整的、基于 GC9A01 初始化并显示一个居中按钮的简单示例：

```python
import lvgl as lv
import time
from display_driver import init_display, init_touch
import task_handler

# 1. 初始化 LVGL 核心库
lv.init()

# 2. 初始化显示屏和触摸屏驱动
# display_driver.py 内部已处理 SPI/I2C 和引脚配置
display = init_display()
touch = init_touch()

# 3. 屏幕参数微调 (针对圆形屏)
display.set_power(True)
display.init()
display.set_color_inversion(True)      # GC9A01 通常需要颜色反转
display.set_rotation(lv.DISPLAY_ROTATION._180) # 根据安装方向旋转
display.set_backlight(100)             # 设置亮度

# 4. 创建 UI 内容
scr = lv.screen_active()

# 创建一个美观的标签
label = lv.label(scr)
label.set_text("LVGL v9\nGC9A01")
label.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
label.set_style_text_font(lv.font_montserrat_16, 0) # 使用内置 16 号字体
label.set_style_text_color(lv.palette_main(lv.PALETTE.BLUE), 0)
label.align(lv.ALIGN.CENTER, 0, -30)

# 创建一个交互按钮
btn = lv.button(scr)
btn.set_size(100, 40)
btn.align(lv.ALIGN.CENTER, 0, 40)
btn_label = lv.label(btn)
btn_label.set_text("Click Me!")
btn_label.center()

# 按钮事件回调
def btn_event_cb(e):
    code = e.get_code()
    if code == lv.EVENT.CLICKED:
        print("Button clicked!")
        label.set_text("Welcome to\nMicroPython!")

btn.add_event_cb(btn_event_cb, lv.EVENT.CLICKED, None)

# 5. 保持 UI 刷新
th = task_handler.TaskHandler()
```

---

## 📝 注意事项
- **显存占用**: GC9A01 分辨率为 240x240，RGB565 模式下全屏刷新对内存有一定要求。
- **字体加载**: 使用 `assets/font/` 下的外部字体时，请确保已初始化 `fs_driver` 以支持文件系统读取。
- **圆形屏适配**: 设计 UI 时，请注意圆形边缘可能裁剪内容，建议将关键信息放在屏幕中心区域。
