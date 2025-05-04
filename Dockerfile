FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip openscad && \
    pip3 install flask
RUN apt-get install -y inkscape gerbv
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

RUN pip3 install dash

COPY . /app
WORKDIR /app

CMD ["python", "app.py"]
