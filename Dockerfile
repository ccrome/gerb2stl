FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y python3 python3-pip openscad && \
    pip3 install flask
RUN apt-get install -y inkscape gerbv

COPY . /app
WORKDIR /app

CMD ["python3", "app.py"]
