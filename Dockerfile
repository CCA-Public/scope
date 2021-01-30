FROM python:3.8-alpine

ENV PYTHONUNBUFFERED 1

RUN set -ex \
    && apk add --update --no-cache --virtual .buildDeps \
      alpine-sdk \
      gcc \
      libffi-dev \
      libxslt-dev \
      musl-dev

COPY requirements /build

RUN set -ex \
    && pip install --no-cache-dir -r /build/development.txt \
    && runDeps="$( \
      scanelf --needed --nobanner --format '%n#p' --recursive /usr/local \
        | tr ',' '\n' \
        | sort -u \
        | awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 \
          { next } { print "so:" $1 }' \
    )" \
    && apk add --no-cache --virtual .runDeps \
      $runDeps \
      gettext \
      nodejs-npm

COPY package.json package-lock.json /build/

RUN set -ex \
    && npm install --prefix /build \
    && apk del .buildDeps \
    && rm -rf /usr/src/python

COPY . /src

WORKDIR /src

RUN set -xe \
    && mv /build/node_modules ./ \
    && rm -rf /build

EXPOSE 8000

CMD ["gunicorn", "scope.wsgi:application", "-b=0:8000", "-k=gevent", "--reload"]
