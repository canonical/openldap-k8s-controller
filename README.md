# OpenLDAP Charm

## Overview

This charm provides a basic OpenLDAP server using the SQL backend.

This is a k8s workload charm and can only be deployed to to a Juju k8s
cloud, attached to a controller using `juju add-k8s`.

## Usage

See config option descriptions in config.yaml.

After deploying this charm, you will need to create a relation to a PostgreSQL
database to provide backend storage for OpenLDAP.

### Developing

Notes for deploying a test setup locally using microk8s:

    sudo snap install juju --classic
    sudo snap install juju-wait --classic
    sudo snap install microk8s --classic
    sudo snap alias microk8s.kubectl kubectl
    sudo snap install charmcraft
    git clone https://git.launchpad.net/charm-k8s-openldap
    make -C charm-k8s-openldap openldap.charm

    microk8s.reset  # Warning! Clean slate!
    microk8s.enable dns dashboard registry storage
    microk8s.status --wait-ready
    microk8s.config | juju add-k8s myk8s --client

    # Build your OpenLDAP image
    make image-build
    docker push localhost:32000/openldap

    juju bootstrap myk8s
    juju add-model openldap-test
    juju deploy ./charm-k8s-openldap/openldap.charm --config openldap_image_path=localhost:32000/openldap:latest openldap
    juju wait
    juju status

The charm will not function without a database, so you will need to
deploy `cs:postgresql` somewhere.

If postgresql is deployed in the same model you plan to use for
openldap, simply use `juju relate openldap postgresql:db`.  (This
deployment style is recommended for testing purposes only.)

Cross-model relations are also supported.  Create a suitable model on
a different cloud, for example, LXD or OpenStack.

    juju switch database
    juju deploy cs:postgresql
    juju offer postgresql:db

In most k8s deployments, traffic to external services from worker pods
will be SNATed by some part of the infrastructure.  You will need to
know what the source addresses or address range is for the next step.

    juju switch openldap-test
    juju find-offers  # note down offer URL; example used below:
    juju relate openldap admin/database.postgresql --via 10.9.8.0/24

(In the case of postgresql, `--via` is needed so that the charm can
configure `pga_hba.conf` to let the k8s pods connect to the database.)


## Testing

Just run `run_tests`:

    ./run_tests
