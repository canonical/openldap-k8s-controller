# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for charm-k8s-openldap charm."""

import unittest
from collections import namedtuple
from unittest.mock import MagicMock, patch

from ops import testing
from ops.model import ActiveStatus, WaitingStatus

from charm import OpenLDAPK8sCharm

testing.SIMULATE_CAN_CONNECT = True

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

    def test_openldap_layer(self):
        """Test OpenLDAP Pebble layer."""
        self.harness.charm._state.postgres = DB_URI
        expected = {
            "summary": "openldap layer",
            "description": "pebble config layer for openldap",
            "services": {
                "openldap": {
                    "override": "replace",
                    "startup": "enabled",
                    "command": "/srv/image-scripts/configure-and-run-openldap.sh",
                    "environment": {
                        'POSTGRES_NAME': 'openldap',
                        'POSTGRES_USER': 'ldap_user',
                        'POSTGRES_PASSWORD': 'ldap_password',
                        'POSTGRES_HOST': '1.1.1.1',
                        'POSTGRES_PORT': '5432',
                        'LDAP_ADMIN_PASSWORD': 'badmin_password',
                    },
                }
            },
            "checks": {
                "online": {
                    "override": "replace",
                    "level": "ready",
                    "tcp": {
                        "port": 389,
                    },
                },
            },
        }
        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            self.assertEqual(self.harness.charm._openldap_layer(), expected)

    def test_pwgen(self):
        """Test we produce a password of specified length."""
        first_pw_run = self.harness.charm._pwgen(40)
        self.assertEqual(len(first_pw_run), 40)

        second_pw_run = self.harness.charm._pwgen(40)
        self.assertEqual(len(second_pw_run), 40)

        self.assertFalse(first_pw_run == second_pw_run)

    def test_configure_pod_no_postgres_relation(self):
        """Check that we block correctly without a Postgres relation."""
        mock_event = MagicMock()

        expected = WaitingStatus('Waiting for database relation')
        self.harness.charm._on_config_changed(mock_event)
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_configure_pod_not_leader(self):
        """Test pod config as a non-leader."""
        mock_event = MagicMock()

        self.harness.charm._state.postgres = DB_URI
        expected = ActiveStatus()
        self.harness.charm._on_config_changed(mock_event)
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_configure_pod(self):
        """Test pod configuration with everything working appropriately."""
        mock_event = MagicMock()

        expected = {
            "summary": "openldap layer",
            "description": "pebble config layer for openldap",
            "services": {
                "openldap": {
                    "override": "replace",
                    "startup": "enabled",
                    "command": "/srv/image-scripts/configure-and-run-openldap.sh",
                    "environment": {
                        'POSTGRES_NAME': 'openldap',
                        'POSTGRES_USER': 'ldap_user',
                        'POSTGRES_PASSWORD': 'ldap_password',
                        'POSTGRES_HOST': '1.1.1.1',
                        'POSTGRES_PORT': '5432',
                        'LDAP_ADMIN_PASSWORD': 'badmin_password',
                    },
                }
            },
            "checks": {
                "online": {
                    "override": "replace",
                    "level": "ready",
                    "tcp": {
                        "port": 389,
                    },
                },
            },
        }

        self.harness.charm._state.postgres = DB_URI
        self.harness.set_leader(True)
        expected_status = ActiveStatus()
        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            self.harness.container_pebble_ready('openldap')
            self.harness.charm._on_config_changed(mock_event)
            self.assertEqual(self.harness.charm.unit.status, expected_status)
            self.assertEqual(self.harness.charm._openldap_layer(), expected)
            self.harness.update_config({"container_port": 567})
            self.harness.charm._on_config_changed(mock_event)
            expected["checks"]["online"]["tcp"]["port"] = 567
            self.assertEqual(self.harness.charm.unit.status, expected_status)
            self.assertEqual(self.harness.charm._openldap_layer(), expected)

    def test_on_database_relation_joined(self):
        mock_event = MagicMock()

        self.harness.set_leader(True)
        expected = "openldap"
        self.harness.charm._on_database_relation_joined(mock_event)
        self.assertEqual(mock_event.database, expected)

    def test_on_database_relation_broken(self):
        mock_event = MagicMock()

        self.harness.set_leader(True)
        expected = WaitingStatus('Waiting for database relation')
        self.harness.charm._on_database_relation_broken(mock_event)
        self.assertEqual(self.harness.charm.unit.status, expected)

    def test_on_master_changed(self):
        mock_event = MagicMock()

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

        with patch.object(self.harness.charm, "get_admin_password") as get_admin_password:
            get_admin_password.return_value = 'badmin_password'
            self.harness.charm._on_get_admin_password_action(mock_event)
            mock_event.set_results.assert_called_with({"admin-password": "badmin_password"})
            # And now return an empty result.
            get_admin_password.return_value = ""
            mock_event.reset_mock()
            self.harness.charm._on_get_admin_password_action(mock_event)
            mock_event.fail.assert_called_with("LDAP admin password has not yet been set, please retry later.")
