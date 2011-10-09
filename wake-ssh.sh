#!/bin/sh

# Wakes a WOL-enabled remote machine, then opens an SSH connection to it.
# Copyright (C) 2011  Nicholas Parker
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

DEST_IP=SPECIFY_HOST_OR_IP_HERE #expected ip/host of the machine
DEST_MAC=SPECIFY_MAC_HERE #mac address of the machine

WOL_SEND_IP=SPECIFY_BROADCAST_IP_HERE #broadcast address to send the WOL packet on
WOL_SEND_PORT=7 #port to send WOL packet to (usually 7 or 9)

SSH_USER=SPECIFY_USER_HERE
SSH_FLAGS=

SSH_EXE=ssh
PING_EXE=ping
WOL_EXE=wakeonlan #/usr/sbin/wol on dd-wrt routers

ECHO()
{
	echo $(date +[%H:%M:%S]) $@
}

do_ping()
{
	${PING_EXE} -W 1 -c 1 ${DEST_IP} > /dev/null
}

do_wol()
{
	${WOL_EXE} -i ${WOL_SEND_IP} -p ${WOL_SEND_PORT} ${DEST_MAC}
	if [ $? -ne 0 ]; then
		ECHO WOL failed, giving up
		exit 1
	fi
}

do_ssh()
{
	${SSH_EXE} ${SSH_FLAGS} ${SSH_USER}@${DEST_IP}
}

ECHO Checking ${DEST_IP}...
do_ping
if [ $? -ne 0 ]; then
	ECHO ${DEST_IP} appears to be asleep, sending WOL
	do_wol
	while [ 1 ]; do
		ECHO Waiting for ${DEST_IP} to boot up...
		do_ping
		if [ $? -eq 0 ]; then
			break
		fi
	done
fi

ECHO Machine is awake, attempting ssh
while [ 1 ]; do
	attempt_time=$(date +%s)
	do_ssh
	# if ssh returns non-error OR we've been in ssh for >=10s, exit
	# 10s check is in case eg our user had shut down the remote machine
	if [ $? -ne 255 -o $(expr ${attempt_time} + 10) -le $(date +%s) ]; then
		exit $?
	fi
	ECHO Waiting for ${DEST_IP} to open ssh...
	sleep 2
done
