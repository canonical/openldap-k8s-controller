"""Integration tests for charm-k8s-openldap."""

import asyncio
import logging

import pytest
from pytest_operator.plugin import OpsTest
from ops.model import ActiveStatus, WaitingStatus

logger = logging.getLogger(__name__)

APP_NAME = "openldap"
PSQL = "postgresql-k8s"


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest):
    openldap_charm = await ops_test.build_charm(".")
    await asyncio.gather(
        ops_test.model.deploy("postgresql-k8s", application_name=PSQL, num_units=1),
        ops_test.model.deploy(
            openldap_charm,
            resources={'openldap-image': 'openldapcharmers/openldap:2.4.50'},
            application_name=APP_NAME,
            num_units=1,
        ),
    )
    await ops_test.model.wait_for_idle(apps=[APP_NAME, PSQL])
    assert ops_test.model.applications[APP_NAME].status == WaitingStatus.name
    assert ops_test.model.applications[PSQL].status == ActiveStatus.name

    await ops_test.model.add_relation(APP_NAME + ":db", PSQL + ":db")
    await ops_test.model.wait_for_idle(apps=[APP_NAME, PSQL])
    assert ops_test.model.applications[APP_NAME].status == ActiveStatus.name
    assert ops_test.model.applications[PSQL].status == ActiveStatus.name


@pytest.mark.abort_on_fail
async def test_maintenance_without_postgresql(ops_test: OpsTest):
    await asyncio.gather(ops_test.model.applications[PSQL].remove())
    await ops_test.model.wait_for_idle(apps=[APP_NAME])
    assert ops_test.model.applications[APP_NAME].status == WaitingStatus.name
