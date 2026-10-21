#!/bin/sh
# Точка входа контейнера frontend.
#
# В compose-сети Podman адрес DNS-сервера не всегда 127.0.0.11: он зависит
# от сети и может быть любым адресом из /etc/resolv.conf. Жёстко прописанный
# resolver приводил к зависанию проксирования на backend.
# Поэтому адрес резолвера определяется при старте контейнера и подставляется
# в конфигурацию nginx.

set -eu

TEMPLATE=/etc/nginx/templates/default.conf.template
TARGET=/etc/nginx/conf.d/default.conf

RESOLVER="$(awk '/^nameserver/ { print $2; exit }' /etc/resolv.conf)"

if [ -z "${RESOLVER}" ]; then
    echo "[entrypoint] не найден nameserver в /etc/resolv.conf, использую 127.0.0.11" >&2
    RESOLVER=127.0.0.11
fi

echo "[entrypoint] DNS-резолвер: ${RESOLVER}" >&2
sed "s/__NGINX_RESOLVER__/${RESOLVER}/g" "${TEMPLATE}" > "${TARGET}"

# Проверяем конфигурацию до запуска: ошибка nginx не должна оставаться незамеченной
nginx -t >&2

exec nginx -g 'daemon off;'
