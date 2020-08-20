#!/bin/bash

echo "Running apt update and installs"
apt-get update
apt-get -y dist-upgrade
apt-get --purge autoremove -y
apt-get install -y wget unixodbc make gcc unixodbc-dev groff-base ldap-utils odbc-postgresql gettext postgresql-client

echo "Making build dir"
mkdir -p /srv/build
cd /srv/build
echo "Fetching openldap source"
wget https://www.openldap.org/software/download/OpenLDAP/openldap-release/openldap-2.4.50.tgz
tar -xvzf openldap-2.4.50.tgz
cd /srv/build/openldap-2.4.50/
echo "Configuring openldap"
/srv/build/openldap-2.4.50/configure --prefix=/usr --sysconfdir=/etc --localstatedir=/var --enable-sql --disable-bdb --disable-ndb --disable-hdb
echo "Building openldap dependencies"
make depend
echo "Building openldap"
make
echo "Installing openldap"
make install
echo "Removing build directory"
cd /srv
rm -rf /srv/build/openldap-2.4.50/
echo "Purging build dependencies"
apt-get purge -y wget make gcc groff-base unixodbc-dev
apt-get --purge autoremove -y
apt-get clean
