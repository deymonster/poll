FROM            python:3.11-slim

ENV             PYTHONBUFFERED=1
ENV             LANGUAGE en_US.UTF-8
ENV             USER pool_users
ENV             PROJECTPATH=/home/pool_users/app

RUN             set -x \
                && apt update -qq \
                && apt install -y --no-install-recommends libpq-dev binutils curl \
                && apt purge -y --auto-remove \
                && rm -rf /var/lib/apt/lists/*

RUN             useradd -m -d /home/${USER} ${USER} \
                && chown -R ${USER} /home/${USER}

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

COPY            ./src/* ${PROJECTPATH}

USER            ${USER}

