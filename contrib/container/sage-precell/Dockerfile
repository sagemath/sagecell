FROM sagemath/sagemath:10.7

USER root

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y

COPY ./packages /tmp/

RUN apt install -y $(cat /tmp/sage-recommendations.txt)
RUN apt install -y $(cat /tmp/sage-optional.txt)
RUN apt install -y $(cat /tmp/sage-precell.txt)

RUN apt clean
