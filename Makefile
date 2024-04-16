KEY_TARGETS := tls/tls.crt tls/tls.key

ALL_TARGETS := $(KEY_TARGETS)
.PHONY: all
all: $(ALL_TARGETS)

tls/tls.crt: tls/tls.key
	openssl req -x509 -new -key $< \
	  -batch -subj '/CN=localhost' \
	  -days 3650 \
	  -out $@

tls/tls.key:
	@-mkdir tls
	openssl genrsa 2048 > $@

.PHONY: up
up: all k8s-credentials
	docker compose up --build -d

.PHONY: logs
logs:
	docker compose logs -f

.PHONY: down
down:
	docker compose down

.PHONY: clean
clean:
	rm -rf $(ALL_TARGETS)

k8s-credentials:
	./devsupport/prepare-k8s-credentials "$@"
