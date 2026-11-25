# syntax=docker/dockerfile:1
# Apache FOP, unchanged: renders the official KoSIT XSL-FO (xr-pdf.xsl) to PDF. Used only to build the
# evaluation set (ADR-0018), never by the app. Run: see belegfluss_eval/dataset/official.py.

ARG FOP_VERSION=2.12

FROM alpine:3.24 AS fetch
ARG FOP_VERSION
# SHA-512 published by Apache (downloads.apache.org and archive.apache.org agree, 2026-11-25).
ARG FOP_SHA512=975c54953cf409b41b61fb46e6bc6c629e2a62f1d9c79c219e28fadaccb4428968fe44344cd5b5bd64b418ebd9d4522a66d98c5033d92572c7349a68fcc32e20
RUN wget -q -O /tmp/fop.tar.gz \
        "https://archive.apache.org/dist/xmlgraphics/fop/binaries/fop-${FOP_VERSION}-bin.tar.gz" \
    && echo "${FOP_SHA512}  /tmp/fop.tar.gz" | sha512sum -c - \
    && mkdir /fetch && tar -xzf /tmp/fop.tar.gz -C /fetch \
    && mv "/fetch/fop-${FOP_VERSION}" /fetch/fop && chmod -R a+rX /fetch/fop

FROM eclipse-temurin:21-jre
ARG FOP_VERSION
LABEL org.opencontainers.image.title="belegfluss-eval-fop" \
      org.opencontainers.image.description="Apache FOP ${FOP_VERSION} for rendering the evaluation set"
COPY --from=fetch /fetch/fop /opt/fop
RUN useradd --system --uid 10003 --home-dir /nonexistent --shell /usr/sbin/nologin fop
USER fop
WORKDIR /work
ENTRYPOINT ["/opt/fop/fop/fop"]
