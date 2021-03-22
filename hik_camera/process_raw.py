#!/usr/bin/env python3

import boxx
import numpy as np


class RawToRgbUint8:
    def __init__(self, bit=12, poww=1, partten="GBRG"):
        self.bit = bit
        self.poww = poww
        self.partten = partten

    def __call__(self, raw):
        norma_raw = raw / 2 ** self.bit

        if self.poww != 1:
            pow_func = self.pow_func_for_uint8()
            norma_raw = pow_func(norma_raw)

        rgb = (self.demosaicing(norma_raw)).clip(0, 1 - 1 / 2 ** self.bit)
        rgb = np.uint8(rgb * 256)
        return rgb

    def demosaicing(self, raw):
        import colour_demosaicing

        demosaicing_func = colour_demosaicing.demosaicing_CFA_Bayer_DDFAPD
        demosaicing_func = colour_demosaicing.demosaicing_CFA_Bayer_Malvar2004
        # demosaicing_func = colour_demosaicing.demosaicing_CFA_Bayer_bilinear
        rgb = demosaicing_func(raw, self.partten)
        return rgb

    def pow_func_for_uint8(self):
        """
        pow 改进
        改进的动机: 充分利用 uint8 来容纳细节, 即使 1/2^12 的亮度值在映射后不会超过 1/2^8
        """
        poww = self.poww
        bit = self.bit

        x0 = (2 ** (bit - 8) / poww) ** (1 / (poww - 1))  # where_dx_equl_scale
        y0 = x0 ** poww
        remap = lambda raw: (((raw) * (1 - x0) + x0) ** poww - y0) / (1 - y0)
        return (
            lambda raw: np.uint8(remap(raw / 2 ** bit) * 256)
            if np.issubdtype(raw.dtype, np.integer)
            else remap(raw)
        )


if __name__ == "__main__":
    from boxx import *

    raw_png = "/home/dl/junk/raw_img/raw12-test3.png"
    raw = boxx.imread(raw_png)

    with boxx.timeit("rgb1"):
        rgb1 = RawToRgbUint8()(raw)
    with boxx.timeit("rgb2"):
        rgb2 = RawToRgbUint8(poww=0.3)(raw)
    boxx.tree - [raw, rgb1, rgb2]

    boxx.shows([raw, rgb1, rgb2], png=True)
