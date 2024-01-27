import pytest

from jchannel.frontend.ipython import IPythonFrontend


@pytest.fixture
def HTML(mocker):
    from jchannel.frontend import ipython
    return mocker.spy(ipython, 'HTML')


@pytest.fixture
def f():
    return IPythonFrontend()


def test_injects_file(HTML, f):
    f.inject_file('http://a/b.js')
    HTML.assert_called_once_with('<script src="http://a/b.js"></script>')


def test_injects_code(HTML, f):
    f.inject_code('a(b);')
    HTML.assert_called_once_with('<script>a(b);</script>')
