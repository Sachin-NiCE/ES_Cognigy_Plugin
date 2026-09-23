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

# uvicorn (see supervisord.conf's "user=mcp") drops to this non-root user;
# nginx's master process and supervisord itself stay root, which nginx
# requires to bind ports 80/443 (its workers still drop to www-data
# internally, per the stock Debian nginx config).
RUN useradd --no-create-home --shell /usr/sbin/nologin mcp

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
