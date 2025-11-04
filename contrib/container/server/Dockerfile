FROM sagemath/sagemath:10.7

USER root

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
  git curl npm build-essential \
  openssh-server rsyslog \
  && rm -rf /var/lib/apt/lists/*

USER sage

RUN sage -pip install sockjs-tornado sqlalchemy paramiko lockfile

WORKDIR /home/sage

RUN git clone --recursive https://github.com/sagemath/sagecell.git 
RUN mkdir .ssh

WORKDIR /home/sage/sagecell

RUN mkdir static/jsmol && curl -o static/jsmol/JSmol.min.nojq.js https://chemapps.stolaf.edu/jmol/jsmol/JSmol.min.nojq.js

RUN sage -sh -c make

COPY ./sagecell /usr/local/bin/

EXPOSE 8888

CMD ["sagecell"]

