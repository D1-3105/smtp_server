FROM python:3.10.6-alpine

ENV PYTHONUNBUFFERED 1
COPY ./requirements.txt /requirements.txt

RUN pip install -r requirements.txt


RUN mkdir /mailing_service
RUN mkdir /mailing_service/mailing
RUN mkdir /mailing_service/test

COPY ./mailing /mailing_service/mailing
COPY ./test /mailing_service/test

WORKDIR /mailing_service
