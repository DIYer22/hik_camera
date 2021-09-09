# 海康网口相机控制库
封装海康网口相机 SDK, 使得易于使用. 支持 Linux 和 Windows

## 特性
- **鲁棒**: 遇到错误, 会自动 reset 相机并 retry
   - 接口为: `cams.robust_get_frame()`
- 支持获得/处理/存取 raw 图
   - Example 见 [./hik_camera/hik_camera.py](./hik_camera/hik_camera.py) 的 `HikCamera.test_raw()`
- 易于使用的接口

## 安装
1. 可直接使用 docker
   - `docker run --net=host -v /tmp:/tmp -it armharbor-dev-r.megvii-demo.com/library/hik_camera`
2. 或者参考 [Dockerfile](Dockerfile), 一步一步手动安装

Example 见 [./hik_camera/hik_camera.py](./hik_camera/hik_camera.py) 的 "\_\_main\_\_"
```bash
# 快速测试
python -m hik_camera.hik_camera
```
