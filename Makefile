include .env

KEY_TARGETS := tls/satosa.crt tls/satosa.key

ALL_TARGETS := $(KEY_TARGETS)
.PHONY: all
all: $(ALL_TARGETS)

tls/satosa.crt: tls/satosa.key
	openssl req -x509 -new -key $< \
	  -batch -subj '/CN=localhost' \
	  -days 3650 \
	  -out $@

tls/satosa.key:
	@-mkdir tls
	openssl genrsa 2048 > $@

.PHONY: up
up: all
	docker compose up -d

.PHONY: down
down:
	docker compose down

.PHONY: clean
clean:
	rm -rf $(ALL_TARGETS)
