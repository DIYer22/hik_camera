# 海康网口工业相机控制库
使用 Pythonic 风格封装海康网口工业相机 Python SDK, 易于使用, 方便管理. 

## ▮ 安装
1. 可直接使用 docker
   - `docker run --net=host -v /tmp:/tmp -it ylmegvii/hik_camera`
2. 或者参考 [Dockerfile](Dockerfile), 一步一步手动安装, 主要为两步:
   1. 下载安装[海康官方 MVS SDK](https://www.hikrobotics.com/cn/machinevision/service/download)(官网下载需要注册, 也可以在 dockerfile 里面找下载链接)
   2. `pip install hik_camera`


## ▮ Example
Example 见 [./hik_camera/hik_camera.py](./hik_camera/hik_camera.py) 的 "\_\_main\_\_"

详细的配置说明见 [./hik_camera/hik_camera.py](./hik_camera/hik_camera.py#L91) 中, `HikCamera.setting()` 的注释

## ▮ 特性
- 支持 Windows/Linux 系统, 有编译好的 docker 镜像
- 支持 CE/CU/CS/CA/CH 系列的网口相机 
- 易于使用的 Pythonic 接口
- **鲁棒**: 遇到错误, 会自动 reset 相机并 retry
   - 接口为: `cams.robust_get_frame()`
- 支持获得/处理/存取 raw 图, 保存为 dng 格式
   - Example 见 [./test/test_raw.py](./test/test_raw.py)
- 支持每隔一定时间拍一次照片来调整自动曝光, 以防止太久没调整自动曝光, 导致曝光失效
   - Example 见 [./test/test_continuous_adjust_exposure.py](./test/test_continuous_adjust_exposure.py)

```bash
# 快速测试
python -m hik_camera.hik_camera
```
