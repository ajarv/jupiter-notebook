FROM python:3.8-alpine3.11

RUN apk --update add --no-cache g++

COPY requirements.txt /tmp

RUN pip install -r /tmp/requirements.txt
