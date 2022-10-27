import boxx, cv2
from hik_camera.hik_camera import HikCamera


class CvShow:
    destroyed = False

    def __init__(self):
        pass

    def __enter__(self):
        CvShow.destroyed = False
        self.get_key()
        return self

    def __exit__(*args):
        CvShow.destroyed = True
        cv2.destroyAllWindows()

    @staticmethod
    def imshow(rgb, window="default"):
        rgb = rgb[..., ::-1] if rgb.ndim == 3 and rgb.shape[-1] == 3 else rgb
        cv2.imshow(window, rgb)

    def get_key(self):
        key_idx = cv2.waitKey(1)
        if 0 < key_idx and key_idx < 256:
            return chr(key_idx)
        return key_idx

    def __next__(self):
        return self.get_key()

    def __iter__(self):
        return self


class Hik(HikCamera):
    def setting(self):
        # self.setitem("GevSCPD", 200)  # 包延时, 单位 ns, 防止丢包, 6 个百万像素相机推荐 15000
        # self.set_OptimalPacketSize()  # 最优包大小

        self.setitem("ExposureAuto", "Continuous")
        try:
            self.set_rgb()  # 取 RGB 图
        except AssertionError:
            self.set_raw(12)
        pass


if __name__ == "__main__":
    from boxx import *

    dirr = "/tmp/hik_camera_collect"
    boxx.makedirs(dirr)
    ips = Hik.get_all_ips()
    print("All camera IP adresses:", ips)
    cams = Hik.get_all_cams()
    with cams, CvShow() as cv_show:
        for idx, key in enumerate(cv_show):
            if key == "q":
                break
            timestr = localTimeStr(1)
            for ip, cam in cams.items():
                img = cam.get_frame()
                if cam.is_raw:
                    img = cam.raw_to_uint8_rgb(img, poww=0.5)
                cv_show.imshow(img[::3, ::3], window=ip)
                if key == " ":
                    imgp = pathjoin(dirr, f"{timestr}~{ip}.jpg")
                    print("Save to", imgp)
                    boxx.imsave(imgp, img)
