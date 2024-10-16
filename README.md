[![Integration tests](https://github.com/CCA-Public/scope/workflows/Integration%20tests/badge.svg)](https://github.com/CCA-Public/scope/actions?query=workflow%3A%22Integration+tests%22)
[![Unit tests](https://github.com/CCA-Public/scope/workflows/Unit%20tests/badge.svg)](https://github.com/CCA-Public/scope/actions?query=workflow%3A%22Unit+tests%22)
[![Codecov](https://codecov.io/gh/CCA-Public/scope/branch/master/graph/badge.svg)](https://codecov.io/gh/CCA-Public/scope)
[![pyup](https://pyup.io/repos/github/CCA-Public/scope/shield.svg)](https://pyup.io/repos/github/CCA-Public/scope)
[![Python Version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue)](https://devguide.python.org/#status-of-python-branches)
[![AGPLv3 license](https://img.shields.io/badge/license-AGPLv3-blue.svg)](https://github.com/CCA-Public/scope/blob/master/LICENSE)


# SCOPE: A Digital Archives Access Interface

* [Overview](#overview)
* [Data model](#data-model)
* [Uploading new DIPs](#uploading-new-dips)
* [User types and permissions](#user-types-and-permissions)
* [Technologies involved](#technologies-involved)
  * [Django, Celery and SQLite](#django-celery-and-sqlite)
  * [Redis](#redis)
  * [Elasticsearch](#elasticsearch)
* [Recommended system requirements](#recommended-system-requirements)
* [Installation](#installation)
  * [Requirements](#requirements)
  * [Environment](#environment)
  * [Setup](#setup)
  * [Configure worker](#configure-worker)
  * [Serve](#serve)
  * [Storage Service integration](#storage-service-integration)
* [Development](#development)
* [Testing](#testing)
* [Credits](#credits)

## Overview

SCOPE is a Django project designed to provide access to Dissemination Information Packages (i.e., access copies of digital files stored in Archival Information Packages in CCA's Archivematica-based digital repository). The project is designed to work with normal Archivematica DIPs and also with the custom DIPs generated by [create_dip.py](https://github.com/artefactual/automation-tools/blob/master/aips/create_dip.py) via Artefactual's [Automation Tools](https://github.com/artefactual/automation-tools).

The primary application, "scope", allows users to add, organize, and interact with these DIPs and the digital files they contain, depending on user permissions.  

See the [user stories](https://github.com/CCA-Public/scope/wiki/User-Stories) for background on current and future features.

See the [user manual](manuals/SCOPE-user-manual-v.1.0_EN.pdf) for instructions on how to use SCOPE v.1.0

**Une version française du manuel pour SCOPE v.1.0 peut être [trouvée ici](manuals/SCOPE%20user%20manual%20-%20v.1.0%20FR%20(002).pdf)**.

## Data model

The application organizes and displays information in several levels:

* **Collection**: A Collection is the highest level of organization and corresponds to an archive or other assembled collection of materials. A Collection has 0 to many Folders as children (in practice, every collection should have at least one child, but this is not enforced by the application). Collections may also have unqualified Dublin Core descriptive metadata, as well as a link to a finding aid.
* **Folder**: A Folder corresponds 1:1 with a Dissemination Information Package (DIP). A Folder has 1 to many Digital Files as children, which are auto-generated from information in the AIP METS file included as part of the CCA-style DIP. Folders may also have unqualified Dublin Core metadata. The DC metadata from the most recently updated dmdSec is written into the Folder record when the METS file is uploaded (except "ispartof", which is hard-coded on creation of the Folder. This might be something to change for more generalized usage).
* **Digital File**: A Digital File corresponds to a description of an original digital file in the AIP METS file and contains detailed metadata from an AIP METS file amdSec, including a list of PREMIS events. Digital Files should never be created manually, but only generated via parsing of the METS file when a new Folder is added.

## Uploading new DIPs

When a sufficiently privileged user creates a new Folder through the GUI interface, they need only enter the identifier, optionally choose the Collection to which the Folder belongs, and upload a copy of the DIP file (in tar or zip format). The application then uses the `parsemets.py` script to parse the AIP METS file included in the DIP, automatically:

* Saving Dublin Core metadata found in the (most recently updated) dmdSec to the DIP model object for the Folder
* Generating records for Digital Files and the PREMIS events associated with each digital file and saving them to the database.

Additionally, the application can be integrated with one or more Archivematica Storage Service instances to import the DIPs stored in them automatically, without keeping a local copy in SCOPE.

Once the DIP has been uploaded, the metadata for the Folder can be edited through the GUI by any user with sufficient permissions.

## User types and permissions

By default, the application has five levels of permissions:

* **Administrators**: Administrators have access to all parts of the application.
* **Managers**: Users in this group can manage users but not make them administrators.
* **Editors**: Users in this group can add and edit Collections and Folders but not delete them.
* **Public**: Users with a username/password but no additional permissions have view-only access.
* **Unauthenticated**: Not logged in users can only access the FAQ and login pages.

## Technologies involved

SCOPE is a Django application that uses Elasticsearch as search engine, Celery to process asynchronous tasks, a SQLite database and Redis as message broker (probably in the future, as cache system too).

### Django, Celery and SQLite

The Django application and the Celery worker need access to the source code, the database and the stored DIP files. To avoid complexity and because the application currently uses SQLite as the database engine, it’s recommended to have both components running on the same machine.

The application is ready to be served with Gunicorn and Gevent, using WhiteNoise to serve the static files and Nginx, to proxy the application and serve the uploaded DIP files. Check the install notes below for more information. Gunicorn is deployed using the Gevent worker class, meaning that a single worker should scale sufficiently even during I/O-bound operations like serving static files. If there are more CPU-bound tasks needed in the future, those will be delegated to the Celery async. task queue to ensure that the event loop is not blocked; therefore, the recommended amount of workers deployed is one.

Large file uploads (+2.5 megabytes) are saved in the OS temporary directory and deleted at the end of the request by Django and, using SQLite as the database engine, the memory requirements should be really low for this part of the application. Some notes about SQLite memory management in [this page](https://www2.sqlite.org/sysreq.html) (from S30000 to S30500).

The amount of Celery workers deployed to handle asynchronous tasks could vary, as well as the pool size for each worker, check [the Celery concurrency documentation](http://docs.celeryproject.org/en/latest/userguide/workers.html#concurrency). However, to reduce the possibility of simultaneous writes to the SQLite database, we suggest to use a single worker with a concurrency of one. Until a better parsing process is developed, the entire METS file is being hold in memory and, for that reason, the amount of memory needed for this part of the application can be really high, depending on the number of files in the DIP and the size and contents of its METS file. The METS file will also be extracted in the OS temporary directory during the process, so the disk capacity should also meet the same requirement.

The application stores the manually uploaded DIP files in the "media" folder at the application location. This should be considered to determine the disk capacity needed to hold the application data; in addition to the SQLite database, the space needed for the METS files extraction (mentioned above) and around 200 megabytes to hold the source code and Python dependencies.

### Redis

Redis is used as broker in the current Celery implementation and it will probably be used as cache system in the future. This component could be installed in the same or a different server and its URL can be configured through an environment variable read in the Django settings. At this point the memory footprint, the CPU usage and the disk allocation needed for snapshots will be minimal. Check [the Redis FAQ page](https://redis.io/topics/faq) for more information.

### Elasticsearch

Elasticsearch could also be installed in the same or different servers and its URL(s) can be configured through an environment variable read in the Django settings. The application requires Elasticsearch 7.x, which includes a a bundled version of [OpenJDK](http://openjdk.java.net/) from the JDK maintainers (GPLv2+CE). To use your own version of Java, see the [JVM version requirements](https://www.elastic.co/guide/en/elasticsearch/reference/7.x/setup.html#jvm-version).

The Elasticsearch node/cluster configuration can be fully customized, however, for the current implementation, a single node with the the default JVM heap size of 1GB set by Elasticsearch would be more than enough. It could even be reduced to 512MB if more memory is needed for other parts of the application or to reduce its requirements. For more info on how to change the Elasticsearch configuration check [their documentation](https://www.elastic.co/guide/en/elasticsearch/reference/7.x/settings.html), specially [the JVM heap size page](https://www.elastic.co/guide/en/elasticsearch/reference/7.x/heap-size.html).

The Elasticsearch indexes size will vary based on the application data and they will require some disk space, but it’s hard to tell how much at this point.

## Recommended system requirements

* Processor, 2 CPU cores.
* Memory, 2GB:
  - 1GB JVM heap size.
  - Biggest METS file size expected.
  - Other services (Nginx, Redis)
* Disk space, the sum of:
  - ~1GB for source code, dependencies and needed services.
  - ~1GB for SQLite database and Elasticsearch data (to be revised as data grows).
  - Biggest DIP file size expected.
  - Biggest METS file size expected.
  - Total DIP storage size.

## Installation

The following steps are just an example of how to run the application in a production environment, with all the services involved sharing the same machine, over Ubuntu 20.04
(LTS) x64.

### Requirements

* Python 3.6 to 3.8
* Elasticsearch 7
* Redis 4 to 6

### Environment

The following environment variables are used to run the application:

* `DJANGO_ALLOWED_HOSTS` **[REQUIRED]**: List of host/domain names separated by comma that this instance can serve.
* `DJANGO_SECRET_KEY` **[REQUIRED]**: A secret key for this instance, used to provide cryptographic signing, and should be set to a unique, unpredictable value.
* `DJANGO_DEBUG`: Boolean that turns on/off debug mode. Never deploy a site into production with it turned on. *Default:* `False`.
* `DJANGO_TIME_ZONE`: Timezone for the instance. E.g.: `America/Montreal`. *Default:* `UTC`.
* `ES_HOSTS` **[REQUIRED]**: List of Elasticsearch hosts separated by comma. RFC-1738 formatted URLs can be used. E.g.: `https://user:secret@host:443/`.
* `ES_TIMEOUT`: Timeout in seconds for Elasticsearch requests. *Default:* `10`.
* `ES_POOL_SIZE`: Elasticsearch requests pool size. *Default:* `10`.
* `ES_INDEXES_SHARDS`: Number of shards for Elasticsearch indexes. *Default:* `1`.
* `ES_INDEXES_REPLICAS`: Number of replicas for Elasticsearch indexes. *Default:* `0`.
* `CELERY_BROKER_URL` **[REQUIRED]**: Redis server URL. E.g.: `redis://hostname:port`.
* `CELERY_BROKER_VISIBILITY_TIMEOUT`: Time in seconds for Redis to redeliver a task if it has not been acknowledged by any worker ([more info](http://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html#id1)). Set this to a higher value if you're planing to launch simultaneous long time running DIP imports. *Default:* `3600`.
* `SS_HOSTS`: List of Storage Service hosts separated by comma. RFC-1738 formatted URLs must be used to set the credentials for each host. See the [the Storage Service integration notes](#storage-service-integration) bellow for more information.

Make sure [the system locale environment variables](https://wiki.debian.org/Locale) are configured to use UTF-8 encoding.

### Setup

As the root user, install pip, virtualenv and other needed libraries:

```
apt update
apt upgrade
apt install build-essential gcc gettext python3-dev
wget https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
rm get-pip.py
pip install virtualenv
```

Install Elasticsearch:

```
apt install apt-transport-https
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add -
echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-7.x.list
apt update
apt install elasticsearch
systemctl daemon-reload
systemctl start elasticsearch
systemctl enable elasticsearch
```

Verify Elasticsearch is running:

```
curl -X GET "localhost:9200/?pretty"

{
  "name" : "scope",
  "cluster_name" : "elasticsearch",
  "cluster_uuid" : "pfyamzYjS62A8JgDAvHsww",
  "version" : {
    "number" : "7.9.1",
    "build_flavor" : "default",
    "build_type" : "deb",
    "build_hash" : "083627f112ba94dffc1232e8b42b73492789ef91",
    "build_date" : "2020-09-01T21:22:21.964974Z",
    "build_snapshot" : false,
    "lucene_version" : "8.6.2",
    "minimum_wire_compatibility_version" : "6.8.0",
    "minimum_index_compatibility_version" : "6.0.0-beta1"
  },
  "tagline" : "You Know, for Search"
}
```

Intall Redis:

```
apt install redis-server
nano /etc/redis/redis.conf
```

Change the `supervised` directive to use `systemd` and, for a better level of persistence,
set `appendonly` to `yes`:

```
...

# If you run Redis from upstart or systemd, Redis can interact with your
# supervision tree. Options:
#   supervised no      - no supervision interaction
#   supervised upstart - signal upstart by putting Redis into SIGSTOP mode
#   supervised systemd - signal systemd by writing READY=1 to $NOTIFY_SOCKET
#   supervised auto    - detect upstart or systemd method based on
#                        UPSTART_JOB or NOTIFY_SOCKET environment variables
# Note: these supervision methods only signal "process is ready."
#       They do not enable continuous liveness pings back to your supervisor.
supervised systemd

...

# AOF and RDB persistence can be enabled at the same time without problems.
# If the AOF is enabled on startup Redis will load the AOF, that is the file
# with the better durability guarantees.
#
# Please check http://redis.io/topics/persistence for more information.

appendonly yes
...
```

Press Ctrl+X to save and exit, and restart the service:

```
systemctl restart redis
```

If you decide to install it in a different server, make sure to check [Redis' security documentation](https://redis.io/topics/security) and include the password into the 'CELERY_BROKER_URL' environment variable, following the `redis://:password@hostname:port/db_number` format.

Create user to own and run the application, log in and make sure you're placed in its home folder:

```
adduser cca
su - cca
cd ~
```

Create an environment file in `~/scope-env`, at least with the required variables, to reference it where it's needed, for example:

```
DJANGO_ALLOWED_HOSTS=example.com
DJANGO_SECRET_KEY=secret_key
ES_HOSTS=localhost:9200
CELERY_BROKER_URL=redis://localhost:6379
```

Clone the repository and go to its directory:

```
git clone https://github.com/CCA-Public/scope
cd scope
```

Create a Python virtual environment and install the application dependencies:

```
virtualenv venv -p python3  
source venv/bin/activate  
pip install -r requirements.txt
nodeenv --python-virtualenv
npm install
```

Export the environment variables to run the `manage.py` commands:

```
export $(cat ~/scope-env)
```

Create the `media` folder with read and execute permissions for the group:

```
mkdir -p media
chmod 750 media
```

Initialize the database:

```
./manage.py migrate
```

Create search indexes:

```
./manage.py index_data
```

Add a superuser:

```
./manage.py createsuperuser
```

Follow the instructions to create a user with full admin rights.

Compile translation files:

```
./manage.py compilemessages
```

Collect and build static files:

```
./manage.py collectstatic
./manage.py compress
```

You can now deactivate the environment and go back to the root session:

```
deactivate && exit
```

### Configure worker

To execute asynchronous tasks, back as the 'root' user, create a systemd service file to run the Celery worker. In `/etc/systemd/system/scope-worker.service`, with the following content:

```
[Unit]
Description=Scope Celery Worker
After=network.target

[Service]
Type=forking
User=cca
Group=cca
EnvironmentFile=/home/cca/scope-env
Environment=CELERYD_PID_FILE=/home/cca/scope-worker.pid
Environment=CELERYD_LOG_FILE=/home/cca/scope-worker.log
WorkingDirectory=/home/cca/scope
ExecStart=/home/cca/scope/venv/bin/celery \
            multi start scope-worker -A scope \
            --concurrency=1 \
            --pidfile=${CELERYD_PID_FILE} \
            --logfile=${CELERYD_LOG_FILE} \
            --loglevel=WARNING
ExecReload=/home/cca/scope/venv/bin/celery \
            multi restart scope-worker -A scope \
            --concurrency=1 \
            --pidfile=${CELERYD_PID_FILE} \
            --logfile=${CELERYD_LOG_FILE} \
            --loglevel=WARNING
ExecStop=/home/cca/scope/venv/bin/celery \
            multi stopwait scope-worker \
            --pidfile=${CELERYD_PID_FILE}

[Install]
WantedBy=multi-user.target
```

Start and enable the service:

```
systemctl start scope-worker
systemctl enable scope-worker
```

To access the service logs, use:

```
journalctl -u scope-worker
```

### Serve

The application requirements install Gunicorn, Gevent and WhiteNoise to serve the application, including the static files. Create a systemd service file to run the Gunicorn daemon in `/etc/systemd/system/scope-gunicorn.service`, with the following content:

```
[Unit]
Description=Scope Gunicorn daemon
After=network.target

[Service]
User=cca
Group=cca
PrivateTmp=true
PIDFile=/home/cca/scope-gunicorn.pid
EnvironmentFile=/home/cca/scope-env
WorkingDirectory=/home/cca/scope
ExecStart=/home/cca/scope/venv/bin/gunicorn \
            --access-logfile /dev/null \
            --worker-class gevent \
            --bind unix:/home/cca/scope-gunicorn.sock \
            scope.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID

[Install]
WantedBy=multi-user.target
```

Start and enable the service:

```
systemctl start scope-gunicorn
systemctl enable scope-gunicorn
```

To access the service logs, use:

```
journalctl -u scope-gunicorn
```

The Gunicorn service is using an Unix socket to listen for connections and we will use Nginx to proxy the application and to serve the uploaded DIP files. The `client_max_body_size` and `proxy_read_timeout` values should be changed based on the biggest DIP file and upload time expected. It should also be used to secure the site, but we won't cover that configuration in this example. Install Nginx and create a configuration file:

```
apt install nginx
nano /etc/nginx/sites-available/scope
```

With the following configuration:

```
upstream scope {
  server unix:/home/cca/scope-gunicorn.sock;
}

server {
  listen 80;
  server_name example.com;
  client_max_body_size 500M;

  location /media/ {
    internal;
    alias /home/cca/scope/media/;
  }

  location / {
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_redirect off;
    proxy_buffering off;
    proxy_read_timeout 600s;
    proxy_pass http://scope;
  }
}
```

Link the site configuration to `sites-enabled` and remove the default configuration:

```
ln -s /etc/nginx/sites-available/scope /etc/nginx/sites-enabled
rm /etc/nginx/sites-enabled/default
```

Verify configuration and restart Nginx service:

```
nginx -t
systemctl restart nginx
```

Make sure that the user running Nginx (usually 'www-data') has access to the media folder and files by adding it to the 'cca' group:

```
usermod -a -G cca www-data
```

Reboot the OS to reflect user changes. Make sure the required services are running afterwards:

```
systemctl status nginx redis elasticsearch scope-gunicorn scope-worker
```

### Storage Service integration

**Storage Service 0.15.0 or higher required.**

SCOPE can be related with one or more Storage Service instances to automatically import the DIPs stored in them. In this case, the DIPs will only be stored in the Storage Service, SCOPE will fetch the DIP's METS file to perform the import process and it will act as a proxy when a download is requested.

For this integration to be secure, it requires HTTPS in the Storage Service and SCOPE instances, as credentials will be sent from both instances to the other.

#### Create user and token in SCOPE

To authenticate the notification request that will be sent from the Storage Service instance when a DIP is stored, it's recommended to create an user in SCOPE that is only used for token access:

```
./manage.py createsuperuser
./manage.py drf_create_token <username>
```

Save the generated token as it will be needed to configure the Storage Service callback.

#### Configure Storage Service instance(s) in SCOPE

To authenticate the requests sent from SCOPE to fetch the DIP's METS file and download the DIP from the Storage Service instance(s), those instances must be declared in an environment variable called `SS_HOSTS`, which accepts a list of RFC-1738 URLs separated by comma. For example, to integrate SCOPE with a Storage Service instance with `https://ss.com` as URL, `user` as username and `secret` as the Storage Service user's API key, add the following to the `~/scope-env` environment file:

```
SS_HOSTS=https://user:secret@ss.com
```

Make sure to restart SCOPE's worker and Gunicorn services after that change:

```
systemctl restart scope-worker
systemctl restart scope-gunicorn
```

#### Add post store DIP callback in Storage Service

To notify SCOPE when a DIP has been stored in the Storage Service a post store DIP callback must be configured. Following the same example and considering that SCOPE's URL is `https://scope.com`, go to the Storage Service interface, to the "Service callbacks" section in the "Administration" tab and create a new callback with the following parameters:

* **Event:** `Post-store DIP`
* **URI:** `https://scope.com/api/v1/dip/<package_uuid>/stored`
* **Method:** `POST`
* **Headers:**
  * Authorization -> `Token <token>`
  * Origin -> `https://ss.com`
* **Expected Status:** `202`

Replace the `<token>` placeholder with the token generated before but keep `<package_uuid>` like that, as that placeholder is used by the Storage Service to place the DIP UUID. The body field can be left empty for this integration and the callback can be enabled/disable using the check-box at the bottom.

## Development

Requires [Docker CE](https://www.docker.com/community-edition) and [Docker Compose](https://docs.docker.com/compose/).

Clone the repository and go to its directory:

```
git clone https://github.com/CCA-Public/scope
cd scope
```

Build images, initialize services, etc.:

```
docker-compose up -d
```

Initialize database:

```
docker-compose exec scope ./manage.py migrate
```

Create search indexes:

```
docker-compose exec scope ./manage.py index_data
```

Add a superuser:

```
docker-compose exec scope ./manage.py createsuperuser
```

Follow the instructions to create a user with full administrator rights.

Compile translation files:

```
docker-compose exec scope ./manage.py compilemessages
```

Access the logs:

```
docker-compose logs -f scope elasticsearch nginx
```

To access the application with the default options visit http://localhost:43430 in the browser.

## Testing

### Unit tests

If you're using the development environment, you can run the Django unit tests within the
`scope` container (all of them or individually):

```
docker-compose exec scope ./manage.py test
docker-compose exec scope ./manage.py test scope.tests.test_helpers.HelpersTests.test_convert_size
```

To run the automated tests and checks configured with Tox in the required
Python versions, the core developers' Python image for CI is available at
[Quay.io](https://quay.io/repository/python-devs/ci-image). Use the following
command to create a one go container to do so:

```
docker run --rm -t -v `pwd`:/src -w /src quay.io/python-devs/ci-image tox
```

### Integration tests

The application includes a set of end to end tests developed with
[Cypress.io](https://www.cypress.io/). To run these tests locally, check Cypress' dependencies
for you OS and run:

```
npm install --only=dev
npx cypress install
npx cypress open
```

They also provide a set of Docker images that will allow you to run the tests in a container,
for example:

- To run the tests in the terminal with the default browser (Electron), you can use their base image:

```
docker run --rm -v $PWD:/src -w /src --network=host cypress/base:14.15.4 bash -c "npm install -D && npx cypress install && npx cypress run"
```

- And you could use their browsers image to test over Firefox and Chrome:

```
docker run --rm -v $PWD:/src -w /src --network=host cypress/browsers bash -c "npm install -D && npx cypress install && npx cypress run --browser firefox"
```

By default, these tests will try to access the application in http://localhost:43430 using
`ci_admin/ci_admin` as credentials. To change this defaults use the following environment variables:

```
CYPRESS_baseUrl
CYPRESS_username
CYPRESS_password
```

They could be set locally or passed to the Docker container:

```
docker run --rm -v $PWD:/src -w /src --network=host \
  -e CYPRESS_baseUrl=https://example.com \
  -e CYPRESS_username=user \
  -e CYPRESS_password=secret \
  cypress/base:14.15.4 bash -c "npm install -D && npx cypress install && npx cypress run"
```

While these variables could be configured to test a production like instance, the tests may
leave residual data in such instance (for example in the case of failure), so it's recomended
to backup the database and media folder to be able to restore them after the tests.

## Credits

SCOPE was produced by the Canadian Centre for Architecture (CCA) and developed by Artefactual Systems, based on an project initially conceived by Tessa Walsh, digital archivist at CCA from June 2015 to May 2018. It is a project financed within the framework of the Montreal Cultural Development grant awarded by the City of Montreal and the Quebec Department of Culture and Communications.

SCOPE a été conçue par le Centre Canadien d'Architecture (CCA) et développée par Artefactual Systems, à partir d’un concept initialement élaboré par Tessa Walsh, archiviste numérique au CCA de juin 2015 à mai 2018. SCOPE est un projet financé dans le cadre de l’Entente sur le développement culturel de Montréal par la Ville de Montréal et le ministère de la Culture et des Communications.
