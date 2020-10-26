# This file rewrites exceptions caught by PyTest and makes traces involving
# pybind11 classes more readable. It e.g. replaces "<built-in method allclose
# of PyCapsule object at 0x7ffa78041090>" by "allclose" which is arguably just
# as informative and much more compact.

import pytest
import re

re1 = re.compile(r'<built-in method (\w*) of PyCapsule object at 0x[0-9a-f]*>')
re2 = re.compile(r'<bound method PyCapsule.(\w*)[^>]*>')


def patch_line(s):
    s = re1.sub(r'\1', s)
    s = re2.sub(r'\1', s)
    return s


def patch_tb(tb):  # tb: ReprTraceback
    for entry in tb.reprentries:
        entry.lines = [patch_line(l) for l in entry.lines]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.outcome == 'failed':
        if hasattr(rep.longrepr, 'chain'):
            for entry in rep.longrepr.chain:
                patch_tb(entry[0])
    return rep


def generate_fixture(variant):
    @pytest.fixture()
    def fixture():
        try:
            import mitsuba
            mitsuba.set_variant(variant)
        except Exception:
            pytest.skip('Mitsuba variant "%s" is not enabled!' % variant)
    globals()['variant_' + variant] = fixture


for variant in ['scalar_rgb', 'scalar_spectral', 'scalar_spectral_polarized',
                'scalar_mono_polarized', 'llvm_rgb',
                'llvm_spectral', 'cuda_rgb', 'cuda_spectral',
                'llvm_ad_rgb', 'cuda_ad_rgb']:
    generate_fixture(variant)
del generate_fixture


def generate_fixture_group(name, variants):
    @pytest.fixture(params=variants)
    def fixture(request):
        try:
            import mitsuba
            mitsuba.set_variant(request.param)
        except Exception:
            pytest.skip('Mitsuba variant "%s" is not enabled!' % request.param)
        return request.param
    globals()['variants_' + name] = fixture

variant_groups = {
    'scalar_all' : ['scalar_rgb', 'scalar_spectral', 'scalar_mono', 'scalar_spectral_polarized'],
    'vec_rgb' : ['llvm_rgb', 'cuda_rgb'],
    'cpu_rgb' : ['scalar_rgb', 'llvm_rgb'],
    'all_rgb' : ['scalar_rgb', 'llvm_rgb', 'cuda_rgb'],
    'vec_spectral' : ['llvm_spectral', 'cuda_spectral'],
    'all_ad_rgb' : ['llvm_ad_rgb', 'cuda_ad_rgb'],
}

for name, variants in variant_groups.items():
    generate_fixture_group(name, variants)
del generate_fixture_group


def pytest_configure(config):
    markexpr = config.getoption("markexpr", 'False')
    if not 'not slow' in markexpr:
        print("""\033[93mRunning the full test suite. To skip slow tests, please run 'pytest -m "not slow"' \033[0m""")

    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with -m 'not slow')"
    )
