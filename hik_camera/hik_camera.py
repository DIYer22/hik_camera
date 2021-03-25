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


def get_host_ip_by_target_ip(target_ip):
    import socket

    return [
        (s.connect((target_ip, 80)), s.getsockname()[0], s.close())
        for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]
    ][0][1]


def get_setting_df():
    csv = boxx.pd.read_csv(__file__.replace("hik_camera.py", "MvCameraNode-CH.csv"))
    setting_df = boxx.pd.DataFrame()

    def to_key(key):
        if "[" in key:
            key = key[: key.index("[")]
        return key.strip()

    def get_depend(key):
        key = key.strip()
        if "[" in key:
            return key[key.index("[") + 1 : -1]
        return ""

    setting_df["key"] = csv[list(csv)[1]].map(to_key)
    setting_df["depend"] = csv[list(csv)[1]].map(get_depend)
    setting_df["dtype"] = csv[list(csv)[2]].map(lambda x: x.strip().lower())
    return setting_df


class HikCamera(hik.MvCamera):
    def __init__(self, ip=None, host_ip=None):
        super().__init__()
        if ip is None:
            return
            ip = self.get_all_ips()[0]
        if host_ip is None:
            host_ip = get_host_ip_by_target_ip(ip)
        self._ip = ip
        self.host_ip = host_ip
        # self.init_by_ip()
        self._init_by_enum()

    def setting(self):
        self.set_exposure(250000)
        self.setitem("ExposureAuto", "Continuous")
        # self.adjust_auto_exposure()

        self.pixel_format = "RGB8"
        self.pixel_format = "BayerGB12Packed"
        self.setitem("PixelFormat", self.pixel_format)

        self.setitem("GevSCPD", 2000)  # 包延时 ns

    def get_frame(self):
        stFrameInfo = self.stFrameInfo
        TIMEOUT_MS = 10000
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

    @classmethod
    def get_all_ips(cls):
        ip_to_dev_info = cls._get_dev_info()
        return sorted(ip_to_dev_info)

    @classmethod
    def get_cams(cls, ips=None):
        if ips is None:
            ips = cls.get_all_ips()
        else:
            ips = sorted(ips)
        cams = MultiHikCamera({ip: cls(ip) for ip in ips})
        return cams

    get_all_cams = get_cams

    def get_exposure(self):
        return self["ExposureTime"]

    def set_exposure(self, t):
        assert not self.MV_CC_SetEnumValueByString("ExposureAuto", "Off")
        assert not self.MV_CC_SetFloatValue("ExposureTime", t)

    def adjust_auto_exposure(self, t=2):
        boxx.sleep(0.1)
        try:
            self.MV_CC_StartGrabbing()
            print("before_exposure", self.get_exposure())
            boxx.sleep(t)
            print("after_exposure", self.get_exposure())
        finally:
            self.MV_CC_StopGrabbing()

    def get_shape(self):
        if not hasattr(self, "shape"):
            self.get_frame()
        return self.shape

    @property
    def is_raw(self):
        return "Bayer" in self.__dict__.get("pixel_format", "RGB8")

    @property
    def ip(self):
        if not hasattr(self, "_ip"):
            self._ip = self.getitem("GevCurrentIPAddress")
        return self._ip

    def raw_to_uint8_rgb(self, raw, poww=1, demosaicing_method="Malvar2004"):
        transfer_func = RawToRgbUint8(
            bit=self.bit, poww=poww, demosaicing_method=demosaicing_method
        )
        rgb = transfer_func(raw)
        return rgb

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

    def __exit__(self, *l):
        self.MV_CC_CloseDevice()

    def __del__(self):
        self.MV_CC_DestroyHandle()

    def MV_CC_CreateHandle(self, mvcc_dev_info):
        self.mvcc_dev_info = mvcc_dev_info
        self._ip = int_to_ip(mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp)
        assert not super().MV_CC_CreateHandle(mvcc_dev_info)

    high_speed_lock = Lock()
    setting_df = get_setting_df()

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

    def _init_by_spec_ip(self):
        """
        SDK 有 Bug, 调用完"枚举设备" 接口后, 再调用"无枚举连接相机" 会无法打开相机.
        暂时不能用
        """
        stDevInfo = hik.MV_CC_DEVICE_INFO()
        stGigEDev = hik.MV_GIGE_DEVICE_INFO()

        stGigEDev.nCurrentIp = ip_to_int(self.ip)
        stGigEDev.nNetExport = ip_to_int(self.host_ip)
        stDevInfo.nTLayerType = hik.MV_GIGE_DEVICE
        stDevInfo.SpecialInfo.stGigEInfo = stGigEDev
        assert not self.MV_CC_CreateHandle(stDevInfo)

    def _init_by_enum(self):
        stDevInfo = self._get_dev_info(self.ip)
        assert not self.MV_CC_CreateHandle(stDevInfo)

    @classmethod
    def _get_dev_info(cls, ip=None):
        if not hasattr(cls, "ip_to_dev_info"):
            ip_to_dev_info = {}
            deviceList = hik.MV_CC_DEVICE_INFO_LIST()
            tlayerType = hik.MV_GIGE_DEVICE  # | MV_USB_DEVICE
            assert not hik.MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
            for i in range(0, deviceList.nDeviceNum):
                mvcc_dev_info = cast(
                    deviceList.pDeviceInfo[i], POINTER(hik.MV_CC_DEVICE_INFO)
                ).contents
                _ip = int_to_ip(mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp)
                if mvcc_dev_info.nTLayerType == hik.MV_GIGE_DEVICE:
                    ip_to_dev_info[_ip] = mvcc_dev_info
            cls.ip_to_dev_info = {
                ip: ip_to_dev_info[ip] for ip in sorted(ip_to_dev_info)
            }
        if ip is None:
            return cls.ip_to_dev_info
        return cls.ip_to_dev_info[ip]


class MultiHikCamera(dict):
    def __getattr__(self, attr):
        if not callable(getattr(next(iter(self.values())), attr)):
            return {k: getattr(cam, attr) for k, v in self.items()}

        def func(*args, **kwargs):
            threads = []
            res = {}

            def _func(ip, cam):
                res[ip] = getattr(cam, attr)(*args, **kwargs)

            for ip, cam in self.items():
                thread = Timer(0, _func, (ip, cam))
                thread.start()
                threads.append(thread)
                # thread.join()
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

    cam = HikCamera(ip)
    with cam:
        for i in range(2):
            with boxx.timeit("cam.get_frame"):
                img = cam.get_frame()
                print("cam.get_exposure", cam["ExposureTime"])
        if cam.is_raw:
            rgbs = [
                cam.raw_to_uint8_rgb(img, poww=1),
                cam.raw_to_uint8_rgb(img, poww=0.3),
            ]
            boxx.show(rgbs)

    cams = HikCamera.get_all_cams()
    with cams:
        with boxx.timeit("cams.get_frame"):
            imgs = cams.get_frame()
        print("imgs = cams.get_frame()")
        boxx.tree(imgs)
