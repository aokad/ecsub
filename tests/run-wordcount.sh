#!/bin/bash

set -o errexit
set -o nounset

if test ${SECRET_NAME} = ${NAME}
then
    python ${SCRIPT}/wordcount.py ${INPUT_FILE} ${OUTPUT_FILE}
fi
