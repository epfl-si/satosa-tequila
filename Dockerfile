FROM satosa:8

USER 0
RUN pip3 install kubernetes
USER 1000

COPY site-python/epfl /usr/local/lib/python3.12/site-packages/epfl
COPY custom-entrypoint.sh /
COPY config/proxy_conf.yaml /etc/satosa/

ENTRYPOINT ["bash", "-x", "/custom-entrypoint.sh"]
