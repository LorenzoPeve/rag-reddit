# Use Ubuntu as the base image
FROM ubuntu:22.04

# Prevent timezone prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install software-properties-common to get add-apt-repository command
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Add deadsnakes PPA to get Python 3.10
RUN add-apt-repository ppa:deadsnakes/ppa

# Install Python 3.10 and pip
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3.10-distutils \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pip for Python 3.10
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

# Create symbolic links for python and pip commands
RUN ln -sf /usr/bin/python3.10 /usr/bin/python
RUN ln -sf /usr/bin/pip3.10 /usr/bin/pip

# Set the working directory in the container
WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt --verbose

COPY . /app
