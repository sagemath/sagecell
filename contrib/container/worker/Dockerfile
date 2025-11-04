FROM sagemath/sagemath:10.7 AS sagemath-base

USER root

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y

RUN apt install -y \
  git curl npm build-essential \
  openssh-server rsyslog 


FROM sagemath-base

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

