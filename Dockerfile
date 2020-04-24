FROM python:3.7-alpine
MAINTAINER Mateusz Plinta <matplinta@gmail.com>

COPY parser.py /
RUN chmod +x /parser.py
