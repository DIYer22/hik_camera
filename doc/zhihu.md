https://www.zhihu.com/question/424627189/answer/3069074313


# 海康 GigE Vision 网口工业相机 Python 控制库 hik_camera

我从 2019 年开始从事工业视觉研发工作，在过去的四年里，我测试和使用过超过10种工业相机型号，并在不同项目中部署了50多台工业相机。

我主要使用海康网口工业相机, 由于海康官方的 Python API过于复杂和繁琐，因此我开发并封装了一个更加Pythonic的海康工业相机控制库：[hik_camera](https://github.com/DIYer22/hik_camera/)

该库具有以下特点:
- 模块化设计，极为简洁的 Pythonic API，便于进行业务研发且易于他人快速上手
- 将工业相机的各种知识和经验沉淀为代码
- 功能丰富， 支持 Windows 和 Linux 系统，并提供预编译好的 Docker 镜像


安装hik_camera有两种方式：
- Docker 方案
   - `docker run --net=host -v /tmp:/tmp -it diyer22/hik_camera`
- 手动安装方案
   1. 安装官方驱动: 在[海康机器人官网](https://www.hikrobotics.com/cn/machinevision/service/download)下载安装对应操作系统的 "机器视觉工业相机客户端 MVS SDK"
   2. `pip install hik_camera`

```bash
# 接入相机, 测试安装是否成功
python -m hik_camera.hik_camera
```

取图示例代码:  
```Python
from hik_camera import HikCamera
ips = HikCamera.get_all_ips()
print("All camera IP adresses:", ips)
ip = ips[0]
cam = HikCamera(ip)
with cam:
   img = cam.robust_get_frame()
   print("Saveing image to:", cam.save(img)) 
   # 图像将自动保存至临时文件夹下
```
更详细的示例以及相机参数配置方法（如曝光、增益、像素格式等），请访问 hik_camera GitHub 主页：

https://github.com/DIYer22/hik_camera/



