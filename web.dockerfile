FROM continuumio/miniconda3

WORKDIR /raftweb

RUN apt-get update && pip install fastapi==0.66.0 uvicorn==0.14.0

COPY web.py .
