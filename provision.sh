#!/usr/bin/env bash

export LEIN_ROOT="1"
export DEBIAN_FRONTEND=noninteractive

install-lein () {
    if [ ! -f /usr/local/bin/lein ]; then
        echo "Downloading lein"
        wget https://raw.github.com/technomancy/leiningen/stable/bin/lein 2>&1 lein-download-log

        echo "Moving lein into /usr/local/bin"
        mv lein /usr/local/bin/

        echo "Making lein executable"
        chmod a+x /usr/local/bin/lein

        echo "Running lein for the first time"
        lein --help
    else
        echo "lein is already installed at /usr/local/bin/lein"
    fi
}

apt-get update
apt-get install -y openjdk-6-jre-headless git curl screen python python-pip vim
pip install pyyaml clojure-py
install-lein
