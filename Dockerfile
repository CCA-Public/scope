FROM python:3.8-slim-bullseye

ENV PYTHONUNBUFFERED 1

RUN set -ex \
    && apt-get update \
    && apt-get install -y \
      gcc \
      libffi-dev \
      libxslt-dev \
      musl-dev \
      gettext \
      nodejs \
      npm

COPY requirements /build

RUN pip install --no-cache-dir -r /build/development.txt

COPY package.json package-lock.json /build/

RUN npm install --prefix /build

COPY . /src

WORKDIR /src

RUN mv /build/node_modules ./

EXPOSE 8000

CMD ["gunicorn", "scope.wsgi:application", "-b=0:8000", "-k=gevent", "--reload"]
