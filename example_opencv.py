from hik_camera.hik_camera import HikCamera

import cv2

ips = HikCamera.get_all_ips()

print("All camera IP adresses:", ips)
ip = ips[0]

cam = HikCamera(ip=ip)

with cam:
    cam["ExposureAuto"] = "Off"
    cam["ExposureTime"] = 50000

    while True:
        rgb = cam.robust_get_frame()
        cv2.imshow("rgb", rgb)
        cv2.waitKey(1)
        # print("Saving image to:", cam.save(rgb, ip + ".jpg"))