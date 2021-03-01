#!/usr/bin/env python3

import boxx
import numpy as np
from threading import Lock, Timer
import ctypes
from ctypes import byref, POINTER, cast, sizeof, memset

with boxx.impt("/opt/MVS/Samples/64/Python/MvImport"):
    import MvCameraControl_class as hik


int_to_ip = (
    lambda i: f"{(i & 0xff000000) >> 24}.{(i & 0x00ff0000) >> 16}.{(i & 0x0000ff00) >> 8}.{i & 0x000000ff}"
)
ip_to_int = lambda ip: sum(
    [int(s) << shift for s, shift in zip(ip.split("."), [24, 16, 8, 0])]
)


class HikCamera(hik.MvCamera):
    high_speed_lock = Lock()

    def get_frame(self):
        stFrameInfo = self.stFrameInfo
        TIMEOUT_MS = 10000
        with self.high_speed_lock:
            try:
                self.MV_CC_StartGrabbing()
                assert not self.MV_CC_GetOneFrameTimeout(
                    byref(self.data_buf), self.nPayloadSize, stFrameInfo, TIMEOUT_MS
                )

            finally:
                self.MV_CC_StopGrabbing()
                pass
            h, w = stFrameInfo.nHeight, stFrameInfo.nWidth
            self.shape = (h, w, self.nPayloadSize // h // w)
            img = np.array(self.data_buf).copy().reshape(*self.shape)
            return img

    def adjust_auto_exposure(self, t=2):
        boxx.sleep(0.1)
        try:
            self.MV_CC_StartGrabbing()
            print("before_exposure", self.get_exposure())
            boxx.sleep(t)
            print("after_exposure", self.get_exposure())
        finally:
            self.MV_CC_StopGrabbing()

    def setting(self):
        assert not self.MV_CC_SetEnumValue("PixelFormat", 0x02180014)

        # self.adjust_auto_exposure()
        assert not self.MV_CC_SetEnumValueByString("ExposureAuto", "Off")
        assert not self.MV_CC_SetFloatValue("ExposureTime", 250000)
        assert not self.MV_CC_SetEnumValueByString("ExposureAuto", "Continuous")

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
        t = ctypes.c_float()
        self.MV_CC_GetFloatValue("ExposureTime", t)
        return t.value


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
        boxx.tree - imgs

        cam = cams.get("10.9.5.102", ip)
        for i in range(3):
            with boxx.timeit("cam.get_frame"):
                img = cam.get_frame()
                print("cam.get_exposure", cam.get_exposure())
            boxx.show - img
