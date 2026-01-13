# display_driver.py
import lvgl as lv
import gc9a01
import lcd_bus
import machine
from machine import SPI, Pin
from cst816s import CST816S
from micropython import const

_WIDTH = const(240)
_HEIGHT = const(240)

_SPI_HOST = const(2)
_SPI_SCK = const(7)
_SPI_MOSI = const(6)
_SPI_MISO = const(-1)

_LCD_FREQ = const(80000000)
_LCD_DC = const(4)
_LCD_CS = const(3)
_LCD_RST = const(5)
_LCD_BACKLIGHT = const(2)

_I2C_ID = const(0)
_I2C_SCL = const(8)
_I2C_SDA = const(9)
_TOUCH_RST = const(11)

def init_display():
    # Initialize the SPI bus
    spi_bus = SPI.Bus(
        host=_SPI_HOST,
        mosi=_SPI_MOSI,
        miso=_SPI_MISO,
        sck=_SPI_SCK
    )

    # Initialize the display bus
    display_bus = lcd_bus.SPIBus(
        spi_bus=spi_bus,
        dc=_LCD_DC,
        cs=_LCD_CS,
        freq=_LCD_FREQ
    )

    # Initialize and return the GC9A01 display driver
    return gc9a01.GC9A01(
        data_bus=display_bus,
        display_width=_WIDTH,
        display_height=_HEIGHT,
        reset_pin=_LCD_RST,
        reset_state=gc9a01.STATE_LOW,
        power_on_state=gc9a01.STATE_HIGH,
        backlight_pin=_LCD_BACKLIGHT,
        backlight_on_state=gc9a01.STATE_LOW,
        offset_x=0,
        offset_y=0,
        color_space=lv.COLOR_FORMAT.RGB565,
        color_byte_order=gc9a01.BYTE_ORDER_BGR,
        rgb565_byte_swap=True
    )

def init_touch():
    # Initialize the I2C bus for touch
    i2c = machine.I2C(_I2C_ID, scl=machine.Pin(_I2C_SCL), sda=machine.Pin(_I2C_SDA), freq=400000)
    
    # Initialize and return the CST816S touch driver
    touch = CST816S(i2c, reset_pin=machine.Pin(_TOUCH_RST, machine.Pin.OUT))
    touch.auto_sleep = False
    return touch
