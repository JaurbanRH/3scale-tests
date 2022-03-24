"""
    Smoke test that will create 3scale objects for performance testing.
    Fill necessary data to benchmark template.
    Run the test and assert results.
    This test shows usage how to write test where access token is created by performance test.
"""
import os
from urllib.parse import urlparse

import backoff
import pytest

from testsuite import rawobj
from testsuite.perf_utils import HyperfoilUtils
from testsuite.rhsso.rhsso import OIDCClientAuthHook

MAX_RUN_TIME = 4 * 60

pytestmark = [pytest.mark.performance]


@pytest.fixture(scope="module", autouse=True)
def rhsso_setup(lifecycle_hooks, rhsso_service_info):
    """Have application/service with RHSSO auth configured"""
    lifecycle_hooks.append(OIDCClientAuthHook(rhsso_service_info))


@pytest.fixture(scope='module')
def services(services):
    """Service fixture will add '/' POST mapping rule, so we can make such requests in perf-test"""
    for svc in services:
        metric = svc.metrics.list()[0]
        svc.proxy.list().mapping_rules.create(rawobj.Mapping(metric, "/", "POST"))
        svc.proxy.deploy()
    return services


@pytest.fixture(scope='module')
def template(root_path):
    """Path to template"""
    return os.path.join(root_path, 'smoke/template_rhsso_tokens.hf.yaml')


@pytest.fixture(scope='module')
def setup_benchmark(hyperfoil_utils, promoted_services, applications, rhsso_service_info, shared_template):
    """Setup of benchmark. It will add necessary host connections, csv data and files."""
    hyperfoil_utils.add_hosts(promoted_services, shared_connections=20)
    hyperfoil_utils.add_host(
        urlparse(rhsso_service_info.rhsso.server_url)._replace(path="").geturl(), shared_connections=100)
    hyperfoil_utils.add_token_creation_data(rhsso_service_info, applications, 'rhsso_auth.csv')
    hyperfoil_utils.add_file(HyperfoilUtils.message_1kb)
    hyperfoil_utils.add_shared_template(shared_template)
    return hyperfoil_utils


@backoff.on_predicate(backoff.constant, lambda x: not x.is_finished(), interval=5, max_time=MAX_RUN_TIME)
def wait_run(run):
    """Waits for the run to end"""
    return run.reload()


def test_rhsso_tokens(applications, prod_client, setup_benchmark):
    """
        Test checks that application is setup correctly.
        Runs the created benchmark.
        Asserts it was successful.
    """
    for app in applications:
        client = prod_client(app)
        assert client.get("/0/anything").status_code == 200
        assert client.post("/0/anything").status_code == 200

    benchmark = setup_benchmark.create_benchmark()
    run = benchmark.start()

    run = wait_run(run)
    assert run.is_finished()
    stats = run.all_stats()

    assert stats
    assert stats.get('info', {}).get('errors') == []
    assert stats.get('failures') == []
    assert stats.get('stats', []) != []
    assert len(stats.get('stats', [])) == 4
