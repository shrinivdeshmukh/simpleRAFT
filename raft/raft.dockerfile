FROM continuumio/miniconda3

RUN apt-get update -y

WORKDIR /raft

COPY ./*.py /raft/