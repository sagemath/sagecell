FROM sagemath/sagemath:10.7 AS precell

USER root

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y

RUN apt install -y \
  git curl npm build-essential \
  openssh-server rsyslog 

ARG GID=8888
ARG GROUP_NAME=sagecell
ARG SERVER_ID=8888
ARG SERVER_NAME=sc_serv
ARG WORKER_ID=9999
ARG WORKER_NAME=sc_work

RUN groupadd --gid $GID $GROUP_NAME
RUN useradd --uid $SERVER_ID --gid $GID -c '' -m -N $SERVER_NAME && passwd -l $SERVER_NAME
RUN useradd --uid $WORKER_ID --gid $GID -c '' -m -N $WORKER_NAME && passwd -l $WORKER_NAME

RUN chmod go+rx /home/sc_*

USER $SERVER_NAME
WORKDIR /home/$SERVER_NAME
RUN mkdir .ssh && chmod 0700 .ssh

USER $WORKER_NAME
WORKDIR /home/$WORKER_NAME
RUN mkdir .ssh && chmod 0700 .ssh


FROM precell AS sagecell

USER sage

RUN sage -pip install sockjs-tornado sqlalchemy paramiko lockfile

WORKDIR /home/sage

RUN git clone --recursive https://github.com/sagemath/sagecell.git 

WORKDIR /home/sage/sagecell

RUN mkdir static/jsmol && curl -o static/jsmol/JSmol.min.nojq.js https://chemapps.stolaf.edu/jmol/jsmol/JSmol.min.nojq.js

RUN sage -sh -c make

COPY ./sagecell /usr/local/bin/

EXPOSE 8888

CMD ["sagecell"]

