FROM python:3.12-slim

# nginx + supervisor run this container's TLS termination and process
# management; gettext-base provides envsubst for rendering the nginx config
# at startup (see entrypoint.sh).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor gettext-base \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /etc/nginx/templates /etc/nginx/certs \
    && mv nginx/default.conf.template /etc/nginx/templates/default.conf.template \
    && mv supervisord.conf /etc/supervisor/conf.d/supervisord.conf \
    && mv entrypoint.sh /entrypoint.sh \
    && chmod +x /entrypoint.sh \
    && rmdir nginx

# The whole container runs as this non-root user (see USER below) - nginx
# listens on unprivileged ports (8080/8443, see nginx/default.conf.template)
# so it never needs root to bind them, and docker-compose.yml maps the real
# 80/443 host ports to those from outside the container instead.
RUN useradd --no-create-home --shell /usr/sbin/nologin mcp \
    && mkdir -p /var/lib/nginx /var/log/nginx /run \
    && chown -R mcp:mcp /var/lib/nginx /var/log/nginx /run /etc/nginx /app \
    # nginx's stock config drops privileges to www-data after binding as
    # root, which no longer applies (and would fail) once we're already
    # non-root - strip that directive so nginx doesn't try it.
    && sed -i '/^user /d' /etc/nginx/nginx.conf

USER mcp

EXPOSE 8080 8443

ENTRYPOINT ["/entrypoint.sh"]
