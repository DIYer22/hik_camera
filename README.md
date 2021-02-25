# 海康相机sdk

```bash
# 快速测试
python -m hik_camera.hik_camera
```



## Tips
1. sdk目录位于/opt/MVS
2. /opt/MVS/doc包含详细sdk接口说明
   .xlsx为相机可选参数说明
3. /opt/MVS/doc/samples包含代码示例
4. 例如python/MvImport/MvCameraControl_class.py包含Python可调class.(根据需要可按照c代码重构).
5. 相机只缓存设置相关内容.图片缓存在MVS的SDK中,代码运行需要开辟内存空间,注意调用后释放,避免内存泄露.
6. 使用 `./tools/network.py` 监控网口流量.可选参数:
   + 刷新时间time.
   + 流量单位b,B,k,K,m,M,g,G


## TODO
- [ ] 异常重置相机
   - self.MV_CC_SetCommandValue("DeviceReset")
