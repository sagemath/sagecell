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
RUN mkdir .ssh && chmod 0700 .ssh && ssh-keygen -t ed25519 -N '' -f .ssh/id_ed25519

USER $WORKER_NAME
WORKDIR /home/$WORKER_NAME
RUN mkdir .ssh && chmod 0700 .ssh && ssh-keygen -t ed25519 -N '' -f .ssh/id_ed25519


FROM precell AS sagecell

USER root

COPY ./worker /usr/local/bin/

RUN ssh-keygen -A && chmod 0600 /etc/ssh/ssh_host_*_key

RUN useradd -m sage-worker -s /bin/bash -c "sage-worker" \
  && gpasswd -a sage-worker sage \
  && passwd -d sage-worker \
  && printf "sage-worker ALL=(ALL) NOPASSWD: ALL\n" >> /etc/sudoers.d/sage

USER sage-worker

WORKDIR /home/sage-worker

ENV HOME=/home/sage-worker

EXPOSE 22

CMD ["worker"]

