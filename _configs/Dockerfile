FROM            python:3.11-slim as build-stage

ENV             PYTHONUNBUFFERED=1
ENV             LANGUAGE en_US.UTF-8
ENV             USER poll_users
ENV             PROJECTPATH=/home/poll_users/app

ARG             UID
ARG             GID

RUN             set -x \
                && apt update -qq \
                && apt install -y --no-install-recommends libpq-dev binutils curl \
                && apt purge -y --auto-remove \
                && rm -rf /var/lib/apt/lists/*

#RUN             useradd -m -d /home/${USER} ${USER} \
#                && chown -R ${USER} /home/${USER}

RUN             groupadd -g ${GID} ${USER} \
                && useradd -u ${UID} -g ${GID} -m -d /home/${USER} ${USER} \
                && chown -R ${USER}:${USER} /home/${USER}

RUN             mkdir -p ${PROJECTPATH}

ADD             https://github.com/ufoscout/docker-compose-wait/releases/download/2.9.0/wait ${PROJECTPATH}/wait
RUN             chmod +x ${PROJECTPATH}/wait

RUN             curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 - \
                && cd /usr/local/bin \
                && ln -s /etc/poetry/bin/poetry \
                && poetry config virtualenvs.create false

WORKDIR         ${PROJECTPATH}

COPY            poetry.lock pyproject.toml ${PROJECTPATH}

RUN             poetry install --no-root


COPY            ./src ${PROJECTPATH}

RUN             mkdir -p ${PROJECTPATH}/logs \
                && touch ${PROJECTPATH}/logs/all_logs.log \
                && chown -R ${USER}:${USER} ${PROJECTPATH}/logs \
                && chmod 664 ${PROJECTPATH}/logs/all_logs.log

USER            ${USER}

FROM            tiangolo/uvicorn-gunicorn:python3.11-slim as production-stage
ARG             UID
ARG             GID
COPY            ./src/requirements.txt /app/requirements.txt
RUN             pip install --no-cache-dir --upgrade -r /app/requirements.txt
COPY            ./src /app
RUN             mkdir -p /app/logs \
                && touch /app/logs/all_logs.log  \
                && chown -R ${UID}:${GID} /app/logs \
                && chmod 664 /app/logs/all_logs.log \
                && chown -R ${UID}:${GID} /app/media \
                && find /app/media -type d -exec chmod 775 {} \; \
                && find /app/media -type f -exec chmod 664 {} \; \
                && chmod +x /app/prestart.sh
USER            ${UID}:${GID}



