# OpenLDAP Operator

## Overview

This charm provides an OpenLDAP server using the SQL backend.

## Usage

For details on using Kubernetes with Juju [see here](https://juju.is/docs/kubernetes), and for
details on using Juju with MicroK8s for easy local testing [see here](https://juju.is/docs/microk8s-cloud).

To deploy this charm with both OpenLDAP and PostgreSQL inside a k8s model, run:

    juju deploy openldap-k8s
    juju deploy postgresql-k8s
    juju relate openldap:db postgresql-k8s:db

To retrieve the auto-generated LDAP admin password, run:

    juju run-action openldap/0 --wait get-admin-password

For further details, [see here](https://charmhub.io/openldap-charmers-openldap/docs).
