# Certificates go here

Put your corporate TLS certificate and private key in this folder, named
exactly:

```
nginx/certs/fullchain.pem
nginx/certs/privkey.pem
```

If your CA issues a separate intermediate chain, concatenate it into
`fullchain.pem` after your leaf certificate (standard PEM chain order: leaf
first, then intermediates).

This folder is mounted read-only into the container at `/etc/nginx/certs`.
The actual `.pem` files are gitignored — never commit real certificates or
keys to this repo.
