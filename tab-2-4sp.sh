#!/bin/bash

FIND=/usr/bin/find
SED=/bin/sed

help() {
    echo "Syntax: ${0} <path>"
    echo "  Recursively searches <path> for files and replaces all tabs with spaces therein."
    exit 1
}

PATH=$1
if [ -z "${PATH}" ]; then
    # missing required arg
    help
fi
if [ ! -e "${PATH}" ]; then
    echo "Error: Path '${PATH}' doesn't exist\n"
    help
fi

echo "Scanning '${PATH}'..."

if [ ! -e "${FIND}" ]; then
    echo "Couldn't find 'find': ${FIND}"
    exit 1
fi
if [ ! -e "${SED}" ]; then
    echo "Couldn't find 'sed': ${SED}"
    exit 1
fi

# first, get list of files
FILES=$(${FIND} ${PATH} -type f)
if [ $? -ne 0 ]; then
    echo "Got error searching path ${PATH}, exiting.."
    exit 1
fi
echo "The following files are about to be modified:"
for file in ${FILES}; do
    echo "  ${file}"
done

# prompt user with file list
while true; do
    read -p "CONTINUE? [y/n] " yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) echo "Aborted."; exit 0;;
        * ) echo "Please answer yes or no.";;
    esac
done

# they approve -- get to work!
for file in ${FILES}; do
    ${SED} -i 's/\t/    /g' $file
    if [ $? -ne 0 ]; then
        echo "Got error on file $file, exiting.."
        exit 1
    fi
done
echo "Done."
