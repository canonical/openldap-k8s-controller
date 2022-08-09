# OpenLDAP Operator

## Overview

This charm provides an OpenLDAP server using the SQL backend.

## Usage

For details on using Kubernetes with Juju [see here](https://juju.is/docs/kubernetes), and for
details on using Juju with MicroK8s for easy local testing [see here](https://juju.is/docs/microk8s-cloud).

To deploy this charm with both OpenLDAP and PostgreSQL inside a k8s model, run:

    juju deploy cs:~openldap-charmers/openldap
    juju deploy cs:~postgresql-charmers/postgresql-k8s postgresql
    juju add-relation openldap:db postgresql:db

To retrieve the auto-generated LDAP admin password, run, assuming you're using
Juju 2.x:

    juju run-action openldap/0 --wait get-admin-password

For further details, [see here](https://charmhub.io/openldap-charmers-openldap/docs).

## Development environment

To set up an initial development environment:
    
    ```bash
    git clone git+ssh://git.launchpad.net/charm-k8s-openldap
    cd charm-k8s-openldap
    virtualenv venv
    . venv/bin/activate
    pip install -r requirements-dev.txt
    sudo apt install -y tox
    tox -e unit
    ```

