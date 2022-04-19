#!/usr/bin/env python3
import boxx

if __name__ == "__main__":
    with boxx.inpkg():
        from .hik_camera import HikCamera

    print(" ".join(sorted(HikCamera._get_dev_info())))
