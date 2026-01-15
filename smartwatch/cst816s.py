# cst816.py
# Versión optimizada - Compatible con pointer_framework

from micropython import const
import pointer_framework
import time
import machine

# Dirección I2C
I2C_ADDR = const(0x15)

# Registros principales
_GestureID = const(0x01)
_FingerNum = const(0x02)
_XposH = const(0x03)
_XposL = const(0x04)
_YposH = const(0x05)
_YposL = const(0x06)
_RegisterVersion = const(0x15)
_ChipID = const(0xA7)
_ProjID = const(0xA8)
_FwVersion = const(0xA9)
_MotionMask = const(0xEC)
_IrqCtl = const(0xFA)
_DisAutoSleep = const(0xFE)
_AutoSleepTime = const(0xF9)
_LongPressTime = const(0xFC)
_AutoReset = const(0xFB)

# 支持多个Chip ID值（不同版本的芯片）
_ChipIDValues = [0xB4, 0xB5, 0xB6]

# Configuraciones de IRQ
_EnTouch = const(0x40)
_EnChange = const(0x20)
_EnMotion = const(0x10)
_OnceWLP = const(0x01)

# Gestos - 必须在这里定义常量
GESTURE_NONE = const(0x00)
GESTURE_SWIPE_UP = const(0x01)
GESTURE_SWIPE_DOWN = const(0x02)
GESTURE_SWIPE_LEFT = const(0x03)
GESTURE_SWIPE_RIGHT = const(0x04)
GESTURE_SINGLE_CLICK = const(0x05)
GESTURE_DOUBLE_CLICK = const(0x0B)
GESTURE_LONG_PRESS = const(0x0C)

class CST816S(pointer_framework.PointerDriver):
    """
    Controlador CST816S optimizado - Mantiene compatibilidad total
    """

    def __init__(
        self,
        device,
        reset_pin=None,
        touch_cal=None,
        startup_rotation=None,
        debug=False
    ):
        # Buffer para lectura individual
        self._rx_buf = bytearray(1)
        self._device = device
        self._debug = debug
        
        # Buffer para lectura múltiple (6 registros: gesture, finger, xh, xl, yh, yl)
        self._multi_buf = bytearray(6)
        
        # Estado del controlador
        self._is_suspended = False
        self._last_gesture = GESTURE_NONE
        
        # Configurar pin de reset
        if reset_pin is not None:
            if isinstance(reset_pin, int):
                self._reset_pin = machine.Pin(reset_pin, machine.Pin.OUT)
            else:
                self._reset_pin = reset_pin
            self._reset_pin.value(1)
        else:
            self._reset_pin = None

        # Manejar rotación inicial
        if startup_rotation is None:
            try:
                startup_rotation = pointer_framework.lv.DISPLAY_ROTATION._0
            except:
                startup_rotation = None

        # Reset e inicialización
        self._initialize_chip()
        
        # Inicializar clase base
        try:
            super().__init__(
                touch_cal=touch_cal, startup_rotation=startup_rotation, debug=debug
            )
        except Exception as e:
            if debug:
                print(f"Warning during base initialization: {e}")

    def _initialize_chip(self):
        """Inicialización optimizada del chip"""
        # Reset hardware
        self.hw_reset()
        
        # Esperar a que el chip esté listo
        time.sleep_ms(100)
        
        # Verificar comunicación leyendo Chip ID
        chip_id = self._read_reg(_ChipID)
        if chip_id is None:
            if self._debug:
                print("Error: No communication with CST816S")
            return False
            
        if self._debug:
            print(f'Chip ID: {hex(chip_id)}')
            
        # 支持多个芯片版本
        if chip_id not in _ChipIDValues:
            if self._debug:
                print(f'Warning: Unexpected Chip ID. Got {hex(chip_id)}, expected one of {[hex(x) for x in _ChipIDValues]}')
            # 不阻止初始化，继续尝试
        else:
            if self._debug:
                print("Chip ID verified successfully")
        
        # Leer información del chip
        touch_version = self._read_reg(_RegisterVersion)
        proj_id = self._read_reg(_ProjID)
        fw_version = self._read_reg(_FwVersion)
        
        if self._debug:
            print(f'Touch version: {touch_version}')
            print(f'Proj ID: {hex(proj_id)}')
            print(f'FW Version: {hex(fw_version)}')
        
        # Configuración básica optimizada
        self._write_reg(_IrqCtl, _EnTouch | _EnChange)  # Habilitar detección de touch y cambios
        self._write_reg(_DisAutoSleep, 0x01)  # Deshabilitar auto-sleep
        self._write_reg(_AutoSleepTime, 2)    # Timeout de sleep en segundos
        
        if self._debug:
            print("CST816S initialized successfully")
            
        return True

    def _read_reg(self, reg):
        """Leer registro individual con manejo robusto de errores"""
        try:
            self._device.writeto(I2C_ADDR, bytes([reg]), False)
            self._device.readfrom_into(I2C_ADDR, self._rx_buf)
            return self._rx_buf[0]
        except OSError as e:
            if self._debug:
                print(f"I2C read error at reg {hex(reg)}: {e}")
            return None

    def _write_reg(self, reg, value):
        """Escribir registro con manejo robusto de errores"""
        try:
            self._device.writeto(I2C_ADDR, bytes([reg, value]))
            return True
        except OSError as e:
            if self._debug:
                print(f"I2C write error at reg {hex(reg)}: {e}")
            return False

    def _read_touch_data(self):
        """
        Lectura optimizada de datos de touch - Lee todos los registros necesarios en una operación
        """
        try:
            # Leer registros 0x01 a 0x06 de una sola vez
            self._device.writeto(I2C_ADDR, bytes([_GestureID]), False)
            self._device.readfrom_into(I2C_ADDR, self._multi_buf)
            
            gesture = self._multi_buf[0]
            finger_num = self._multi_buf[1]
            xh = self._multi_buf[2]
            xl = self._multi_buf[3]
            yh = self._multi_buf[4]
            yl = self._multi_buf[5]
            
            return gesture, finger_num, xh, xl, yh, yl
            
        except OSError as e:
            if self._debug:
                print(f"I2C multi-read error: {e}")
            return None

    def _get_coords(self):
        """
        Método principal para obtener coordenadas - Optimizado para rendimiento
        """
        if self._is_suspended:
            return None
        
        # Lectura optimizada de todos los datos
        data = self._read_touch_data()
        if data is None:
            return None
            
        gesture, finger_num, xh, xl, yh, yl = data
        
        # Verificar si hay touch
        if finger_num == 0:
            return None
        
        # Procesar coordenadas
        x = ((xh & 0x0F) << 8) | xl
        y = ((yh & 0x0F) << 8) | yl
        
        # Almacenar gesto para posible uso futuro
        if gesture != GESTURE_NONE:
            self._last_gesture = gesture
        
        return self.PRESSED, x, y

    # === MÉTODOS DE CONTROL BÁSICOS ===
    
    def suspend(self):
        """Suspender detección de touch"""
        self._is_suspended = True

    def resume(self):
        """Reanudar detección de touch"""
        self._is_suspended = False

    def hw_reset(self):
        """Reset hardware del chip"""
        if self._reset_pin is None:
            return

        self._reset_pin.value(0)
        time.sleep_ms(5)
        self._reset_pin.value(1)
        time.sleep_ms(50)

    # === PROPIEDADES DE CONFIGURACIÓN ===
    
    @property
    def auto_sleep(self):
        """Obtener estado del auto-sleep"""
        val = self._read_reg(_DisAutoSleep)
        if val is None:
            return None
        return val == 0x00

    @auto_sleep.setter
    def auto_sleep(self, enable):
        """Habilitar/deshabilitar auto-sleep"""
        if enable:
            self._write_reg(_DisAutoSleep, 0x00)
        else:
            self._write_reg(_DisAutoSleep, 0x01)

    @property
    def auto_sleep_timeout(self):
        """Obtener timeout de auto-sleep"""
        return self._read_reg(_AutoSleepTime)

    @auto_sleep_timeout.setter
    def auto_sleep_timeout(self, seconds):
        """Configurar timeout de auto-sleep (1-255 segundos)"""
        if seconds < 1:
            seconds = 1
        elif seconds > 255:
            seconds = 255
        self._write_reg(_AutoSleepTime, seconds)

    # === NUEVOS MÉTODOS MEJORADOS ===
    
    def get_gesture(self):
        """Obtener el último gesto detectado"""
        current_gesture = self._last_gesture
        self._last_gesture = GESTURE_NONE  # Reset después de leer
        return current_gesture

    def gesture_to_string(self, gesture):
        """Convertir código de gesto a string"""
        gestures = {
            GESTURE_NONE: "NONE",
            GESTURE_SWIPE_UP: "SWIPE UP",
            GESTURE_SWIPE_DOWN: "SWIPE DOWN",
            GESTURE_SWIPE_LEFT: "SWIPE LEFT",
            GESTURE_SWIPE_RIGHT: "SWIPE RIGHT",
            GESTURE_SINGLE_CLICK: "SINGLE CLICK",
            GESTURE_DOUBLE_CLICK: "DOUBLE CLICK",
            GESTURE_LONG_PRESS: "LONG PRESS"
        }
        return gestures.get(gesture, f"UNKNOWN ({hex(gesture)})")

    def set_long_press_time(self, seconds):
        """Configurar tiempo para long press (0-255 segundos, 0=deshabilitar)"""
        if seconds < 0:
            seconds = 0
        elif seconds > 255:
            seconds = 255
        return self._write_reg(_LongPressTime, seconds)

    def set_auto_reset_time(self, seconds):
        """Configurar auto-reset por touch inválido (0-255 segundos, 0=deshabilitar)"""
        if seconds < 0:
            seconds = 0
        elif seconds > 255:
            seconds = 255
        return self._write_reg(_AutoReset, seconds)

    def enable_double_click(self, enable=True):
        """Habilitar/deshabilitar detección de double click"""
        current_mask = self._read_reg(_MotionMask) or 0
        if enable:
            new_mask = current_mask | 0x01  # Bit 0 para double click
        else:
            new_mask = current_mask & ~0x01
            
        return self._write_reg(_MotionMask, new_mask)

    def get_chip_info(self):
        """Obtener información completa del chip"""
        info = {}
        try:
            info['chip_id'] = self._read_reg(_ChipID)
            info['proj_id'] = self._read_reg(_ProjID)
            info['fw_version'] = self._read_reg(_FwVersion)
            info['touch_version'] = self._read_reg(_RegisterVersion)
            info['auto_sleep'] = self.auto_sleep
            info['auto_sleep_timeout'] = self.auto_sleep_timeout
        except:
            pass
        return info

    def print_debug_info(self):
        """Imprimir información de debug"""
        if not self._debug:
            return
            
        info = self.get_chip_info()
        print("=== CST816S Debug Info ===")
        for key, value in info.items():
            print(f"{key}: {value}")
        print("==========================")
