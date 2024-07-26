# qteye_blink_qualia.py - a stand-alone round LCD "eye" on a ESP32-S3 Qualia board
# 16 Oct 2023 - @todbot / Tod Kurt
# Part of circuitpython-tricks/larger-tricks/eyeballs
# also see: https://todbot.com/blog/2022/05/19/multiple-displays-in-circuitpython-compiling-custom-circuitpython/

import time, math, random
import board, busio
import displayio
import adafruit_imageload

# config: behaviors
eye_twitch_time = 2    # bigger is less twitchy
eye_twitch_amount = 20  # allowable deviation from center for iris
eye_blink_time = 1.8    # bigger is slower
eye_rotation = 00        # 0 or 180, don't do 90 or 270 because too slow (on gc9a01)


# config: wiring for QT Py, should work on any QT Py or XIAO board, but ESP32-S3 is fastest
# import gc9a01
# spi0 = busio.SPI(clock=tft0_clk, MOSI=tft0_mosi)
# tft0_clk  = board.SCK
# tft0_mosi = board.MOSI
# tft_L0_rst = board.MISO
# tft_L0_dc  = board.RX
# tft_L0_cs  = board.TX
# display_bus = displayio.FourWire(spi, command=dc, chip_select=cs, reset=rst, baudrate=64_000_000)
# display = gc9a01.GC9A01(display_bus, width=dw, height=dh, rotation=rot)
# display.auto_refresh = False
# dw, dh = 240, 240  # display dimensions

# config: for Qualia ESP32S3 board and 480x480 round display
# followed the instructions here:
#   https://learn.adafruit.com/adafruit-qualia-esp32-s3-for-rgb666-displays/circuitpython-display-setup
# and cribbed from @dexter/@rsbohn's work:
#   https://gist.github.com/rsbohn/26a8e69c8fe80112a24e7de09177e8d9
#
# https://github.com/todbot/circuitpython-tricks/tree/main/larger-tricks/eyeballs
import dotclockframebuffer
from framebufferio import FramebufferDisplay

init_sequence_TL021WVC02 = bytes((
    0xff, 0x05, 0x77, 0x01, 0x00, 0x00, 0x10,
    0xc0, 0x02, 0x3b, 0x00,
    0xc1, 0x02, 0x0b, 0x02,
    0xc2, 0x02, 0x00, 0x02,
    0xcc, 0x01, 0x10,
    0xcd, 0x01, 0x08,
    0xb0, 0x10, 0x02, 0x13, 0x1b, 0x0d, 0x10, 0x05, 0x08, 0x07, 0x07, 0x24, 0x04, 0x11, 0x0e, 0x2c, 0x33, 0x1d,
    0xb1, 0x10, 0x05, 0x13, 0x1b, 0x0d, 0x11, 0x05, 0x08, 0x07, 0x07, 0x24, 0x04, 0x11, 0x0e, 0x2c, 0x33, 0x1d,
    0xff, 0x05, 0x77, 0x01, 0x00, 0x00, 0x11,
    0xb0, 0x01, 0x5d,
    0xb1, 0x01, 0x43,
    0xb2, 0x01, 0x81,
    0xb3, 0x01, 0x80,
    0xb5, 0x01, 0x43,
    0xb7, 0x01, 0x85,
    0xb8, 0x01, 0x20,
    0xc1, 0x01, 0x78,
    0xc2, 0x01, 0x78,
    0xd0, 0x01, 0x88,
    0xe0, 0x03, 0x00, 0x00, 0x02,
    0xe1, 0x0b, 0x03, 0xa0, 0x00, 0x00, 0x04, 0xa0, 0x00, 0x00, 0x00, 0x20, 0x20,
    0xe2, 0x0d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xe3, 0x04, 0x00, 0x00, 0x11, 0x00,
    0xe4, 0x02, 0x22, 0x00,
    0xe5, 0x10, 0x05, 0xec, 0xa0, 0xa0, 0x07, 0xee, 0xa0, 0xa0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xe6, 0x04, 0x00, 0x00, 0x11, 0x00,
    0xe7, 0x02, 0x22, 0x00,
    0xe8, 0x10, 0x06, 0xed, 0xa0, 0xa0, 0x08, 0xef, 0xa0, 0xa0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0xeb, 0x07, 0x00, 0x00, 0x40, 0x40, 0x00, 0x00, 0x00,
    0xed, 0x10, 0xff, 0xff, 0xff, 0xba, 0x0a, 0xbf, 0x45, 0xff, 0xff, 0x54, 0xfb, 0xa0, 0xab, 0xff, 0xff, 0xff,
    0xef, 0x06, 0x10, 0x0d, 0x04, 0x08, 0x3f, 0x1f,
    0xff, 0x05, 0x77, 0x01, 0x00, 0x00, 0x13,
    0xef, 0x01, 0x08,
    0xff, 0x05, 0x77, 0x01, 0x00, 0x00, 0x00,
    0x36, 0x01, 0x00,
    0x3a, 0x01, 0x60,
    0x11, 0x80, 0x64,
    0x29, 0x80, 0x32,
))

tft_timings = {
    "frequency": 16_000_000,
    "width": 480,
    "height": 480,
    "hsync_pulse_width": 20,
    "hsync_front_porch": 40,
    "hsync_back_porch": 40,
    "vsync_pulse_width": 10,
    "vsync_front_porch": 40,
    "vsync_back_porch": 40,
    "hsync_idle_low": False,
    "vsync_idle_low": False,
    "de_idle_high": False,
    "pclk_active_high": True,
    "pclk_idle_high": False,
}

displayio.release_displays()
board.I2C().deinit()
i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
dotclockframebuffer.ioexpander_send_init_sequence(
    i2c, init_sequence_TL021WVC02, **(dict(board.TFT_IO_EXPANDER)))
i2c.deinit()

fb = dotclockframebuffer.DotClockFramebuffer(
    **(dict(board.TFT_PINS)), **tft_timings)
display = FramebufferDisplay(fb,  rotation=eye_rotation)
display.auto_refresh=False

dw_real, dh_real = 480, 480
dw, dh = 240,240  # for emulation with 240x240 displays

# load our eye and iris bitmaps
##  static so load from disk (also can't have it it RAM and eyelids in RAM too)
eyeball_bitmap = displayio.OnDiskBitmap(open("/imgs/eye0_ball2.bmp", "rb"))
eyeball_pal = eyeball_bitmap.pixel_shader
##  moves around, so load into RAM
iris_bitmap, iris_pal = adafruit_imageload.load("imgs/eye0_iris0.bmp")
iris_pal.make_transparent(0)
##  also moves, so load into RAM (hopefully)
try:
    eyelid_bitmap, eyelid_pal = adafruit_imageload.load("/imgs/eyelid_spritesheet2.bmp")
except Exception as e:
    print("couldn't load",e)
    eyelid_bitmap = displayio.OnDiskBitmap(open("/imgs/eyelid_spritesheet2.bmp", "rb"))
    eyelid_pal = eyelid_bitmap.pixel_shader
eyelid_sprite_cnt = eyelid_bitmap.width // dw  # should be 16
eyelid_pal.make_transparent(1)

# compute or declare some useful info about the eyes
iris_w, iris_h = iris_bitmap.width, iris_bitmap.height  # iris is normally 110x110
iris_cx, iris_cy = dw//2 - iris_w//2, dh//2 - iris_h//2


# class to help us track eye info (not needed for this use exactly, but I find it interesting)
class Eye:
    """
        global variables used:
        - iris_cx, iris_cy
        - eye_twitch_amount
        - eye_twitch_time
        - eye_blink_time
    """
    def __init__(self, display, eye_speed=0.25):
        # ends up being 80 MHz on ESP32-S3, nice
        main = displayio.Group(scale=2)
        display.root_group = main
        self.display = display
        self.eyeball = displayio.TileGrid(eyeball_bitmap, pixel_shader=eyeball_pal)
        self.iris = displayio.TileGrid(iris_bitmap, pixel_shader=iris_pal, x=iris_cx,y=iris_cy)
        self.lids = displayio.TileGrid(eyelid_bitmap, pixel_shader=eyelid_pal, x=0, y=0, tile_width=dw, tile_height=dw)
        main.append(self.eyeball)
        main.append(self.iris)
        main.append(self.lids)
        self.x, self.y = iris_cx, iris_cy
        self.tx, self.ty = self.x, self.y
        self.next_time = 0
        self.eye_speed = eye_speed
        self.lidpos = 0
        self.lidpos_inc = 1
        self.lid_next_time = 0

    def update(self):
        # make the eye twitch around
        self.x = self.x * (1-self.eye_speed) + self.tx * self.eye_speed # "easing"
        self.y = self.y * (1-self.eye_speed) + self.ty * self.eye_speed
        self.iris.x = int( self.x )
        self.iris.y = int( self.y ) # + 10  # have it look down a bit FIXME
        if time.monotonic() > self.next_time:
            # pick a new "target" for the eye to look at
            t = random.uniform(0.25, eye_twitch_time)
            self.next_time = time.monotonic() + t
            self.tx = iris_cx + random.uniform(-eye_twitch_amount,eye_twitch_amount)
            self.ty = iris_cy + random.uniform(-eye_twitch_amount,eye_twitch_amount)
        # elif to minimize display changes per update
        elif time.monotonic() > self.lid_next_time:
            # make the eye blink its eyelids
            self.lid_next_time = time.monotonic() + random.uniform( eye_blink_time*0.5, eye_blink_time*1.5)
            self.lidpos = self.lidpos + self.lidpos_inc
            self.lids[0] = self.lidpos
            if self.lidpos == 0 or self.lidpos == eyelid_sprite_cnt-1:
                self.lidpos_inc *= -1  # change direction

        self.display.refresh()



# a list of all the eyes, in this case, only one
the_eyes = [
    Eye( display ),
]

while True:
    for eye in the_eyes:
        eye.update()

