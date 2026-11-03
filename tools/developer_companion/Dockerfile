# Explicit build only. Runtime refuses mutable tags and never pulls an image.
FROM node:24-bookworm-slim AS dsh
RUN npm install --prefix /opt/dsh --ignore-scripts --no-audit --no-fund @deepseek-ai/dsh@0.1.2-alpha.1
FROM python:3.13-slim-bookworm
COPY --from=dsh /usr/local/bin/node /usr/local/bin/node
COPY --from=dsh /opt/dsh /opt/dsh
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 runner && useradd --uid 10001 --gid 10001 --create-home runner
COPY container_requirements.txt /opt/companion/container_requirements.txt
RUN pip install --no-cache-dir -r /opt/companion/container_requirements.txt
RUN mkdir -p /home/runner/.dsh/profiles/sdk \
    && ln -s /opt/dsh/node_modules /home/runner/.dsh/profiles/node_modules \
    && printf '%s' '{"name":"companion-sdk","private":true,"dsh":{"profile":{"bundles":["@deepseek-ai/dsh-base","@deepseek-ai/dsh-sdk-app"],"patchReload":"startup"}}}' > /home/runner/.dsh/profiles/sdk/package.json \
    && printf '[]\n' > /home/runner/.dsh/profiles/sdk/cordis.yml \
    && printf '[]\n' > /home/runner/.dsh/profiles/sdk/cordis.patch.yml
RUN printf '{}\n' > /home/runner/.dsh/settings.yaml
COPY container_entry.mjs mailbox_proxy.mjs container_profile.yml /opt/companion/
ENV HOME=/home/runner DSH_HOME=/home/runner/.dsh
USER 10001:10001
WORKDIR /workspace
