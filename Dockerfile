FROM python:3.7-alpine
MAINTAINER Mateusz Plinta <matplinta@gmail.com>

RUN apk --no-cache add bash 
COPY parser.py /
RUN chmod +x /parser.py
