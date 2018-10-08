PYTHON = python
top_srcdir = src
COVERAGE_MODULES = feat
TOOLS = tools
TRIAL = ${TOOLS}/flumotion-trial
PEP8 = ${TOOLS}/pep8.py --repeat
SHOW_COVERAGE = ${TOOLS}/show-coverage.py
GIT_REVISION = $(shell git describe || echo 'unknown')

clean: clean-build clean-pyc clean-test ##@build remove all build, test, coverage and Python artifacts

clean-build: ##@build remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ##@build remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ##@build remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache


check-local: check-tests check-local-pep8

check-local-pep8:
	find $(top_srcdir) -name \*.py | grep -v extern | \
	sort -u | xargs $(PYTHON) $(PEP8)

pyflakes:
	find $(top_srcdir) -name \*.py | grep -v extern | \
	sort -u | xargs pyflakes

pychecker:
	find $(top_srcdir) -name \*.py | grep -v extern | \
	sort -u | xargs pychecker

check-tests:
	$(PYTHON) $(TRIAL) $(TRIAL_FLAGS) $(COVERAGE_MODULES)

check-tests-fast:
	@make check-tests \
	   TRIAL_FLAGS="--skip-slow"

check-doc: doc/reference/html/index.html

check-zip:
	-make check-tests FEAT_DEBUG=4 > test.out 2>&1
	-rm -r check
	mkdir -p check
	-mv test.out check
	-mv _trial_temp check
	-mv test.log check
	git describe > check/feat.gitversion
	zip -r check-$(GIT_REVISION).zip check


doc/reference/html/index.html: Makefile src
	epydoc feat -o doc/reference/html -v --fail-on-warning | $(PYTHON) common/epyfilter.py common/efc.py

docs:
	@-rm doc/reference/html/index.html
	make doc/reference/html/index.html

coverage:
	@test ! -z "$(COVERAGE_MODULES)" ||				\
	(echo Define COVERAGE_MODULES in your Makefile; exit 1)
	rm -f feat-saved-coverage.pickle
	$(PYTHON) $(TRIAL) --temp-directory=_trial_coverage --coverage --saved-coverage=feat-saved-coverage.pickle $(COVERAGE_MODULES)
	make show-coverage

show-coverage:
	@test ! -z "$(COVERAGE_MODULES)" ||				\
	(echo Define COVERAGE_MODULES in your Makefile; exit 1)
	@keep="";							\
	for m in $(COVERAGE_MODULES); do				\
		echo adding $$m;					\
		keep="$$keep `ls _trial_coverage/coverage/$$m*`";	\
	done;								\
	$(PYTHON) $(SHOW_COVERAGE) $$keep

check-fast:
	@make check-commit \
	  TRIAL_FLAGS="--skip-slow"

check-commit:
	current=`pwd`;							\
        repo=`pwd`;							\
	reponame=`basename $$current`;					\
	dst=/tmp/$$reponame;						\
	if test -d $$dst; then						\
	(echo Removing old $$dst; rm -rf $$dst);			\
	fi;								\
	cd /tmp;							\
	git clone --recursive --depth 0 $$repo;				\
	cd $$reponame;							\
	make check-local;						\
	cd $$current;							\
	rm -rf $$dst;

targz:
	python setup.py sdist
	mv dist/feat-*.tar.gz .

rpm:    el6

el6:    targz
	mach -k -r c6l64 build feat.spec
