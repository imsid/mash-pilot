FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV MASH_DATA_DIR=/var/lib/mash
ENV MASH_API_HOST=0.0.0.0
ENV MASH_API_PORT=8000

# postgresql powers the single-container mode (embedded DB); when
# MASH_DATABASE_URL is provided (e.g. docker compose), it stays unused.
RUN apt-get update && apt-get install -y --no-install-recommends git postgresql && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/pilot

COPY pyproject.toml README.md ./
COPY pilot ./pilot

RUN pip install .

# Clone the mashpy repo as the workspace that Pilot agents operate on.
# This gives agents access to source code, READMEs, and git history.
RUN git clone --depth 1 https://github.com/imsid/mashpy.git /opt/mashpy

ENV MASH_HOST_APP=pilot.spec:build_pool
ENV PILOT_WORKSPACE_ROOT=/opt/mashpy
ENV PILOT_DATA_DIR=/var/lib/pilot

RUN mkdir -p /var/lib/mash /var/lib/pilot

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "mash host serve --host-app \"${MASH_HOST_APP}\" --host \"${MASH_API_HOST}\" --port \"${MASH_API_PORT}\" ${MASH_API_KEY:+--api-key \"$MASH_API_KEY\"}"]
