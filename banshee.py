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

# TODO something like this:
# echo "musicwidget.text = \":)\"" | awesome-client
# (or run awesome-client and send musicwidget.text = ":)"\n to its stdin)
# ps add this http://docs.python.org/library/stdtypes.html#string-formatting
#print '%(language)s has %(number)03d quote types.' % \
#       {"language": "Python", "number": 2}

### DEFINES ###

banshee_dbus_name = "org.bansheeproject.Banshee"
banshee_dbus_engine_path = "/org/bansheeproject/Banshee/PlayerEngine"
banshee_dbus_controller_path = "/org/bansheeproject/Banshee/PlaybackController"

dbus_listen_name = "org.bansheeproject.Banshee.PlayerEngine"
dbus_listen_signal = "EventChanged"

# Available keys:
# album, album-artist, artist, artwork-id, bit-rate,
# comment, composer, date-added, file-size, genre,
# is-compilation, last-skipped, length, local-path, media-attributes,
# mime-type, name, rating, sample-rate, score,
# skip-count, track-number, URI, year
default_format = "%(artist)s - %(name)s"

# Send data to an awesome widget
default_send_name = "org.naquadah.awesome.awful"
default_send_path = "/org/naquadah/awesome/awful/Remote"
default_send_cmd = "Eval"

import dbus, sys

def help_exit():
    sys.stderr.write('''Args: %s <command> [format]
Commands:
  play - Toggles playback of current track.
  stop - Stops current playback, if any.
  next - Skips to the next track.
  prev - Skips to the previous track or restarts the current track.
  status - Prints current track status, using 'format' if specified.
  listen_print - Runs continuously, printing status on changes, using 'format' if specified.
  listen_dbus - Same as listen_print, except sending 'format' to a dbus destination.
''' % sys.argv[0])
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

def get_status(track_format):
    # False: if banshee is closed, dont start it
    banshee = get_dbus_obj(banshee_dbus_name, banshee_dbus_engine_path, False)
    if not banshee:
        return "Not Running"
    # in case no track is even selected..
    state = banshee.GetCurrentState()
    if state == "idle":
        return "Idle"
    elif state == "notready":
        return "Loading..."
    track = banshee.GetCurrentTrack()
    try:
        return unicode(track_format % track).encode("utf-8")
    except KeyError, e:
        return "Bad format: Not found:", e
    except:
        return "Exception: ", sys.exc_info()[1]

def _skip(msg, ignorea, ignoreb):
    #print msg, ignorea, ignoreb
    if msg == "startofstream":
        return False
    #assume song hasnt changed
    #print "SKIP:", msg
    return True

class PrintHandler:
    def __init__(self, track_format):
        self.__format = track_format

    def handle(self, msg, ignorea=None, ignoreb=None):
        if _skip(msg, ignorea, ignoreb):
            return

        print get_status(self.__format)

class DbusHandler:
    def __init__(self, dbus_name, dbus_path, dbus_cmd, track_format):
        self.__dbus_name = dbus_name
        self.__dbus_path = dbus_path
        self.__dbus_cmd = dbus_cmd
        self.__format = track_format

    def handle(self, msg, ignorea=None, ignoreb=None):
        if _skip(msg, ignorea, ignoreb):
            return

        sendme = get_status(self.__format)
        #print "SEND:", sendme

        out = get_dbus_obj(self.__dbus_name, self.__dbus_path)
        interface = self.__dbus_path[1:].replace('/','.')

        err = out.get_dbus_method(self.__dbus_cmd)(sendme, dbus_interface=interface)
        if err:
            print err

def cmd_listen(dbus_out, track_format = default_format):
    # This must come BEFORE calling dbus.SessionBus():
    from dbus.mainloop.glib import DBusGMainLoop
    dbus_loop = DBusGMainLoop()

    bus = dbus.SessionBus(mainloop=dbus_loop)
    if dbus_out:
        b = DbusHandler(default_send_name, default_send_path,
                        default_send_cmd, track_format)
    else:
        b = PrintHandler(track_format)

    bus.add_signal_receiver(b.handle,
                            dbus_listen_signal,
                            dbus_listen_name)

    import gobject
    loop = gobject.MainLoop()

    #ping the current status before we start listening for changes
    b.handle("startofstream")

    loop.run()

def cmd_status(track_format = default_format):
    print get_status(track_format)

def cmd_play():
    banshee = get_dbus_obj(banshee_dbus_name, banshee_dbus_engine_path)
    if banshee:
        banshee.TogglePlaying()
    cmd_status()

def cmd_stop():
    # Don't start banshee to stop it...
    banshee = get_dbus_obj(banshee_dbus_name, banshee_dbus_engine_path, False)
    if banshee:
        banshee.Close()
    cmd_status()

def cmd_next():
    # Not sure what the 'restart' bool is for
    banshee = get_dbus_obj(banshee_dbus_name, banshee_dbus_controller_path)
    if banshee:
        banshee.Next(True)
    cmd_status()

def cmd_prev():
    # Not sure what the 'restart' bool is for
    banshee = get_dbus_obj(banshee_dbus_name, banshee_dbus_controller_path)
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
        if len(args) == 3:
            cmd_status(args[2])
        else:
            cmd_status()
    elif cmd == "listen_print":
        if len(args) == 3:
            cmd_listen(False, args[2])
        else:
            cmd_listen(False, )
    elif cmd == "listen_dbus":
        if len(args) == 3:
            cmd_listen(True, args[2])
        else:
            cmd_listen(True)
    else:
        help_exit()

if __name__ == "__main__":
    main(sys.argv)
