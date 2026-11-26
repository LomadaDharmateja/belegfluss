# syntax=docker/dockerfile:1
# Official KoSIT validator with the official XRechnung configuration, unchanged (ADR-0005).
# Daemon mode, no GUI. The daemon has no authentication: never publish its port.

ARG VALIDATOR_VERSION=1.6.3
ARG CONFIG_VERSION=2026-08-31

FROM alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf AS fetch
ARG VALIDATOR_VERSION
ARG CONFIG_VERSION
# Downloads are pinned by SHA-256 (same checksums as the M0 smoke test).
ADD --checksum=sha256:799e64befca97d4080e03608c80b85dd5a5ecc5f4ae4f35d1116ec2855b9a7c9 \
    https://github.com/itplr-kosit/validator/releases/download/v${VALIDATOR_VERSION}/validator-${VALIDATOR_VERSION}-standalone.jar \
    /fetch/validator.jar
ADD --checksum=sha256:2530cd107c414511c5d0462ec10f886910395abfca820db82e83d70bf01221a8 \
    https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/v${CONFIG_VERSION}/xrechnung-3.0.2-validator-configuration-${CONFIG_VERSION}.zip \
    /fetch/config.zip
# Files downloaded by ADD are root-only (0600); the validator runs as a non-root user.
RUN mkdir /fetch/config && unzip -q /fetch/config.zip -d /fetch/config && rm /fetch/config.zip \
    && chmod 0644 /fetch/validator.jar && chmod -R a+rX /fetch/config

FROM eclipse-temurin:25-jre@sha256:4ed132f6832e9804b123e89a849a7b4502756ae64a4ee08ebab939d9d5d0a9fa
ARG VALIDATOR_VERSION
ARG CONFIG_VERSION
LABEL org.opencontainers.image.title="belegfluss-validator" \
      org.opencontainers.image.description="KoSIT validator ${VALIDATOR_VERSION} with XRechnung configuration ${CONFIG_VERSION}"

COPY --from=fetch /fetch/validator.jar /opt/validator/validator.jar
COPY --from=fetch /fetch/config /opt/validator/config
# Security updates of the base image's OS packages (image scan, M4a).
RUN apt-get update && apt-get upgrade --yes --no-install-recommends && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10002 --home-dir /nonexistent --shell /usr/sbin/nologin validator
USER validator

# Heap is capped: without it the JVM took ~1.9 GB in a container (M0). Size measured in M2a.
ENV JAVA_OPTS="-Xmx512m"
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/8080 && printf "GET /server/health HTTP/1.0\r\n\r\n" >&3 && grep -q UP <&3'

CMD ["sh", "-c", "exec java $JAVA_OPTS -jar /opt/validator/validator.jar -s /opt/validator/config/scenarios.xml -r /opt/validator/config -D -H 0.0.0.0 -P 8080 -G"]
