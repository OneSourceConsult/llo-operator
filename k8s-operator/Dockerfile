FROM python:3.9-slim-buster

WORKDIR /

#install deps: curl kubectl #iptables wireguard-tools  && \ 
RUN apt-get update \
&& apt-get install -y python3-pip curl wget file && \
    # clean-up
    rm -rf /root/.cache && mkdir -p /root/.cache && \
    rm -rf /tmp/* /var/tmp/* /var/cache/apk/* /var/cache/distfiles/*

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir kopf[dev]
RUN pip3 install --no-cache-dir -r requirements.txt

COPY kopf-operator /kopf-operator/

EXPOSE 6000

CMD ["kopf", "run", "--all-namespaces", "--verbose", "/kopf-operator/k8s-operator.py"]