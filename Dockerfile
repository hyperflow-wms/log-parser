FROM python:3.7-alpine

COPY parser.py /
RUN chmod +x /parser.py