ARG DIST_RELEASE

FROM ubuntu:${DIST_RELEASE}

LABEL maintainer="openldap-charmers@lists.launchpad.net"

ARG BUILD_DATE
ARG LDAP_VERSION

LABEL org.label-schema.build-date=${BUILD_DATE}
# Used in Launchpad OCI Recipe build to tag the image.
LABEL org.label-schema.version=${LDAP_VERSION}

# Avoid interactive prompts
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

COPY image-scripts /srv/image-scripts

COPY image-files /srv/image-files

RUN /srv/image-scripts/build-openldap.sh ${LDAP_VERSION}

EXPOSE 389/tcp

CMD /srv/image-scripts/configure-and-run-openldap.sh
