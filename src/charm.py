#!/usr/bin/env python3
# Copyright 2020 Tom Haddon
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
)

logger = logging.getLogger(__name__)


REQUIRED_SETTINGS = ['admin_password']


class OpenLDAPDBMasterAvailableEvent(EventBase):
    pass


class OpenLDAPCharmEvents(CharmEvents):
    """Custom charm events."""

    db_master_available = EventSource(OpenLDAPDBMasterAvailableEvent)


class OpenLDAPK8sCharm(CharmBase):
    _stored = StoredState()

    on = OpenLDAPCharmEvents()

    def __init__(self, *args):
        super().__init__(*args)

        self.framework.observe(self.on.start, self.configure_pod)
        self.framework.observe(self.on.config_changed, self.configure_pod)
        self.framework.observe(self.on.leader_elected, self.configure_pod)
        self.framework.observe(self.on.upgrade_charm, self.configure_pod)

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
            image_details.update(
                {'username': config['image_username'], 'password': config['image_password']}
            )
        pod_config = self._make_pod_config()

        return {
            'version': 3,  # otherwise resources are ignored
            'containers': [
                {
                    'name': self.app.name,
                    'imageDetails': image_details,
                    'ports': [{'containerPort': 389, 'protocol': 'TCP'}],
                    'envConfig': pod_config,
                    'kubernetes': {
                        'readinessProbe': {'tcpSocket': {'port': 389}},
                    },
                }
            ],
        }

    def _make_pod_config(self):
        """Return an envConfig with some core configuration."""
        config = self.model.config
        pod_config = {}

        if config['admin_password']:
            pod_config['admin_password'] = config['admin_password']

        return pod_config

    def configure_pod(self, event):
        """Assemble the pod spec and apply it, if possible."""
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
    main(OpenLDAPK8sCharm)
