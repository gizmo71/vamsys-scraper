FROM python:3

WORKDIR /usr/src/app

RUN apt-get update -y
RUN apt update -y
#RUN apt install -y chromium
RUN apt install -y firefox-esr
RUN pip3 install --upgrade pip
RUN pip3 install selenium blinker==1.7.0 selenium-wire webdriver-manager geopy lxml unidecode regex elementpath

VOLUME /data
VOLUME /pages

WORKDIR /data
