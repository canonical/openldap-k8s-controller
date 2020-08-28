ARG DIST_RELEASE

FROM ubuntu:${DIST_RELEASE}

LABEL maintainer="openldap-charmers@lists.launchpad.net"

ARG BUILD_DATE
ARG PKGS_TO_INSTALL

LABEL org.label-schema.build-date=${BUILD_DATE}

# Avoid interactive prompts
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

# Update all packages, remove cruft, install required packages
RUN apt-get update && apt-get -y dist-upgrade \
    && apt-get --purge autoremove -y \
    && apt-get install -y ${PKGS_TO_INSTALL}

COPY ./image-scripts/dump-environment.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/dump-environment.sh

CMD /usr/local/bin/dump-environment.sh
