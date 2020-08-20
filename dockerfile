ARG DIST_RELEASE

FROM ubuntu:${DIST_RELEASE}

LABEL maintainer="openldap-charmers@lists.launchpad.net"

ARG BUILD_DATE

LABEL org.label-schema.build-date=${BUILD_DATE}

# Avoid interactive prompts
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

COPY image-scripts /srv/image-scripts

COPY image-files /srv/image-files

RUN /srv/image-scripts/build-openldap.sh

EXPOSE 389/tcp

CMD /srv/image-scripts/configure-and-run-openldap.sh
