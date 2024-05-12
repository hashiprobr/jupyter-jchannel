from jchannel.frontend.ipython import IPythonFrontend


def test_instantiates_with_url(mocker):
    environ = {'JCHANNEL_CLIENT_URL': 'http://localhost:8080/main.js'}
    mocker.patch.dict('jchannel.frontend.abstract.os.environ', environ)
    frontend = IPythonFrontend()
    assert frontend.url == 'http://localhost:8080/main.js'


def test_runs_twice(mocker):
    frontend = IPythonFrontend()

    def side_effect(element):
        if element == frontend.output:
            element._view_count += 1

    display = mocker.patch('jchannel.frontend.ipython.display')
    display.side_effect = side_effect

    frontend.run('a(b)')
    frontend.run('a(b)')
