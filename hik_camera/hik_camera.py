#!/usr/bin/env python3

import boxx
import numpy as np
from threading import Lock, Timer
import ctypes
from ctypes import byref, POINTER, cast, sizeof, memset

with boxx.impt("/opt/MVS/Samples/64/Python/MvImport"):
    import MvCameraControl_class as hik

with boxx.inpkg():
    from .process_raw import RawToRgbUint8

int_to_ip = (
    lambda i: f"{(i & 0xff000000) >> 24}.{(i & 0x00ff0000) >> 16}.{(i & 0x0000ff00) >> 8}.{i & 0x000000ff}"
)
ip_to_int = lambda ip: sum(
    [int(s) << shift for s, shift in zip(ip.split("."), [24, 16, 8, 0])]
)


class HikCamera(hik.MvCamera):
    def __init__(self):
        super().__init__()
        self.get_setting_df()

    high_speed_lock = Lock()

    def get_frame(self):
        stFrameInfo = self.stFrameInfo
        TIMEOUT_MS = 10000
        with self.high_speed_lock:
            try:
                self.MV_CC_StartGrabbing()
                assert not self.MV_CC_GetOneFrameTimeout(
                    byref(self.data_buf), self.nPayloadSize, stFrameInfo, TIMEOUT_MS
                ), self.ip

            finally:
                self.MV_CC_StopGrabbing()
                pass
            h, w = stFrameInfo.nHeight, stFrameInfo.nWidth
            self.bit = bit = self.nPayloadSize * 8 // h // w
            self.shape = (
                h,
                w,
            )
            if bit == 8:
                img = np.array(self.data_buf).copy().reshape(*self.shape)
            elif bit == 24:
                self.shape = (h, w, 3)
                img = np.array(self.data_buf).copy().reshape(*self.shape)
            elif bit == 16:
                raw = np.array(self.data_buf).copy().reshape(h, w, 2)
                img = raw[..., 1].astype(np.uint16) * 256 + raw[..., 0]
            elif bit == 12:
                self.shape = h, w
                arr = np.array(self.data_buf).copy().astype(np.uint16)
                arr2 = arr[1::3]
                arrl = (arr[::3] << 4) + ((arr2 & ~np.uint16(15)) >> 4)
                arrr = (arr[2::3] << 4) + (arr2 & np.uint16(15))

                img = np.concatenate([arrl[..., None], arrr[..., None]], 1).reshape(
                    self.shape
                )
            return img

    def get_setting_df(self):
        csv = boxx.pd.read_csv(__file__.replace("hik_camera.py", "MvCameraNode-CH.csv"))
        self.setting_df = boxx.pd.DataFrame()

        def to_key(key):
            if "[" in key:
                key = key[: key.index("[")]
            return key.strip()

        def get_depend(key):
            key = key.strip()
            if "[" in key:
                return key[key.index("[") + 1 : -1]
            return ""

        self.setting_df["key"] = csv[list(csv)[1]].map(to_key)
        self.setting_df["depend"] = csv[list(csv)[1]].map(get_depend)
        self.setting_df["dtype"] = csv[list(csv)[2]].map(lambda x: x.strip().lower())

    def getitem(self, key):
        df = self.setting_df
        dtype = df[df.key == key]["dtype"].iloc[0]
        if dtype == "iboolean":
            get_func = self.MV_CC_GetBoolValue
            value = ctypes.c_bool()
        if dtype == "icommand":
            get_func = self.MV_CC_GetCommandValue
        if dtype == "ienumeration":
            get_func = self.MV_CC_GetEnumValue
            value = ctypes.c_uint32()
        if dtype == "ifloat":
            get_func = self.MV_CC_GetFloatValue
            value = ctypes.c_float()
        if dtype == "iinteger":
            get_func = self.MV_CC_GetIntValue
            value = ctypes.c_int()
        if dtype == "istring":
            get_func = self.MV_CC_GetStringValue
            value = (ctypes.c_char * 50)()
        if dtype == "register":
            get_func = self.MV_CC_RegisterEventCallBackEx

        assert not get_func(
            key, value
        ), f"{get_func.__name__}('{key}', {value}) not return 0"
        return value.value

    def setitem(self, key, value):
        df = self.setting_df
        dtype = df[df.key == key]["dtype"].iloc[0]
        if dtype == "iboolean":
            set_func = self.MV_CC_SetBoolValue
        if dtype == "icommand":
            set_func = self.MV_CC_SetCommandValue
        if dtype == "ienumeration":
            if isinstance(value, str):
                set_func = self.MV_CC_SetEnumValueByString
            else:
                set_func = self.MV_CC_SetEnumValue
        if dtype == "ifloat":
            set_func = self.MV_CC_SetFloatValue
        if dtype == "iinteger":
            set_func = self.MV_CC_SetIntValue
        if dtype == "istring":
            set_func = self.MV_CC_SetStringValue
        if dtype == "register":
            set_func = self.MV_CC_RegisterEventCallBackEx

        assert not set_func(
            key, value
        ), f"{set_func.__name__}('{key}', {value}) not return 0"

    __getitem__ = getitem
    __setitem__ = setitem

    def adjust_auto_exposure(self, t=2):
        boxx.sleep(0.1)
        try:
            self.MV_CC_StartGrabbing()
            print("before_exposure", self.get_exposure())
            boxx.sleep(t)
            print("after_exposure", self.get_exposure())
        finally:
            self.MV_CC_StopGrabbing()

    pixel_format_values = {
        "RGB8": 0x02180014,
        "BayerGB8": 0x0108000A,
        "BayerGB12": 0x01100012,
        "BayerGB12Packed": 0x010C002C,
    }

    def setting(self):
        self.pixel_format = "RGB8"
        self.pixel_format = "BayerGB12Packed"
        self.setitem("PixelFormat", self.pixel_format_values[self.pixel_format])

        # self.adjust_auto_exposure()
        self.setitem("ExposureAuto", "Off")
        self.setitem("ExposureTime", 250000)
        self.setitem("ExposureAuto", "Continuous")

    def __enter__(self):
        assert not self.MV_CC_OpenDevice(hik.MV_ACCESS_Exclusive, 0)

        # assert not self.MV_CC_SetCommandValue("DeviceReset")
        # sleep(5)
        # assert not super().MV_CC_CreateHandle(self.mvcc_dev_info)
        # assert not self.MV_CC_OpenDevice(hik.MV_ACCESS_Exclusive, 0)

        self.setting()

        stParam = hik.MVCC_INTVALUE()
        memset(byref(stParam), 0, sizeof(hik.MVCC_INTVALUE))

        assert not self.MV_CC_GetIntValue("PayloadSize", stParam)
        self.nPayloadSize = stParam.nCurValue
        self.data_buf = (ctypes.c_ubyte * self.nPayloadSize)()

        # ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
        with self.high_speed_lock:
            nPacketSize = self.MV_CC_GetOptimalPacketSize()
        assert nPacketSize
        assert not self.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)

        self.stFrameInfo = hik.MV_FRAME_OUT_INFO_EX()
        memset(byref(self.stFrameInfo), 0, sizeof(self.stFrameInfo))

        assert not self.MV_CC_SetEnumValue("TriggerMode", hik.MV_TRIGGER_MODE_OFF)

        return self

    def get_shape(self):
        if not hasattr(self, "shape"):
            self.get_frame()
        return self.shape

    def __exit__(self, *l):
        self.MV_CC_CloseDevice()

    @staticmethod
    def get_all_ips():
        deviceList = hik.MV_CC_DEVICE_INFO_LIST()
        tlayerType = hik.MV_GIGE_DEVICE  # | MV_USB_DEVICE

        # ch:枚举设备 | en:Enum device
        assert not hik.MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
        ips = {}
        for i in range(0, deviceList.nDeviceNum):
            mvcc_dev_info = cast(
                deviceList.pDeviceInfo[i], POINTER(hik.MV_CC_DEVICE_INFO)
            ).contents
            if mvcc_dev_info.nTLayerType == hik.MV_GIGE_DEVICE:
                ips[int_to_ip(mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp)] = i
        return ips

    @classmethod
    def get_all_cams(cls):
        deviceList = hik.MV_CC_DEVICE_INFO_LIST()
        tlayerType = hik.MV_GIGE_DEVICE  # | MV_USB_DEVICE

        # ch:枚举设备 | en:Enum device
        assert not hik.MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
        cams = MultiHikCamera()
        for i in range(0, deviceList.nDeviceNum):
            mvcc_dev_info = cast(
                deviceList.pDeviceInfo[i], POINTER(hik.MV_CC_DEVICE_INFO)
            ).contents
            if mvcc_dev_info.nTLayerType == hik.MV_GIGE_DEVICE:
                cam = cls()
                assert not cam.MV_CC_CreateHandle(mvcc_dev_info)
                ip = cam.ip
                cams[ip] = cam
        cams = MultiHikCamera({ip: cams[ip] for ip in sorted(cams)})
        return cams

    def MV_CC_CreateHandle(self, mvcc_dev_info):
        self.mvcc_dev_info = mvcc_dev_info
        self.ip = int_to_ip(mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp)
        assert not super().MV_CC_CreateHandle(mvcc_dev_info)

    def __del__(self):
        self.MV_CC_DestroyHandle()

    def get_exposure(self):
        return self["ExposureTime"]

    def set_exposure(self, t):
        assert not self.MV_CC_SetEnumValueByString("ExposureAuto", "Off")
        assert not self.MV_CC_SetFloatValue("ExposureTime", t)

    def raw_to_uint8_rgb_with_pow(self, raw, poww=1):
        transfer_func = RawToRgbUint8(bit=self.bit, poww=poww)
        rgb = transfer_func(raw)
        return rgb

    @property
    def is_raw(self):
        return "Bayer" in self.__dict__.get("pixel_format", "RGB8")


class MultiHikCamera(dict):
    def __getattr__(self, attr):
        def func(*args, **kwargs):
            threads = []
            res = {}

            def _func(ip, cam):
                res[ip] = getattr(cam, attr)(*args, **kwargs)

            for ip, cam in self.items():
                thread = Timer(0, _func, (ip, cam))
                thread.start()
                threads.append(thread)
                thread.join()
            [thread.join() for thread in threads]
            res = {ip: res[ip] for ip in sorted(res)}
            return res

        return func

    def __enter__(self):
        self.__getattr__("__enter__")()
        return self

    def __exit__(self, *l):
        self.__getattr__("__exit__")(*l)


if __name__ == "__main__":
    from boxx import *

    ips = HikCamera.get_all_ips()
    print(ips)
    ip = list(ips)[0]
    cams = HikCamera.get_all_cams()
    with cams:
        imgs = cams.get_frame()
        print("imgs = cams.get_frame()")
        boxx.tree(imgs)

        cam = cams.get("10.9.5.102", cams[ip])
        for i in range(2):
            with boxx.timeit("cam.get_frame"):
                img = cam.get_frame()
                print("cam.get_exposure", cam["ExposureTime"])
            boxx.show(img)
        if cam.is_raw:
            rgbs = [
                cam.raw_to_uint8_rgb_with_pow(img, poww=1),
                cam.raw_to_uint8_rgb_with_pow(img, poww=0.3),
            ]
            boxx.show(rgbs)
