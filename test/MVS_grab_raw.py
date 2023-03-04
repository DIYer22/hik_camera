# -- coding: utf-8 --
"""
Created on 2021.01.03
hik grab images

@author: yanziwei
"""
import base64
import os
import queue
import sys
import termios
import threading
import time
import urllib
from ctypes import *

import cv2
import matplotlib.pyplot as plt
import numpy as np

import tqdm
from boxx import *
from PIL import Image
from skimage import io

sys.path.append("/opt/MVS/Samples/64/Python/MvImport")
from MvCameraControl_class import *

g_bExit = False


class HikMvCamera:
    def __init__(self):

        # ch:创建相机实例 | en:Creat Camera Object
        self.nConnectionNum = self.find_device()
        self.cam = {}
        self.stParam = {}
        for i in range(self.nConnectionNum):
            self.cam[str(i)] = MvCamera()
            self.cam[str(i)] = self.create_cam(self.cam[str(i)], i)
            self.cam[str(i)], self.stParam[str(i)] = self.set_info(self.cam[str(i)])

    def set_info(self, cam):

        # ch:设置触发模式为off | en:Set trigger mode as off
        ret = cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
        if ret != 0:
            print("set trigger mode fail! ret[0x%x]" % ret)
            sys.exit()

        # #设置PixelFormat为RGB-8
        ret = cam.MV_CC_SetEnumValue("PixelFormat", 0x02180014)
        if ret != 0:
            print("set RBG8 fail! ret[0x%x]" % ret)
            sys.exit()

        # 设置ROI宽高
        # ret = cam.MV_CC_SetIntValue("Width", 5472) #5472
        # if ret != 0:
        #     print("set width fail! ret[0x%x]" % ret)
        #     sys.exit()
        # ret = cam.MV_CC_SetIntValue("Height", 3648) #3648
        # if ret != 0:
        #     print("set height fail! ret[0x%x]" % ret)
        #     sys.exit()
        # # 设置ROI偏移位置
        # ret = cam.MV_CC_SetIntValue("OffsetX", 2096) #2096
        # if ret != 0:
        #     print("set width fail! ret[0x%x]" % ret)
        #     sys.exit()
        # ret = cam.MV_CC_SetIntValue("OffsetY", 1184) #1184
        # if ret != 0:
        #     print("set height fail! ret[0x%x]" % ret)
        #     sys.exit()
        # 设置曝光
        ret = cam.MV_CC_SetFloatValue("ExposureTime", 250000)
        if ret != 0:
            print("set ExposureTime fail! ret[0x%x]" % ret)
            sys.exit()

        ret = cam.MV_CC_SetIntValue("GevSCPD", 1000)
        if ret != 0:
            print("set GevSCPD fail! ret[0x%x]" % ret)
            sys.exit()

        # 设置SDK图像缓存个数
        # cam.MV_CC_SetImageNodeNum(10)
        # ch:获取数据包大小 | en:Get payload size
        stParam = MVCC_INTVALUE()
        memset(byref(stParam), 0, 2 * sizeof(MVCC_INTVALUE))
        ret = cam.MV_CC_GetIntValue("PayloadSize", stParam)
        if ret != 0:
            print("get payload size fail! ret[0x%x]" % ret)
            sys.exit()

        return cam, stParam

    def find_device(self):
        # 创建相机
        # 获得版本号
        self.SDKVersion = MvCamera.MV_CC_GetSDKVersion()
        print("SDKVersion[0x%x] :v3.0" % self.SDKVersion)
        self.deviceList = MV_CC_DEVICE_INFO_LIST()
        self.tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
        tlayerType = self.tlayerType
        deviceList = self.deviceList
        # ch:枚举设备 | en:Enum device
        ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
        if ret != 0:
            print("enum devices fail! ret[0x%x]" % ret)
            sys.exit()

        if deviceList.nDeviceNum == 0:
            print("find no device!")
            sys.exit()

        print("Find %d devices!" % deviceList.nDeviceNum)
        for i in range(0, deviceList.nDeviceNum):
            mvcc_dev_info = cast(
                deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)
            ).contents
            if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
                print("\ngige device: [%d]" % i)
                strModeName = ""
                for per in mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName:
                    strModeName = strModeName + chr(per)
                print("device model name: %s" % strModeName)

                nip1 = (
                    mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xFF000000
                ) >> 24
                nip2 = (
                    mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00FF0000
                ) >> 16
                nip3 = (
                    mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000FF00
                ) >> 8
                nip4 = mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000FF
                print("current ip: %d.%d.%d.%d\n" % (nip1, nip2, nip3, nip4))

        return deviceList.nDeviceNum

    def create_cam(self, cam, nConnectionNum):

        deviceList = self.deviceList
        # ch:选择设备并创建句柄| en:Select device and create handle
        stDeviceList = cast(
            deviceList.pDeviceInfo[int(nConnectionNum)], POINTER(MV_CC_DEVICE_INFO)
        ).contents

        ret = cam.MV_CC_CreateHandle(stDeviceList)
        if ret != 0:
            print("create handle fail! ret[0x%x]" % ret)
            sys.exit()

        # ch:打开设备 | en:Open device
        ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            print("open device fail! ret[0x%x]" % ret)
            sys.exit()

        # ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
        if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
            nPacketSize = cam.MV_CC_GetOptimalPacketSize()
        if int(nPacketSize) > 0:
            ret = cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)
            if ret != 0:
                print("Warning: Set Packet Size fail! ret[0x%x]" % ret)
        else:
            print("Warning: Get Packet Size fail! ret[0x%x]" % nPacketSize)

        return cam

    def get_frame(self, img_root=None):

        now_time = time.time()
        local_time = time.localtime(now_time)
        dt = time.strftime("%y%m%d_%H%M%S_", local_time)

        for cam_id, cam in self.cam.items():
            ret = cam.MV_CC_StartGrabbing()
            if ret != 0:
                print("start grabbing fail! ret[0x%x]" % ret)
                sys.exit()
            print(cam_id)

            nPayloadSize = self.stParam[cam_id].nCurValue
            data_buf = (c_ubyte * nPayloadSize)()
            pData = byref(data_buf)
            # 获取帧信息结构体
            stFrameInfo = MV_FRAME_OUT_INFO_EX()

            # memset(byref(stFrameInfo), 0, 2*sizeof(stFrameInfo))

            img_save_name = img_root + dt + str(cam_id) + ".jpg"
            print(img_save_name)
            ret = cam.MV_CC_GetOneFrameTimeout(pData, nPayloadSize, stFrameInfo, 1000)
            # what-pData
            if ret == 0:
                # MV_Image_Undefined  = 0,
                #   MV_Image_Bmp        = 1, //BMP
                #   MV_Image_Jpeg       = 2, //JPEG
                #   MV_Image_Png        = 3, //PNG
                #   MV_Image_Tif        = 4, //TIF
                # 图片在pData._obj内,reshape即可获得
                # image = np.asarray(pData._obj)
                # image = image.reshape(
                # 	(stFrameInfo.nHeight, stFrameInfo.nWidth, 3)

                stConvertParam = MV_SAVE_IMAGE_PARAM_EX()
                stConvertParam.nWidth = stFrameInfo.nWidth
                stConvertParam.nHeight = stFrameInfo.nHeight
                stConvertParam.pData = data_buf
                stConvertParam.nDataLen = stFrameInfo.nFrameLen
                stConvertParam.enPixelType = stFrameInfo.enPixelType
                stConvertParam.nJpgQuality = 99  # range[50-99]
                stConvertParam.enImageType = MV_Image_Jpeg
                bmpsize = nPayloadSize
                stConvertParam.nBufferSize = bmpsize
                bmp_buf = (c_ubyte * bmpsize)()
                stConvertParam.pImageBuffer = bmp_buf
                ret = cam.MV_CC_SaveImageEx2(stConvertParam)
                if ret != 0:
                    print("save file executed failed0:! ret[0x%x]" % ret)
                    del data_buf
                    sys.exit()
                img_buff = (c_ubyte * stConvertParam.nImageLen)()
                memmove(
                    byref(img_buff),
                    stConvertParam.pImageBuffer,
                    stConvertParam.nImageLen,
                )
                with open(img_save_name, "wb+") as f:
                    f.write(img_buff)

            else:
                print("no data[0x%x]" % ret)

            ret = cam.MV_CC_StopGrabbing()
            if ret != 0:
                print("stop grabbing fail! ret[0x%x]" % ret)
                del data_buf
                sys.exit()

        return True

    def close_cam(self):
        for cam in self.cam.values():

            # ch:关闭设备 | Close device
            ret = cam.MV_CC_CloseDevice()
            if ret != 0:
                print("close deivce fail! ret[0x%x]" % ret)
                del data_buf
                sys.exit()

            # ch:销毁句柄 | Destroy handle
            ret = cam.MV_CC_DestroyHandle()
            if ret != 0:
                print("destroy handle fail! ret[0x%x]" % ret)
                del data_buf
                sys.exit()
        print("Stop grab image")
        # del data_buf


def press_any_key_exit():
    fd = sys.stdin.fileno()
    old_ttyinfo = termios.tcgetattr(fd)
    new_ttyinfo = old_ttyinfo[:]
    new_ttyinfo[3] &= ~termios.ICANON
    new_ttyinfo[3] &= ~termios.ECHO
    # sys.stdout.write(msg)
    # sys.stdout.flush()
    termios.tcsetattr(fd, termios.TCSANOW, new_ttyinfo)
    try:
        os.read(fd, 7)
    except:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old_ttyinfo)


def grab_img():
    cap = HikMvCamera()
    WINDOW_NAME = "hik detector"
    while True:
        img_root = "./grab_img/"
        if not os.path.exists(img_root):
            os.makedirs(img_root)
        press_any_key_exit()
        start_time = time.time()
        ret = cap.get_frame(img_root)
        print("run once time:" + str(time.time() - start_time))

    cap.stop_cam()


if __name__ == "__main__":
    # 打开巨帧模式,先ifconfig找到网卡名称(enp0s31f6),第一次开启需要输入密码
    os.system("sudo ifconfig enp0s31f6 mtu 9000")
    print("巨帧模式已开启!")
    grab_img()
