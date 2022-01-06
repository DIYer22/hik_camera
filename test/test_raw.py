#!/usr/bin/env python3

import os
import boxx
import test_base

from hik_camera import HikCamera


class RawCam(HikCamera):
    def setting(self):
        super().setting()
        self.set_raw()


if __name__ == "__main__":
    from boxx import *

    cam = RawCam.get_cam()
    with cam:
        raw = cam.robust_get_frame()
        if cam.is_raw:
            rgbs = [
                cam.raw_to_uint8_rgb(raw, poww=1),
                cam.raw_to_uint8_rgb(raw, poww=0.3),
            ]
            boxx.shows(rgbs)
            dngp = "/tmp/test-raw.dng"
            cam.save_raw(raw, dngp)
            os.system(f"ls -lh {dngp}")
            boxx.showb(dngp)
