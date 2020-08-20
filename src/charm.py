#!/usr/bin/env python3
# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import logging

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
    BlockedStatus,
    MaintenanceStatus,
    WaitingStatus,
)

from interface import pgsql

logger = logging.getLogger(__name__)


REQUIRED_SETTINGS = ['admin_password']
DATABASE_NAME = 'openldap'


class OpenLDAPDBMasterAvailableEvent(EventBase):
    pass


class OpenLDAPCharmEvents(CharmEvents):
    """Custom charm events."""

    db_master_available = EventSource(OpenLDAPDBMasterAvailableEvent)


class OpenLDAPK8sCharm(CharmBase):
    _state = StoredState()

    on = OpenLDAPCharmEvents()

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.start, self.configure_pod)
        self.framework.observe(self.on.config_changed, self.configure_pod)
        self.framework.observe(self.on.leader_elected, self.configure_pod)
        self.framework.observe(self.on.upgrade_charm, self.configure_pod)

        # database
        self._state.set_default(db_name=None, db_user=None, db_password=None, db_host=None, db_port=None)
        self.db = pgsql.PostgreSQLClient(self, 'db')
        self.framework.observe(self.db.on.database_relation_joined, self._on_database_relation_joined)  # NOQA: E501
        self.framework.observe(self.db.on.master_changed, self._on_master_changed)
        self.framework.observe(self.on.db_master_available, self.configure_pod)

    def _on_database_relation_joined(self, event: pgsql.DatabaseRelationJoinedEvent):
        """Handle db-relation-joined."""
        if self.model.unit.is_leader():
            # Provide requirements to the PostgreSQL server.
            event.database = DATABASE_NAME  # Request database named mydbname
        elif event.database != DATABASE_NAME:
            # Leader has not yet set requirements. Defer, incase this unit
            # becomes leader and needs to perform that operation.
            event.defer()
            return

    def _on_master_changed(self, event: pgsql.MasterChangedEvent):
        """Handle changes in the primary database unit."""
        if event.database != DATABASE_NAME:
            # Leader has not yet set requirements. Wait until next
            # event, or risk connecting to an incorrect database.
            return

        self._state.db_name = None if event.master is None else event.master.dbname
        self._state.db_user = None if event.master is None else event.master.user
        self._state.db_password = None if event.master is None else event.master.password
        self._state.db_host = None if event.master is None else event.master.host
        self._state.db_port = None if event.master is None else event.master.port

        if event.master is None:
            return

        self.on.db_master_available.emit()

    def _check_for_config_problems(self):
        """Check for some simple configuration problems and return a
        string describing them, otherwise return an empty string."""
        problems = []

        missing = self._missing_charm_settings()
        if missing:
            problems.append('required setting(s) empty: {}'.format(', '.join(sorted(missing))))

        return '; '.join(filter(None, problems))

    def _missing_charm_settings(self):
        """Check configuration setting dependencies and return a list of
        missing settings; otherwise return an empty list."""
        config = self.model.config
        missing = []

        missing.extend([setting for setting in REQUIRED_SETTINGS if setting not in config])

        return sorted(list(set(missing)))

    def _make_pod_spec(self):
        """Return a pod spec with some core configuration."""
        config = self.model.config
        image_details = {
            'imagePath': config['image_path'],
        }
        if config['image_username']:
            image_details.update({'username': config['image_username'], 'password': config['image_password']})
        pod_config = self._make_pod_config()

        return {
            'version': 3,  # otherwise resources are ignored
            'containers': [
                {
                    'name': self.app.name,
                    'imageDetails': image_details,
                    'ports': [{'containerPort': 389, 'protocol': 'TCP'}],
                    'envConfig': pod_config,
                    'kubernetes': {'readinessProbe': {'tcpSocket': {'port': 389}},},
                }
            ],
        }

    def _make_pod_config(self):
        """Return an envConfig with some core configuration."""
        config = self.model.config
        pod_config = {
            'POSTGRES_NAME': self._state.db_name,
            'POSTGRES_USER': self._state.db_user,
            'POSTGRES_PASSWORD': self._state.db_password,
            'POSTGRES_HOST': self._state.db_host,
            'POSTGRES_PORT': self._state.db_port,
        }

        if 'admin_password' in config:
            pod_config['LDAP_ADMIN_PASSWORD'] = config['admin_password']

        return pod_config

    def configure_pod(self, event):
        """Assemble the pod spec and apply it, if possible."""
        if not self._state.db_name:
            self.unit.status = WaitingStatus('Waiting for database relation')
            event.defer()
            return

        if not self.unit.is_leader():
            self.unit.status = ActiveStatus()
            return

        problems = self._check_for_config_problems()
        if problems:
            self.unit.status = BlockedStatus(problems)
            return

        self.unit.status = MaintenanceStatus('Assembling pod spec')
        pod_spec = self._make_pod_spec()

        self.unit.status = MaintenanceStatus('Setting pod spec')
        self.model.pod.set_spec(pod_spec)
        self.unit.status = ActiveStatus()


if __name__ == "__main__":
    main(OpenLDAPK8sCharm, use_juju_for_storage=True)
