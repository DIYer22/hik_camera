#!/usr/bin/env python3

import boxx
import test_base

from hik_camera import HikCamera


class Cam(HikCamera):
    def setting(self):
        # 每隔一定时间拍一次照片来调整自动曝光, 防止隔了太久, 曝光失效
        self.continuous_adjust_exposure(6)
        # 取 RGB 图
        self.pixel_format = "RGB8Packed"
        self.setitem("PixelFormat", self.pixel_format)


if __name__ == "__main__":
    from boxx import *

    with Cam.get_all_cams() as cams:
        for i in range(5):
            frames = cams.robust_get_frame()
            p - "sleep"
            sleep(8)

            frames = cams.robust_get_frame()
            tree - frames
