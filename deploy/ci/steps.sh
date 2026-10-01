#!/bin/bash
##### CI steps shared by GitHub Actions
# Each step runs the same commands as .circleci/config.yml, so the two CI
# systems can be compared side by side. Usage: deploy/ci/steps.sh <step>

set -e

cd "$(dirname "$0")/../.."
mkdir -p build/logs

case "$1" in
  prepare)
    # Point /buttonmen at this checkout, then let puppet install anything
    # missing, copy the current source into /var/www and rebuild the databases
    ln -sfn "$(pwd)" /buttonmen
    git config --global --add safe.directory '*'
    bash deploy/vagrant/bootstrap.sh
    puppet apply --modulepath=/buttonmen/deploy/vagrant/modules /buttonmen/deploy/circleci/manifests/init.pp
    ;;
  audit-newlines)
    python3 deploy/circleci/audit_newlines.py
    ;;
  audit-php)
    php ./deploy/circleci/audit_php_files.php .
    ;;
  audit-js-coverage)
    python3 ./deploy/circleci/audit_js_unit_test_coverage.py
    ;;
  grunt)
    sh ./util/grunt/circleci-grunt.sh
    ;;
  phpcs)
    php /etc/php/8.3/deploy-includes/phpcs.phar --report=checkstyle --report-file=./build/logs/checkstyle.xml --standard=./deploy/circleci/checkstyle/buttonmen.xml ./src/api ./src/engine
    ;;
  db-rebuild)
    # The test compares this branch with origin/master and needs a named branch
    if ! git symbolic-ref -q HEAD > /dev/null; then
      git checkout -q -B ci-branch
    fi
    /usr/local/bin/branch_database_rebuild_test
    ;;
  phpunit)
    phpunit --dont-report-useless-tests --bootstrap ./deploy/circleci/phpunit_bootstrap.php --log-junit build/logs/junit.xml --coverage-clover build/logs/clover.xml --debug test/
    ;;
  dummy-data)
    rsync -a src/api/dummy_data/ /var/www/api/dummy_data/
    bash ./deploy/circleci/verify_dummy_responder_files.sh src/api/dummy_data/ /var/www/api/dummy_data/
    ;;
  qunit)
    OPENSSL_CONF=/dev/null /usr/bin/xvfb-run /usr/local/bin/phantomjs --web-security=false /usr/local/etc/run-jscover-qunit.js http://localhost/test-ui/phantom-index.html | tee build/logs/qunit.log
    ;;
  python27|python39)
    BMAPI_TEST_TYPE=circleci PYTHON_VERSION="$1" /usr/local/bin/run_buttonmen_python_tests
    ;;
  metrics)
    pdepend --jdepend-xml=./build/logs/jdepend.xml --jdepend-chart=./build/pdepend/dependencies.svg --overview-pyramid=build/pdepend/overview-pyramid.svg ./src
    php /etc/php/8.3/deploy-includes/phpmd.phar ./src xml ./deploy/circleci/pmd/buttonmen.xml --reportfile ./build/logs/pmd.xml
    /usr/bin/phploc --log-csv ./build/logs/phploc.csv ./src
    php /etc/php/8.3/deploy-includes/phpcb.phar --log ./build/logs --source ./src --output ./build/code-browser
    ;;
  summary)
    # Write test counts to the GitHub Actions job summary
    python3 deploy/ci/summary.py >> "${GITHUB_STEP_SUMMARY:-/dev/stdout}"
    ;;
  *)
    echo "Unknown step: $1" >&2
    exit 2
    ;;
esac
