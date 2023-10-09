FROM python:3

WORKDIR /usr/src/app

RUN apt update -y
RUN apt install -y chromium
RUN pip install selenium==4.4.3 selenium-wire webdriver-manager geopy lxml unidecode

VOLUME /data
VOLUME /pages

WORKDIR /data
