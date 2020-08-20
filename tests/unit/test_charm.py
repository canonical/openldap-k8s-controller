# Copyright 2020 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest

from charm import OpenLDAPK8sCharm
from ops import testing

CONFIG_ALL = {
    'image_path': 'example.com/openldap:latest',
    'image_username': 'image_user',
    'image_password': 'image_pass',
    'admin_password': 'badmin_password',
}

CONFIG_IMAGE_NO_CREDS = {
    'image_path': 'example.com/openldap:latest',
    'image_username': '',
    'image_password': '',
    'admin_password': 'badmin_password',
}

CONFIG_IMAGE_NO_IMAGE = {
    'image_path': '',
    'image_username': '',
    'image_password': '',
    'admin_password': 'badmin_password',
}

CONFIG_IMAGE_NO_PASSWORD = {
    'image_path': 'example.com/openldap:latest',
    'image_username': 'production',
    'image_password': '',
    'admin_password': 'badmin_password',
}

CONFIG_NO_ADMIN_PASSWORD = {
    'image_path': 'example.com/openldap:latest',
    'image_username': 'production',
    'image_password': '',
}

DB_URI = {
    'db_name': 'openldap',
    'db_user': 'ldap_user',
    'db_password': 'ldap_password',
    'db_host': '1.1.1.1',
    'db_port': '5432',
}


class TestOpenLDAPK8sCharmHooksDisabled(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(OpenLDAPK8sCharm)
        self.harness.begin()
        self.harness.disable_hooks()

    def test_check_for_config_problems(self):
        """Config problems as a string."""
        self.harness.update_config(CONFIG_NO_ADMIN_PASSWORD)
        expected = 'required setting(s) empty: admin_password'
        self.assertEqual(self.harness.charm._check_for_config_problems(), expected)

    def test_make_pod_config(self):
        """Make basic, correct pod config."""
        self.harness.update_config(CONFIG_IMAGE_NO_CREDS)
        self.harness.charm._state.db_name = 'openldap'
        self.harness.charm._state.db_user = 'ldap_user'
        self.harness.charm._state.db_password = 'ldap_password'
        self.harness.charm._state.db_host = '1.1.1.1'
        self.harness.charm._state.db_port = '5432'
        expected = {
            'POSTGRES_NAME': 'openldap',
            'POSTGRES_USER': 'ldap_user',
            'POSTGRES_PASSWORD': 'ldap_password',
            'POSTGRES_HOST': '1.1.1.1',
            'POSTGRES_PORT': '5432',
            'LDAP_ADMIN_PASSWORD': 'badmin_password',
        }
        self.assertEqual(self.harness.charm._make_pod_config(), expected)

    def test_make_pod_config_no_password(self):
        """Missing admin password in config shouldn't explode at least."""
        self.harness.update_config(CONFIG_NO_ADMIN_PASSWORD)
        self.harness.charm._state.db_name = 'openldap'
        self.harness.charm._state.db_user = 'ldap_user'
        self.harness.charm._state.db_password = 'ldap_password'
        self.harness.charm._state.db_host = '1.1.1.1'
        self.harness.charm._state.db_port = '5432'
        expected = {
            'POSTGRES_NAME': 'openldap',
            'POSTGRES_USER': 'ldap_user',
            'POSTGRES_PASSWORD': 'ldap_password',
            'POSTGRES_HOST': '1.1.1.1',
            'POSTGRES_PORT': '5432',
        }
        self.assertEqual(self.harness.charm._make_pod_config(), expected)

    def test_make_pod_spec(self):
        """Basic, correct pod spec."""
        self.harness.update_config(CONFIG_ALL)
        self.harness.charm._state.db_name = 'openldap'
        self.harness.charm._state.db_user = 'ldap_user'
        self.harness.charm._state.db_password = 'ldap_password'
        self.harness.charm._state.db_host = '1.1.1.1'
        self.harness.charm._state.db_port = '5432'
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
                    'kubernetes': {'readinessProbe': {'tcpSocket': {'port': 389}},},
                }
            ],
        }
        self.assertEqual(self.harness.charm._make_pod_spec(), expected)
