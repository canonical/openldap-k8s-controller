#!/bin/bash
LDAP_VERSION="2.4.50"

echo "Running apt update and installs"
apt-get update
apt-get -y dist-upgrade
apt-get --purge autoremove -y
apt-get install -y wget unixodbc make gcc unixodbc-dev groff-base ldap-utils odbc-postgresql gettext postgresql-client

echo "Making build dir"
mkdir -p /srv/build
cd /srv/build || exit
echo "Fetching openldap source"
wget https://www.openldap.org/software/download/OpenLDAP/openldap-release/openldap-$LDAP_VERSION.tgz
tar -xvzf openldap-$LDAP_VERSION.tgz
cd /srv/build/openldap-$LDAP_VERSION/ || exit
echo "Configuring openldap"
/srv/build/openldap-$LDAP_VERSION/configure --prefix=/usr --sysconfdir=/etc --localstatedir=/var --enable-sql --disable-bdb --disable-ndb --disable-hdb
echo "Building openldap dependencies"
make depend
echo "Building openldap"
make
echo "Installing openldap"
make install
echo "Removing build directory"
cd /srv || exit
rm -rf /srv/build/openldap-$LDAP_VERSION/
echo "Purging build dependencies"
apt-get purge -y wget make gcc groff-base unixodbc-dev
apt-get --purge autoremove -y
apt-get clean
