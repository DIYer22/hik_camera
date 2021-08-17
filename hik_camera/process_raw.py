#!/usr/bin/env python3

import os
import boxx
import numpy as np


class RawToRgbUint8:
    def __init__(self, bit=12, poww=1, demosaicing_method="Malvar2004", pattern="GBRG"):
        self.bit = bit
        self.poww = poww
        self.demosaicing_method = demosaicing_method
        self.pattern = pattern

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

        demosaicing_funcs = dict(
            DDFAPD=colour_demosaicing.demosaicing_CFA_Bayer_DDFAPD,
            Menon2007=colour_demosaicing.demosaicing_CFA_Bayer_DDFAPD,
            Malvar2004=colour_demosaicing.demosaicing_CFA_Bayer_Malvar2004,
            bilinear=colour_demosaicing.demosaicing_CFA_Bayer_bilinear,
            simple=self.simple_demosaicing,
        )
        demosaicing_func = demosaicing_funcs[self.demosaicing_method]
        rgb = demosaicing_func(raw, self.pattern)
        return rgb

    def pow_func_for_uint8(self,):
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

    @staticmethod
    def simple_demosaicing(raw, pattern=None):
        return np.concatenate(
            [
                raw[1::2, ::2, None],
                (raw[::2, ::2, None] / 2 + raw[::2, ::2, None] / 2).astype(raw.dtype),
                raw[::2, 1::2, None],
            ],
            -1,
        )

    @staticmethod
    def test(raw=None):
        if raw is None:
            raw = boxx.imread("../tmp_BayerGB12Packed.png")
        with boxx.timeit("demosaicing_method: simple"):
            rgb1 = RawToRgbUint8(demosaicing_method="simple")(raw)
        with boxx.timeit("demosaicing_method: Malvar2004"):
            rgb2 = RawToRgbUint8()(raw)
        with boxx.timeit("demosaicing_method: Malvar2004 pow 0.3"):
            rgb3 = RawToRgbUint8(poww=0.3)(raw)
        imgs = boxx.tree / [boxx.norma(raw), rgb1, rgb2, rgb3]

        boxx.shows(imgs, png=True)
        boxx.g()


class DngFileformat:
    @staticmethod
    def save_dng(dng_path, raw, bit=12, pattern="GBRG", compress=False, Orientation=1):
        try:
            from pidng.core import RAW2DNG, DNGTags, Tag
        except ModuleNotFoundError as e:
            boxx.pred('Please install pidng by "pip install pidng"')
            raise e

        assert raw.dtype in (np.uint16, np.uint8)
        height, width = raw.shape

        CFAPattern = ["RGB".index(c) for c in pattern]

        # set DNG tags.
        t = DNGTags()
        t.set(Tag.ImageWidth, width)
        t.set(Tag.ImageLength, height)
        t.set(Tag.BitsPerSample, bit)
        t.set(Tag.CFARepeatPatternDim, [2, 2])
        t.set(Tag.CFAPattern, CFAPattern)
        t.set(Tag.BlackLevel, (4096 >> (16 - bit)))
        t.set(Tag.WhiteLevel, ((1 << bit) - 1))
        t.set(Tag.DNGVersion, [1, 4, 0, 0])
        t.set(Tag.PhotometricInterpretation, 32803)
        t.set(Tag.PreviewColorSpace, 2)
        t.set(Tag.Orientation, Orientation)

        RAW2DNG().convert(
            raw,
            tags=t,
            filename=boxx.filename(dng_path),
            path=boxx.dirname(dng_path) + "/",
            compress=compress,
        )
        # compress = True lossless for bayer, 29MB => 19 MB

    @staticmethod
    def read_dng(dng_path):
        import rawpy

        class RawPy_(rawpy.RawPy):
            def set_custom_attr(self):
                raw_obj = self
                raw_obj.pattern = "".join(
                    [chr(raw_obj.color_desc[i]) for i in raw_obj.raw_pattern.flatten()]
                )
                raw_obj.raw = raw_obj.raw_image
                raw_obj.bit = int(np.log2(raw_obj.white_level + 1))

            def demosaicing(self, poww=1, demosaicing_method="Malvar2004"):
                if "bit" not in self.__dict__:
                    self.set_custom_attr()
                return RawToRgbUint8(
                    bit=self.bit,
                    poww=poww,
                    demosaicing_method=demosaicing_method,
                    pattern=self.pattern,
                )(self.raw_image)

        raw_obj = RawPy_()
        raw_obj.open_file(dng_path)
        raw_obj.set_custom_attr()
        return raw_obj
        # return dict(raw=raw, pattern=pattern, bit=bit, raw_obj=raw_obj)

    @staticmethod
    def test(raw=None):
        if raw is None:
            raw = boxx.imread("../tmp_BayerGB12Packed.png")
        dngp = "../raw.dng"
        DngFileformat.save_dng(dngp, raw)
        re = DngFileformat.read_dng(dngp)
        raw2 = re.raw_image
        os.system(f"ls -lh {dngp}")
        boxx.showb(dngp)
        assert (raw2 == raw).all()
        boxx.g()


if __name__ == "__main__":
    from boxx import *

    raw_png = "../tmp_BayerGB12Packed.png"
    raw = boxx.imread(raw_png)

    DngFileformat.test(raw)
