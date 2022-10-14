#!/bin/bash
set -e -x

python setup.py develop
$@
