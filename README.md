FEAT => F3AT => Flumotion Asynchronous Autonomous Agent Toolkit

=== Important ===
This project is deprecated and abandoned by its original authors.

This is a forked version that we maintain within GetFinancing for our legacy services.

=== Repository ===

Get the code::

    git clone --recursive git@github.com:f3at/feat.git
    cd feat

If you forgot the parameter "--recursive", then you should do::

    git submodule init
    git submodule update


=== Make Commands ===

From source directory.

To run the tests::

    cd src
    make


To check coverage::

    make coverage

To check local commits before pushing::

    make check-commit

To check PEP8:

    make check-local-pep8

=== Buildbot ===

You can check the state of the builds in our public buildbot:
    http://build.fluendo.com:8075/waterfall
