
# compiling/testing
To test these things, you will need to setup an environment, and then run
the test. This module depends on a custom variant of pyserial that contains vid/pid scanning for Linux/Windows/OSX, and therefore is best run in a virtualenv to avoid conflict with other pyserial versions

To setup the virtual envrionment test environment
```
. ./setup.sh  
```

If using the virtual environment,  you will need to activate it before any testing or use of the module. I have included the 'activate' in each test below, but you only need to run it once. When a virtual environemnt is active, your shell will have the prefix of (virtualenv) 

Run unit tests
```
s3g/> . ./setup.sh
(virtuanenv)s3g/> python unit_tests.py
```

Running post-install tests. If you install this as an installer, or manually
this will quickly verify your install is OK and likely to work properly
```
s3g/> . ./setup.sh
(virtuanenv)s3g/> python pi_tests.py
```

# building an egg
To build an egg from this project:
python -c "import setuptools; execfile('setup.py')" bdist_egg
