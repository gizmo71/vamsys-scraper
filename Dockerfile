FROM debian

RUN apt update -y
RUN apt install -y python3 python3-pip chromium
RUN pip install selenium==4.4.3 selenium-wire webdriver-manager geopy lxml

VOLUME /data

WORKDIR /data
