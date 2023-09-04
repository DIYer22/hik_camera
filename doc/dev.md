# 开发文档

## Tips
1. SDK目录位于 `/opt/MVS`
2. `/opt/MVS/doc`包含详细SDK接口说明
   .xlsx为相机可选参数说明
3. `/opt/MVS/doc/samples`包含代码示例
4. 例如  `python/MvImport/MvCameraControl_class.py` 包含Python可调class.(根据需要可按照c代码重构).
5. 相机只缓存设置相关内容.图片缓存在MVS的SDK中,代码运行需要开辟内存空间,注意调用后释放,避免内存泄露.
6. 使用 `python -m hik_camera.bandwidth` 监控网口流量


## TODO
- [x] python setup.py install 找不到 xls
- [x] 异常重置相机
   - self.MV_CC_SetCommandValue("DeviceReset")
- [x] 自研快速自动曝光算法?
   - 自动曝光 RoI
- [x] 了解 rawpy 的 rgb=re['raw_obj'].postprocess(), 尝试加速转换为 RGB
   - 没有比采集图像显著的快
- [x] ~~要不要考虑多帧融合 HDR?~~
   - 12bit raw 图能同时获得亮暗细节
- [ ] 跑通 ParametrizeCamera_LoadAndSave.py MV_CC_FeatureSave
- [ ] DNG 支持正确的 meta 信息


## 图片存储空间
```bash
# 对于 12 bit 的 raw12 图, 其不同存储形式的占用空间
>>> tree-raw12
└── /: (3036, 4024)uint16

412K	./color.jpg  # uint8
8.7M	./color.png  # uint8
14M	./raw.png    # uint16
15M	./uint16.npz
18M	./int32.npz
24M	./uint16.pkl
47M	./int32.pkl
```

