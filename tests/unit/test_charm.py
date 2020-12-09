# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import patch

from charm import OpenLDAPK8sCharm
from collections import namedtuple
from ops import testing
from ops.model import (
    ActiveStatus,
    WaitingStatus,
)

from unittest.mock import MagicMock

CONFIG_ALL = {
    'image_path': 'example.com/openldap:latest',
    'image_username': 'image_user',
    'image_password': 'image_pass',
}

CONFIG_IMAGE_NO_CREDS = {
    'image_path': 'example.com/openldap:latest',
    'image_username': '',
    'image_password': '',
}

CONFIG_IMAGE_NO_IMAGE = {
    'image_path': '',
    'image_username': '',
    'image_password': '',
}

CONFIG_IMAGE_NO_PASSWORD = {
    'image_path': 'example.com/openldap:latest',
    'image_username': 'production',
    'image_password': '',
}

DB_URI = {
    'dbname': 'openldap',
    'user': 'ldap_user',
    'password': 'ldap_password',
    'host': '1.1.1.1',
    'port': '5432',
}


class TestOpenLDAPK8sCharmHooksDisabled(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(OpenLDAPK8sCharm)
        self.harness.begin()
        self.harness.disable_hooks()

    def test_make_pod_config(self):
        """Make basic, correct pod config."""
        self.harness.update_config(CONFIG_IMAGE_NO_CREDS)
        self.harness.charm._state.postgres = DB_URI
        expected = {
            'POSTGRES_NAME': 'openldap',
            'POSTGRES_USER': 'ldap_user',
            'POSTGRES_PASSWORD': 'ldap_password',
            'POSTGRES_HOST': '1.1.1.1',
            'POSTGRES_PORT': '5432',
            'LDAP_ADMIN_PASSWORD': 'badmin_password',
        }
        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            self.assertEqual(self.harness.charm._make_pod_config(), expected)

    def test_make_pod_spec(self):
        """Basic, correct pod spec."""
        self.harness.update_config(CONFIG_ALL)
        self.harness.charm._state.postgres = DB_URI
        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            expected = {
                'version': 3,
                'containers': [
                    {
                        'name': 'openldap',
                        'imageDetails': {
                            'imagePath': 'example.com/openldap:latest',
                            'username': 'image_user',
                            'password': 'image_pass',
                        },
                        'ports': [{'containerPort': 389, 'protocol': 'TCP'}],
                        'envConfig': self.harness.charm._make_pod_config(),
                        'kubernetes': {
                            'readinessProbe': {'tcpSocket': {'port': 389}},
                        },
                    }
                ],
            }
            self.assertEqual(self.harness.charm._make_pod_spec(), expected)

    def test_make_pod_spec_no_image_creds(self):
        self.harness.update_config(CONFIG_IMAGE_NO_CREDS)
        self.harness.charm._state.postgres = DB_URI
        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            expected = {
                'version': 3,
                'containers': [
                    {
                        'name': 'openldap',
                        'imageDetails': {
                            'imagePath': 'example.com/openldap:latest',
                        },
                        'ports': [{'containerPort': 389, 'protocol': 'TCP'}],
                        'envConfig': self.harness.charm._make_pod_config(),
                        'kubernetes': {
                            'readinessProbe': {'tcpSocket': {'port': 389}},
                        },
                    }
                ],
            }
            self.assertEqual(self.harness.charm._make_pod_spec(), expected)

    def test_configure_pod_no_postgres_relation(self):
        """Check that we block correctly without a Postgres relation."""
        mock_event = MagicMock()

        self.harness.update_config(CONFIG_ALL)
        expected = WaitingStatus('Waiting for database relation')
        self.harness.charm._configure_pod(mock_event)
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_configure_pod_not_leader(self):
        """Test pod config as a non-leader."""
        mock_event = MagicMock()

        self.harness.update_config(CONFIG_ALL)
        self.harness.charm._state.postgres = DB_URI
        expected = ActiveStatus()
        self.harness.charm._configure_pod(mock_event)
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_configure_pod(self):
        """Test pod configuration with everything working appropriately."""
        mock_event = MagicMock()

        self.harness.update_config(CONFIG_ALL)
        self.harness.charm._state.postgres = DB_URI
        self.harness.set_leader(True)
        expected = ActiveStatus()
        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            self.harness.charm._configure_pod(mock_event)
            self.assertEqual(self.harness.charm.unit.status, expected)

    def test_on_database_relation_joined(self):
        mock_event = MagicMock()

        self.harness.update_config(CONFIG_ALL)
        self.harness.set_leader(True)
        expected = "openldap"
        self.harness.charm._on_database_relation_joined(mock_event)
        self.assertEqual(mock_event.database, expected)

    def test_on_master_changed(self):
        mock_event = MagicMock()

        self.harness.update_config(CONFIG_ALL)
        self.harness.set_leader(True)
        master = namedtuple('master', ['dbname', 'user', 'password', 'host', 'port'])
        master.dbname = "openldap"
        master.user = "ldap_user"
        master.password = "ldap_password"
        master.host = "1.1.1.1"
        master.port = "5432"
        mock_event.master = master
        mock_event.database = "openldap"

        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            self.harness.charm._on_master_changed(mock_event)
            self.assertEqual(self.harness.charm._state.postgres['dbname'], "openldap")

    def test_on_get_admin_password_action(self):
        mock_event = MagicMock()

        self.harness.update_config(CONFIG_ALL)
        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            self.harness.charm._on_get_admin_password_action(mock_event)
            mock_event.set_results.assert_called_with({"admin-password": "badmin_password"})
            # And now return an empty result.
            get_admin_password.return_value = ""
            mock_event.reset_mock()
            self.harness.charm._on_get_admin_password_action(mock_event)
            mock_event.fail.assert_called_with("LDAP admin password has not yet been set, please retry later.")
