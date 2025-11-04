FROM sagemath/sagemath:10.7

USER root

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
  git curl npm build-essential \
  openssh-server rsyslog \
  && rm -rf /var/lib/apt/lists/* \
  && mkdir /run/sshd

RUN useradd -m sage-worker -s /bin/bash -c "sage-worker" \
  && gpasswd -a sage-worker sage \
  && passwd -d sage-worker \
  && printf "sage-worker ALL=(ALL) NOPASSWD: ALL\n" >> /etc/sudoers.d/sage

USER sage-worker

COPY ./worker /usr/local/bin/

WORKDIR /home/sage-worker

EXPOSE 22

RUN /usr/local/bin/worker

USER root

RUN ssh-keygen -A && chmod 0600 /etc/ssh/ssh_host_*_key

CMD ["/usr/sbin/sshd", "-D"]
