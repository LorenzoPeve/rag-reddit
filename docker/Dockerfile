FROM python:3.11.3-slim-buster

# set work directory
WORKDIR /app
COPY . /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install system dependencies
RUN apt-get update && apt-get install

# install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
