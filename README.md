# 海康 GigE Vision 网口工业相机 Python 控制库
使用 Pythonic 风格封装海康网口工业相机 Python SDK, 灵活易用, 方便集成. 

## ▮ 特性 Features
- **易用**的 Pythonic API:
   - 采用面向对象封装, 方便多相机管理
   - 支持 `with` 语法来调用: `with HikCamera() as cam:`
   - 简洁直观的控制语法: `cam["ExposureTime"]=100000`, `print(cam["ExposureTime"])`
- **鲁棒(robust)**: 遇到错误, 会自动 reset 相机并 retry
   - 接口为: `cams.robust_get_frame()`
- 支持获得/处理/存取 **raw 图**, 并保存为 **`.dng` 格式**
   - Example 见 [./test/test_raw.py](./test/test_raw.py)
- 支持每隔一定时间自动拍一次照片来调整自动曝光, 以防止太久没触发拍照, 导致曝光失效
   - Example 见 [./test/test_continuous_adjust_exposure.py](./test/test_continuous_adjust_exposure.py)
- 支持 **Windows/Linux** 系统, 有编译好的 **Docker 镜像** (`diyer22/hik_camera`)
- 支持 CS/CU/CE/CA/CH 系列的 GigE Vision 网口工业相机 
- 方便封装为 ROS 节点

## ▮ 安装 Install
- Docker 方案:
   - `docker run --net=host -v /tmp:/tmp -it diyer22/hik_camera`
- 手动安装方案:
   1. 安装官方驱动: 在[海康机器人官网](https://www.hikrobotics.com/cn/machinevision/service/download)下载安装对应系统的 “机器视觉工业相机客户端 MVS SDK”
      - 官网下载需要注册, 也可以在 [Dockerfile](Dockerfile) 里面找到 Linux 版的下载链接
   2. `pip install hik_camera`
   3. 若遇到问题, 可以参考 [Dockerfile](Dockerfile), 一步一步手动安装
- 验证: 接入相机, 验证 hik_camera 是否安装成功:
```bash
$ python -m hik_camera.hik_camera

All camera IP adresses: ['10.101.68.102', '10.101.68.103']
Saveing image to: /tmp/10.101.68.102.jpg
"cam.get_frame" spend time: 0.072249
----------------------------------------
imgs = cams.robust_get_frame()
└── /: dict  2
    ├── 10.101.68.102: (3036, 4024, 3)uint8
    └── 10.101.68.103: (3036, 4024, 3)uint8
"cams.get_frame" spend time: 0.700901
```

## ▮ 用法 Usage
### 图像采集 Demo
```bash
python -m hik_camera.collect_img
```
- 运行后会弹出 opencv 窗口显示相机图像流, 按 `"空格"` 键拍照, `Q` 键退出
- 采图 demo 源代码在 [hik_camera/collect_img.py](hik_camera/collect_img.py)

### Python 接口
```Python
from hik_camera import HikCamera
ips = HikCamera.get_all_ips()
print("All camera IP adresses:", ips)
ip = ips[0]
cam = HikCamera(ip)
with cam:  # 用 with 的上下文的方式来 OpenDevice
   cam["ExposureAuto"] = "Off"  # 配置参数和海康官方 API 一致
   cam["ExposureTime"] = 50000  # 单位 ns
   rgb = cam.robust_get_frame()  # rgb's shape is np.uint8(h, w, 3)
   print("Saveing image to:", cam.save(rgb, ip + ".jpg"))
```
- 更全面的 Example 见 [hik_camera/hik_camera.py](hik_camera/hik_camera.py) 最底部的 "\_\_main\_\_" 代码
- 更多相机参数配置示例(曝光/Gain/PixelFormat等)见 [hik_camera/hik_camera.py](hik_camera/hik_camera.py#L91) 中, `HikCamera.setting()` 的注释
- 海康官方的配置项列表: [MvCameraNode-CH.csv](hik_camera/MvCameraNode-CH.csv)
- 推荐通过继承 `HikCamera` 类, 并 override setting 函数来配置相机参数, 例子: [hik_camera/collect_img.py](hik_camera/collect_img.py)
