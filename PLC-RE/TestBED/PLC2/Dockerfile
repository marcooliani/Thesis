FROM ubuntu:18.04

USER root
WORKDIR /root/
RUN apt-get update && \
    apt-get -y install git python-pip autoconf bison build-essential pkg-config bison flex autoconf automake libtool make git python2.7 python-pip sqlite3 cmake sudo
RUN pip install flask flask-login pyserial pymodbus

WORKDIR /home/
RUN git clone https://github.com/thiagoralves/OpenPLC_v3.git
WORKDIR /home/OpenPLC_v3/
RUN sudo ./install.sh linux

RUN mkdir /home/OpenPLC_v3/scripts

#COPY mbconfig.cfg /home/OpenPLC_v3/scripts

COPY run.sh /home/OpenPLC_v3/
RUN sudo chmod +x run.sh
COPY PLC2.st /home/OpenPLC_v3/scripts


EXPOSE 502
EXPOSE 6668/udp
EXPOSE 8080

CMD ["/home/OpenPLC_v3/run.sh"]

