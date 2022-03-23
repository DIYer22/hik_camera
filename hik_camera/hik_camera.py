#!/usr/bin/env python3

import boxx
from boxx import *

import os
import time
import ctypes
import numpy as np
from threading import Lock, Thread
from ctypes import byref, POINTER, cast, sizeof, memset

with boxx.impt("/opt/MVS/Samples/64/Python/MvImport"), boxx.impt(
    r"C:\Program Files (x86)\MVS\Development\Samples\Python\MvImport"
):
    import MvCameraControl_class as hik

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
    continuous_adjust_exposure_cams = {}
    _continuous_adjust_exposure_thread_on = False

    def __init__(self, ip=None, host_ip=None):
        super().__init__()
        self.lock = Lock()
        self.TIMEOUT_MS = 40000
        if ip is None:
            ip = self.get_all_ips()[0]
        if host_ip is None:
            host_ip = get_host_ip_by_target_ip(ip)
        self._ip = ip
        self.host_ip = host_ip
        self._init()
        self.is_open = False
        self.last_time_get_frame = 0

    def _init(self):
        # self._init_by_spec_ip()
        self._init_by_enum()

    def setting(self):
        # self.setitem("GevSCPD", 200)  # 包延时, 单位 ns, 防止丢包, 6 个百万像素相机推荐 15000
        # self.set_OptimalPacketSize()  # 最优包大小

        self.set_rgb()  # 取 RGB 图
        # self.set_raw() # 取 raw 图

        # 手动曝光, 单位秒
        # self.set_exposure_by_second(0.1)

        # 设置为自动曝光
        self.setitem("ExposureAuto", "Continuous")

        # 每隔 120s 拍一次照片来调整自动曝光, 以防止太久没调整自动曝光, 导致曝光失效
        # self.continuous_adjust_exposure(120)

        # 初始化时候, 花两秒来调整自动曝光
        # self.adjust_auto_exposure(2)

    def _get_one_frame_to_buf(self):
        with self.lock:
            assert not self.MV_CC_SetCommandValue("TriggerSoftware")
            assert not self.MV_CC_GetOneFrameTimeout(
                byref(self.data_buf),
                self.nPayloadSize,
                self.stFrameInfo,
                self.TIMEOUT_MS,
            ), self.ip
        self.last_time_get_frame = time.time()

    def get_frame(self):
        stFrameInfo = self.stFrameInfo
        self._get_one_frame_to_buf()

        h, w = stFrameInfo.nHeight, stFrameInfo.nWidth
        self.bit = bit = self.nPayloadSize * 8 // h // w
        self.shape = h, w
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

    def robust_get_frame(self):
        """
        遇到错误, 会自动 reset device 并 retry 的 get frame
        - 支持断网重连后继续工作
        """
        try:
            return self.get_frame()
        except Exception as e:
            print(boxx.prettyFrameLocation())
            boxx.pred(type(e).__name__, e)
            try:
                self.MV_CC_SetCommandValue("DeviceReset")
            except:
                pass
            self.waite()
            self._init()
            self.__enter__()
            return self.get_frame()

    def _ping(self):
        # TODO support Windows
        return not os.system("ping -c 1 -w 1 " + self.ip + " > /dev/null")

    def waite(self, timeout=20):
        begin = time.time()
        while not self._ping():
            boxx.sleep(0.1)
            if time.time() - begin > timeout:
                raise TimeoutError(f"Lost connection to {self.ip} for {timeout}s!")

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

    def set_rgb(self):
        self.pixel_format = "RGB8Packed"
        self.setitem("PixelFormat", self.pixel_format)

    def set_raw(self, bit=12, packed=True):
        if packed:
            packed = bit % 8
        pixel_formats = [
            "Bayer%s%d%s" % (color_format, bit, "Packed" if packed else "")
            for color_format in ["GB", "GR", "RG", "BG"]
        ]
        for pixel_format in pixel_formats:
            try:
                self.pixel_format = pixel_format
                self.setitem("PixelFormat", self.pixel_format)
                return
            except AssertionError:
                pass
        raise NotImplementedError(
            f"This camera's pixel_format not support any {bit}bit of {pixel_formats}"
        )

    def get_exposure(self):
        return self["ExposureTime"]

    def set_exposure(self, t):
        assert not self.MV_CC_SetEnumValueByString("ExposureAuto", "Off")
        assert not self.MV_CC_SetFloatValue("ExposureTime", t)

    def get_exposure_by_second(self):
        return self.get_exposure() * 1e-6

    def set_exposure_by_second(self, t):
        self.set_exposure(t / 1e-6)

    def adjust_auto_exposure(self, t=2):
        boxx.sleep(0.1)
        try:
            self.MV_CC_StartGrabbing()
            print("before_exposure", self.get_exposure())
            boxx.sleep(t)
            print("after_exposure", self.get_exposure())
        finally:
            self.MV_CC_StopGrabbing()

    def continuous_adjust_exposure(self, interval=60):
        """ 
        触发模式下, 会额外起一条线程, 每隔大致 interval 秒, 拍一次照
        以调整自动曝光. 该功能会避免任意两次拍照的时间间隔过小, 而导致网络堵塞
        """
        self.setitem("ExposureAuto", "Continuous")
        self.interval = interval
        HikCamera.continuous_adjust_exposure_cams[self.ip] = self
        if not HikCamera._continuous_adjust_exposure_thread_on:
            HikCamera._continuous_adjust_exposure_thread_on = True
            boxx.setTimeout(self._continuous_adjust_exposure_thread, interval)

    @classmethod
    def _continuous_adjust_exposure_thread(cls):
        cams = [
            cam for cam in cls.continuous_adjust_exposure_cams.values() if cam.is_open
        ]
        if not len(cams):
            cls._continuous_adjust_exposure_thread_on = False
            return
        now = time.time()
        last_get_frame = max([cam.last_time_get_frame for cam in cams])

        cam = sorted(
            cams, key=lambda cam: now - cam.last_time_get_frame - cam.interval
        )[-1]
        # 避免任意两次拍照的时间间隔过小, 而导致网络堵塞
        min_get_frame_gap = max(cam.interval / len(cams) / 4, 1)
        if (
            now - cam.last_time_get_frame >= cam.interval
            and now - last_get_frame >= min_get_frame_gap
        ):
            # boxx.pred("adjust", cam.ip, time.time())
            try:
                cam._get_one_frame_to_buf()
            except Exception as e:
                boxx.pred(type(e).__name__, e)
        boxx.setTimeout(cls._continuous_adjust_exposure_thread, 1)

    def get_shape(self):
        if not hasattr(self, "shape"):
            self.robust_get_frame()
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
        from process_raw import RawToRgbUint8

        transfer_func = RawToRgbUint8(
            bit=self.bit,
            poww=poww,
            demosaicing_method=demosaicing_method,
            pattern=self.get_bayer_pattern(),
        )
        rgb = transfer_func(raw)
        return rgb

    def save_raw(self, raw, dng_path, compress=False):
        from process_raw import DngFile

        pattern = self.get_bayer_pattern()
        DngFile.save(dng_path, raw, bit=self.bit, pattern=pattern, compress=compress)
        return dng_path

    def save(self, img, path=""):
        if self.is_raw:
            return self.save_raw(img, path or f"/tmp/{self.ip}.dng")
        path = path or f"/tmp/{self.ip}.jpg"
        boxx.imsave(path, img)
        return path

    def get_bayer_pattern(self):
        assert self.is_raw
        if "BayerGB" in self.pixel_format:
            return "GBRG"
        elif "BayerGR" in self.pixel_format:
            return "GRBG"
        elif "BayerRG" in self.pixel_format:
            return "RGGB"
        elif "BayerBG" in self.pixel_format:
            return "BGGR"
        raise NotImplementedError(self.pixel_format)

    def __enter__(self):
        assert not self.MV_CC_OpenDevice(hik.MV_ACCESS_Exclusive, 0)

        # TODO rember setting
        self.setitem("TriggerMode", hik.MV_TRIGGER_MODE_ON)
        self.setitem("TriggerSource", hik.MV_TRIGGER_SOURCE_SOFTWARE)
        self.setitem("AcquisitionFrameRateEnable", False)
        self.setting()

        stParam = hik.MVCC_INTVALUE()
        memset(byref(stParam), 0, sizeof(hik.MVCC_INTVALUE))

        assert not self.MV_CC_GetIntValue("PayloadSize", stParam)
        self.nPayloadSize = stParam.nCurValue
        self.data_buf = (ctypes.c_ubyte * self.nPayloadSize)()

        self.stFrameInfo = hik.MV_FRAME_OUT_INFO_EX()
        memset(byref(self.stFrameInfo), 0, sizeof(self.stFrameInfo))

        assert not self.MV_CC_StartGrabbing()
        self.is_open = True
        return self

    def set_OptimalPacketSize(self):
        # ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
        # print("GevSCPSPacketSize", self["GevSCPSPacketSize"])
        with self.high_speed_lock:
            nPacketSize = self.MV_CC_GetOptimalPacketSize()
        assert nPacketSize
        assert not self.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)

    def __exit__(self, *l):
        self.setitem("TriggerMode", hik.MV_TRIGGER_MODE_OFF)
        self.setitem("AcquisitionFrameRateEnable", True)
        assert not self.MV_CC_StopGrabbing()
        self.MV_CC_CloseDevice()

        self.is_open = False

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
        # print(get_func, value)
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

    @classmethod
    def get_cam(cls):
        ips = cls.get_all_ips()
        cam = cls(ips[0])
        return cam


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
                thread = Thread(target=_func, args=(ip, cam))
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

    ips = HikCamera.get_all_ips()
    print("All camera IP adresses:", ips)
    ip = ips[0]
    cam = HikCamera(ip)
    # cam.test_raw()
    with cam, boxx.timeit("cam.get_frame"):
        img = cam.robust_get_frame()
        print("Saveing image to:", cam.save(img))

    print("-" * 40)

    cams = HikCamera.get_all_cams()
    with cams, boxx.timeit("cams.get_frame"):
        imgs = cams.robust_get_frame()
        print("imgs = cams.robust_get_frame()")
        boxx.tree(imgs)
