#!/usr/bin/env python3
# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

"""OpenLDAP Charm - a sidecar charm for openldap
with the option to relate to a PostgreSQL database."""

import logging
import random
import string

import ops.lib
from ops.charm import (
    CharmBase,
    CharmEvents,
)
from ops.main import main
from ops.framework import (
    StoredState,
    EventBase,
    EventSource,
)
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
    WaitingStatus,
)
from leadership import LeadershipSettings


pgsql = ops.lib.use("pgsql", 1, "postgresql-charmers@lists.launchpad.net")

logger = logging.getLogger(__name__)


DATABASE_NAME = 'openldap'


class OpenLDAPDBMasterAvailableEvent(EventBase):
    """OpenLDAP empty handler for master available."""


class OpenLDAPCharmEvents(CharmEvents):
    """Custom charm events."""
    db_master_available = EventSource(OpenLDAPDBMasterAvailableEvent)


class OpenLDAPK8sCharm(CharmBase):
    """Charm the service as a sidecar charm.
    Gameplan:
    render a pebble layer in a func
    transfer logic to container (i.e. pebble sidecar)
    remove redundancies
    test
    refactor
    ...
    """
    _state = StoredState()

    on = OpenLDAPCharmEvents()

    def __init__(self, *args):
        super().__init__(*args)

        self.leader_data = LeadershipSettings()

        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.get_admin_password_action,
                               self._on_get_admin_password_action)

        # database
        self._state.set_default(postgres=None)
        self.db = pgsql.PostgreSQLClient(self, 'db')
        self.framework.observe(self.db.on.database_relation_joined,
                               self._on_database_relation_joined)
        self.framework.observe(self.db.on.master_changed, self._on_master_changed)

    @staticmethod
    def _pwgen(length=None):
        """Generate a random password."""
        if length is None:
            # A random length is ok to use a weak PRNG
            length = random.choice(range(35, 45))
        alphanumeric_chars = [
            letter for letter in (string.ascii_letters + string.digits)
            if letter not in 'l0QD1vAEIOUaeiou']
        # Use a crypto-friendly PRNG (e.g. /dev/urandom) for making the
        # actual password
        random_generator = random.SystemRandom()
        random_chars = [
            random_generator.choice(alphanumeric_chars) for _ in range(length)]
        return ''.join(random_chars)

    def _on_database_relation_joined(self, event: pgsql.DatabaseRelationJoinedEvent):
        """Handle db-relation-joined."""
        if self.model.unit.is_leader():
            # Provide requirements to the PostgreSQL server.
            event.database = DATABASE_NAME  # Request database named mydbname
        elif event.database != DATABASE_NAME:
            # Leader has not yet set requirements. Defer, incase this unit
            # becomes leader and needs to perform that operation.
            event.defer()

    def _on_master_changed(self, event: pgsql.MasterChangedEvent):
        """Handle changes in the primary database unit."""
        if event.database != DATABASE_NAME:
            # Leader has not yet set requirements. Wait until next
            # event, or risk connecting to an incorrect database.
            return

        self._state.postgres = None
        if event.master is None:
            return

        self._state.postgres = {
            'dbname': event.master.dbname,
            'user': event.master.user,
            'password': event.master.password,
            'host': event.master.host,
            'port': event.master.port,
        }

        self.on.db_master_available.emit()

    def _openldap_layer(self):
        """A pebble layer for OpenLDAP."""
        ldap_admin_password = self.get_admin_password()

        return {
            "summary": "openldap layer",
            "description": "pebble config layer for openldap",
            "services": {
                "openldap": {
                    "override": "replace",
                    "startup": "enabled",
                    "command": "/srv/image-scripts/configure-and-run-openldap.sh",
                    "environment": {
                        'POSTGRES_NAME': self._state.postgres['dbname'],
                        'POSTGRES_USER': self._state.postgres['user'],
                        'POSTGRES_PASSWORD': self._state.postgres['password'],
                        'POSTGRES_HOST': self._state.postgres['host'],
                        'POSTGRES_PORT': self._state.postgres['port'],
                        'LDAP_ADMIN_PASSWORD': ldap_admin_password,
                    },
                }
            },
            "checks": {
                "online": {
                    "override": "replace",
                    "level": "ready",
                    "tcp": {
                        "port": self.config["container_port"]
                    },
                },
            },
        }

    def _on_get_admin_password_action(self, event):
        """Handle on get-admin-password action."""
        admin_password = self.get_admin_password()
        if admin_password:
            event.set_results({"admin-password": self.get_admin_password()})
        else:
            event.fail("LDAP admin password has not yet been set, please retry later.")

    def get_admin_password(self):
        """Get the LDAP admin password.

        If a password hasn't been set yet, create one if we're the leader,
        or return an empty string if we're not."""
        admin_password = self.leader_data["admin_password"]
        if not admin_password:
            # TODO make a test here to see whether we shouldn't call the function
            if self.unit.is_leader:
                admin_password = self._pwgen(40)
                self.leader_data["admin_password"] = admin_password
        return admin_password

    def _on_config_changed(self, event):
        """Reconfigure service."""
        if not self._state.postgres:
            self.unit.status = WaitingStatus('Waiting for database relation')
            event.defer()
            return

        if not self.unit.is_leader():
            self.unit.status = ActiveStatus()
            return

        container = self.unit.get_container("openldap")
        layer = self._openldap_layer()

        if container.can_connect():
            services = container.get_plan().to_dict().get("services", {})
            if services != layer["services"]:
                self.unit.status = MaintenanceStatus("adjusting workload container")
                container.add_layer("openldap", layer, combine=True)
                container.restart("openldap")
            self.unit.status = ActiveStatus()
        else:
            self.unit.status = WaitingStatus("waiting for Pebble in workload continer")


if __name__ == "__main__":
    main(OpenLDAPK8sCharm, use_juju_for_storage=True)
