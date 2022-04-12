# FROM jjanzic/docker-python3-opencv:opencv-4.0.1
FROM diyer22/tiny_cv2:4.5.5-py38-ubuntu20.04

ENV LC_ALL=C.UTF-8 LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive TZ=Asia/Shanghai

RUN apt update && \
    apt install -y unzip wget make g++

RUN wget https://www.hikrobotics.com/cn2/source/support/software/MVS_STD_GML_V2.1.1_211224.zip  \
    && unzip MVS_STD_GML_V2.1.1_211224.zip \
    && dpkg -i MVS-2.1.1_x86_64_20211224.deb \
    && rm MVS*.deb MVS*.gz MVS*.zip

RUN apt install -y net-tools iputils-ping traceroute  

# RUN ln -sf `which python3` /usr/bin/python && ln -sf `which pip3` /usr/bin/pip
RUN pip install --no-cache-dir -U pip wheel setuptools
RUN pip install --no-cache-dir boxx process_raw

ENV MVCAM_COMMON_RUNENV=/opt/MVS/lib LD_LIBRARY_PATH=/opt/MVS/lib/64:/opt/MVS/lib/32:$LD_LIBRARY_PATH PYTHONPATH=/hik_camera:$PYTHONPATH

COPY . /hik_camera
WORKDIR /hik_camera
RUN pip install --no-cache-dir -r requirements.txt

CMD python -m hik_camera.hik_camera

# WORKDIR /opt/MVS/Samples/64/Trigger_Image

# docker build -t ylmegvii/hik_camera ./;docker run --net=host -v /tmp:/tmp -it ylmegvii/hik_camera;

# docker build -t armharbor-dev-r.megvii-demo.com/library/hik_camera ./;docker run --net=host -v /tmp:/tmp -it armharbor-dev-r.megvii-demo.com/library/hik_camera;

