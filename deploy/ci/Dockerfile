##### CI image: the CircleCI puppet setup, applied ahead of time
# Jobs still run puppet against their own checkout, which copies the current
# source into /var/www and rebuilds the databases; this image only saves the
# package installs.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git rsync

COPY . /root/project
RUN ln -s /root/project /buttonmen \
 && mkdir -p /root/project/build/logs \
 && bash /buttonmen/deploy/vagrant/bootstrap.sh \
 && puppet apply --modulepath=/buttonmen/deploy/vagrant/modules /buttonmen/deploy/circleci/manifests/init.pp

# Don't ship databases built from this snapshot; each job creates its own
RUN service mysql start \
 && mysql -u root -e 'DROP DATABASE IF EXISTS buttonmen; DROP DATABASE IF EXISTS buttonmen_test' \
 && service mysql stop
