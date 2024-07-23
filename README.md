jupyter-jchannel
================

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/jupyter-jchannel)](https://devguide.python.org/versions/)
[![PyPI - Version](https://img.shields.io/pypi/v/jupyter-jchannel)](https://pypi.org/project/jupyter-jchannel/)
[![Coverage Status](https://coveralls.io/repos/github/hashiprobr/jupyter-jchannel/badge.svg)](https://coveralls.io/github/hashiprobr/jupyter-jchannel)
[![Read the Docs](https://readthedocs.org/projects/jupyter-jchannel/badge/)](http://jupyter-jchannel.readthedocs.io)

**Simple asynchronous RPC framework for Jupyter Notebooks. Facilitates calling
JavaScript frontend code from Python kernel code and vice-versa.**


What?
-----

Suppose a Jupyter Notebook client (for example, a tab in Google Chrome or Visual
Studio Code) provides a JavaScript object whose methods you want to call from
its corresponding Python kernel. For example, an object that wraps the
[padStart](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String/padStart)
and
[padEnd](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/String/padEnd)
string methods to provide indentation utilities (this is admittedly useless, but
indulge me for the sake of the example).

``` js
example = {
    indentLeft(line, count) {
        return line.padStart(line.length + count);
    },
    indentRight(line, count) {
        return line.padEnd(line.length + count);
    },
};
```

The jupyter-jchannel framework allows you to create `channel` objects that make
these calls as simple as

* `channel.call('indentLeft', 'hello', 4)`;

* `channel.call('indentRight', 'world', 4)`.

These objects perform asynchronous non-blocking communication based on
[aiohttp](https://github.com/aio-libs/aiohttp). The `call` method returns a
[task](https://docs.python.org/3/library/asyncio-task.html#asyncio.Task) that
can be awaited to retrieve the result whenever you want.

![](https://raw.githubusercontent.com/hashiprobr/jupyter-jchannel/main/docs/images/notebook_capture_1.png)

In particular, awaiting immediately ensures synchronous execution, without the
need for sleeping and/or polling.

![](https://raw.githubusercontent.com/hashiprobr/jupyter-jchannel/main/docs/images/notebook_capture_2.png)

Furthermore, if the frontend throws a JavaScript exception, the task wraps it
into a Python exception.

![](https://raw.githubusercontent.com/hashiprobr/jupyter-jchannel/main/docs/images/notebook_capture_3.png)

Likewise, suppose the kernel provides an object whose methods you want to call
from the client.

``` py
class Example:
    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        return a / b
```

The `channel` objects have client representations that make these calls equally
as simple.

![](https://raw.githubusercontent.com/hashiprobr/jupyter-jchannel/main/docs/images/console_capture_1.png)

### Main features

* Robustness to client refreshes and crashes: as long as the kernel is not
  restarted, the channels reconnect automatically.

* Support for sending anything JSON-serializable as an argument and receiving
  anything JSON-serializable as the return value.

* Support for sending a binary stream as an argument and receiving a binary
  stream as the return value.

* Compatibility with NbClassic, Notebook 7+, and JupyterLab without extensions.

* Compatibility with multiple browsers and Visual Studio Code.

* Compatibility with Binder and Google Colab.

### Getting started

The [tutorial for local
notebooks](https://github.com/hashiprobr/jupyter-jchannel/blob/main/examples/local.ipynb)
should be enough to introduce the basic usage.

Remote notebooks require tunneling. Tutorials for Binder and Colab are available
below.

[![Launch in Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/hashiprobr/jupyter-jchannel/main?labpath=examples%2Fbinder.ipynb)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/hashiprobr/jupyter-jchannel/blob/master/examples/colab.ipynb)


Why?
----

This framework has been developed to overcome limitations of current
alternatives.

* The
  [`IPython.display`](https://ipython.readthedocs.io/en/stable/api/generated/IPython.display.html#module-IPython.display)
  module can call JavaScript frontend code from Python kernel code, but cannot
  retrieve the result or ensure synchronous execution.

* The `Jupyter` frontend object can call Python kernel code and register a
  callback, but is not exposed in newer platforms like Notebook 7+ and
  JupyterLab.

* The Jupyter messaging system can send [custom
  messages](https://jupyter-client.readthedocs.io/en/latest/messaging.html#custom-messages)
  from kernels to frontends and vice-versa, but its API changed between older
  platforms like NbClassic and newer platforms. Furthermore, this system assumes
  that a kernel can be connected to multiple clients. This causes ambiguity for
  RPCs:

  + if a kernel makes a call, should it be handled by all the clients or only
    one client?

  + if it is all clients, should the kernel receive multiple return values?

  + if it is one client, which should be chosen?

* The [ipywidgets](https://github.com/jupyter-widgets/ipywidgets) framework
  abstracts the Jupyter messaging system across different platforms and avoids
  ambiguity by synchronizing all clients with a single model, but this
  introduces an unnecessary overhead for kernels that are not connected to
  multiple clients. Furthermore, changing and watching model states to simulate
  arguments and return values feels like an abuse of the concept.

It should be noted that jupyter-jchannel does not remove these limitations,
since they have good reasons to exist. It merely circumvents them, while
introducing limitations of its own. It is not a solution, but another
alternative that might be adequate for some users.


How?
----

As mentioned above, the Jupyter messaging system assumes that a kernel can be
connected to multiple clients. The kernel connects to a server via
[ØMQ](https://zeromq.org/) and the server connects to the clients via HTTP and
WebSockets. This decoupling is what makes extensions like [Jupyter Real-Time
Collaboration](https://github.com/jupyterlab/jupyter-collaboration) possible.

> ![](https://raw.githubusercontent.com/hashiprobr/jupyter-jchannel/main/docs/images/notebook_components_2.drawio.png)
>
> *Source: adapted from [The Jupyter Notebook Interface](https://docs.jupyter.org/en/latest/projects/architecture/content-architecture.html#the-jupyter-notebook-interface)*

The jupyter-jchannel framework deliberately breaks this architecture by
establishing a direct connection between the kernel and a single client, on a
"first come, only served" basis. In other words, it explicitly assumes that the
user is not interested in synchronizing multiple clients.

> ![](https://raw.githubusercontent.com/hashiprobr/jupyter-jchannel/main/docs/images/notebook_components_3.drawio.png)


Why not?
--------

Since this framework deliberately breaks the Jupyter architecture, it is not
adequate for all users:

* connecting multiple clients is not possible, unless you establish that one of
  them is more important than the others;

* real-time collaboration is completely impossible;

* the jupyter-jchannel connection requires an additional port, which is a
  security issue in non-containerized remote notebooks;

* remote notebooks require tunneling, which is not always allowed.
