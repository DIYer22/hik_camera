# 海康网口相机控制库
封装海康网口相机 SDK, 使得易于使用. 支持 Linux 和 Windows

## 特性
- 易于使用的接口
- **鲁棒**: 遇到错误, 会自动 reset 相机并 retry
   - 接口为: `cams.robust_get_frame()`
- 支持获得/处理/存取 raw 图, 保存为 dng 格式
   - Example 见 [./test/test_raw.py](./test/test_raw.py)
- 支持每隔一定时间拍一次照片来调整自动曝光, 以防止太久没调整自动曝光, 导致曝光失效
   - Example 见 [./test/test_continuous_adjust_exposure.py](./test/test_continuous_adjust_exposure.py)



## 安装
1. 可直接使用 docker
   - `docker run --net=host -v /tmp:/tmp -it armharbor-dev-r.megvii-demo.com/library/hik_camera`
2. 或者参考 [Dockerfile](Dockerfile), 一步一步手动安装

## Example
Example 见 [./hik_camera/hik_camera.py](./hik_camera/hik_camera.py) 的 "\_\_main\_\_"

详细的配置说明见 [./hik_camera/hik_camera.py](./hik_camera/hik_camera.py#L78) 中, `HikCamera.setting()` 的注释

```bash
# 快速测试
python -m hik_camera.hik_camera
```
