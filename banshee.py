#!/usr/bin/python

# Controls Banshee from the commandline, producing the current song.
# Copyright (C) 2012  Nicholas Parker
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

### DEFINES ###

dbus_name = "org.bansheeproject.Banshee"
dbus_engine_path = "/org/bansheeproject/Banshee/PlayerEngine"
dbus_controller_path = "/org/bansheeproject/Banshee/PlaybackController"

import dbus, sys

def help_exit():
    sys.stderr.write('''Args: %s <command>
Commands:
  play - Toggles playback of current track.
  stop - Stops current playback, if any.
  next - Skips to the next track.
  prev - Skips to the previous track or restarts the current track.
  status - Prints current track status\n''' % sys.argv[0])
    sys.exit(1)

# Returns the DBus object for Banshee, or None if autostart is false and it's not running
def get_dbus_obj(name, path, autostart = True):
    bus = dbus.SessionBus()

    # get_object will launch banshee, so manually check if it's running
    try:
        bus.get_name_owner(name)
    except:
        # banshee isn't running
        if not autostart:
            return None

    return bus.get_object(name, path)

def cmd_status():
    # False: if banshee is closed, dont start it
    banshee = get_dbus_obj(dbus_name, dbus_engine_path, False)
    if not banshee:
        print "Not Running"
        return
    # in case no track is even selected..
    state = banshee.GetCurrentState()
    if state == "idle":
        print "Idle"
        return
    elif state == "notready":
        print "Loading..."
        return
    track = banshee.GetCurrentTrack()
    # Available keys:
    # album, local-path, media-attributes, rating,
    # name, artist, bit-rate, file-size, mime-type,
    # URI, comment, genre, length, artwork-id,
    # sample-rate, year, is-compilation, track-number,
    # date-added, album-artist
    artist = track.get("artist","")
    name = track.get("name","")
    print "%s - %s" % (artist, name)

def cmd_play():
    banshee = get_dbus_obj(dbus_name, dbus_engine_path)
    if banshee:
        banshee.TogglePlaying()
    cmd_status()

def cmd_stop():
    # Don't start banshee to stop it...
    banshee = get_dbus_obj(dbus_name, dbus_engine_path, False)
    if banshee:
        banshee.Close()
    cmd_status()

def cmd_next():
    # Not sure what the 'restart' bool is for
    banshee = get_dbus_obj(dbus_name, dbus_controller_path)
    if banshee:
        banshee.Next(True)
    cmd_status()

def cmd_prev():
    # Not sure what the 'restart' bool is for
    banshee = get_dbus_obj(dbus_name, dbus_controller_path)
    if banshee:
        banshee.RestartOrPrevious(True)
    cmd_status()

def main(args):
    if len(args) == 1:
        help_exit()

    cmd = args[1]
    if cmd == "play":
        cmd_play()
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "next":
        cmd_next()
    elif cmd == "prev":
        cmd_prev()
    elif cmd == "status":
        cmd_status()
    else:
        help_exit()

if __name__ == "__main__":
    main(sys.argv)
