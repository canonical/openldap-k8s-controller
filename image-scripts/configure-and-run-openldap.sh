#!/bin/bash

# Make an encrypted version of the admin password passed into the pod, stripping newlines
export ENCRYPTED_ADMIN_PASSWORD=""
ENCRYPTED_ADMIN_PASSWORD=$(/usr/sbin/slappasswd -s "$LDAP_ADMIN_PASSWORD" | tr -d '\n')
# Substitute embedded environment variables
envsubst < /srv/image-files/slapd.conf > /etc/openldap/slapd.conf
envsubst < /srv/image-files/odbc.ini > /etc/odbc.ini
# Set up postgres connection and add metadata schema
export PGHOST=$POSTGRES_HOST
export PGPORT=$POSTGRES_PORT
export PGDATABASE=$POSTGRES_NAME
export PGUSER=$POSTGRES_USER
export PGPASSWORD=$POSTGRES_PASSWORD
export PGOPTIONS="-c client_min_messages=error"
psql < /srv/image-scripts/backsql_create.sql
/usr/libexec/slapd -d 5 -h 'ldap:/// ldapi:///' -f /etc/openldap/slapd.conf
