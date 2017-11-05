FROM python:3.6

WORKDIR /src
COPY . /src

RUN pip install python-lambda
