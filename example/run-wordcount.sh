#!/bin/bash

set -o errexit
set -o nounset

python ${SCRIPT}/wordcount.py ${INPUT_FILE} ${OUTPUT_FILE}
