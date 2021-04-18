FROM  ubuntu

ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt update && \
    apt install -y unzip wget make g++

RUN wget https://download.hikvision.com/UploadFile/Soft/MVS/01%20Machine%20Vision/02%20Service%20Support/01%20Clients/MVS_Linux_STD_V2.1.0_201228.zip  \
    && unzip MVS_Linux_STD_V2.1.0_201228.zip \
    && dpkg -i MVS-2.1.0_x86_64_20201228.deb \
    && rm MVS*.deb MVS*.gz MVS*.zip

WORKDIR /opt/MVS/Samples/64/Trigger_Image




