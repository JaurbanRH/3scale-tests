"""
Tests upstream mTLS policy with standard gateway, which enables mTLS between APIcast and upstream api (httpbin)

It uses two configuration of custom deployed Httpbin:
First with matching certificates and authorities, which should succeed with 200
Second with mismatched certificates, which should fail with 502 due to httpbin refusing to accept the other certificate

It tests only embedded type as path requires manipulation with the deployment
"""
import pytest

import testsuite.gateways as gateways
from testsuite import rawobj
from testsuite.certificates import Certificate
from testsuite.tests.apicast.policy.tls import embedded


@pytest.fixture(scope="session")
def invalid_authority(request, configuration) -> Certificate:
    """To be used in tests validating server certificates"""
    certificate_authority = configuration.manager.get_or_create_ca("invalid_ca", hosts=["*.com"])
    request.addfinalizer(certificate_authority.delete_files)
    return certificate_authority


@pytest.fixture(scope="session")
def staging_gateway(request, testconfig, configuration):
    """Standard gateway, copied from root conftest.
     Not ideal, but since I need this file in this directory, this is the least amount of code duplication I managed"""
    options = gateways.configuration.options(staging=True,
                                             settings_block=testconfig["threescale"]["gateway"]["configuration"],
                                             configuration=configuration)
    gateway = gateways.configuration.staging(options)
    request.addfinalizer(gateway.destroy)

    gateway.create()

    return gateway


@pytest.fixture(scope="module")
def policy_settings(certificate):
    """Embedded upstream mTLS policy"""
    embedded_cert = embedded(certificate.certificate, "tls.crt", "pkix-cert")
    embedded_key = embedded(certificate.key, "tls.key", "x-iwork-keynote-sffkey")
    return rawobj.PolicyConfig("upstream_mtls", {"certificate_type": "embedded",
                                                 "certificate_key_type": "embedded",
                                                 "certificate": embedded_cert,
                                                 "certificate_key": embedded_key})


def test_mtls_request(application, authority_and_code):
    """Test that mtls request returns correct status code"""
    _, code = authority_and_code
    assert application.api_client().get("/get").status_code == code