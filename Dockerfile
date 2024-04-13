FROM satosa:8

RUN pip3 install kubernetes

COPY site-python/epfl /usr/local/lib/python3.12/site-packages/epfl
COPY custom-entrypoint.sh /
COPY config/proxy_conf.yaml /etc/satosa/

ENTRYPOINT ["bash", "-x", "/custom-entrypoint.sh"]
