FROM  ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt update && \
    apt install -y unzip wget make g++

RUN apt install -y python3 python3-pip vim
RUN ln -sf `which python3` /usr/bin/python && ln -sf `which pip3` /usr/bin/pip

RUN wget https://www.hikrobotics.com/cn2/source/support/client/MVS_Linux_STD_V2.1.0_201228.zip  \
    && unzip MVS_Linux_STD_V2.1.0_201228.zip \
    && dpkg -i MVS-2.1.0_x86_64_20201228.deb \
    && rm MVS*.deb MVS*.gz MVS*.zip

ENV MVCAM_COMMON_RUNENV /opt/MVS/lib
ENV LD_LIBRARY_PATH /opt/MVS/lib/64:/opt/MVS/lib/32:$LD_LIBRARY_PATH

RUN pip install --no-cache-dir boxx
RUN apt install -y git
RUN apt install -y net-tools iputils-ping traceroute  

COPY . /hik_camera
WORKDIR /hik_camera
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH /hik_camera:$PYTHONPATH



CMD python -m hik_camera.hik_camera

# WORKDIR /opt/MVS/Samples/64/Trigger_Image

# docker build -t ylmegvii/hik_camera ./;docker run --net=host -v /tmp:/tmp -it ylmegvii/hik_camera;

