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

# Available keys:
# album, album-artist, artist, artwork-id, bit-rate,
# comment, composer, date-added, file-size, genre,
# is-compilation, last-skipped, length, local-path, media-attributes,
# mime-type, name, rating, sample-rate, score,
# skip-count, track-number, URI, year
default_track_format = "%(artist)s - %(name)s"
# A separate format for messages about Banshee itself (eg when it's not running)
default_err_format = "%s"

####

banshee_dbus_name = "org.bansheeproject.Banshee"
banshee_dbus_engine_path = "/org/bansheeproject/Banshee/PlayerEngine"
banshee_dbus_controller_path = "/org/bansheeproject/Banshee/PlaybackController"

dbus_listen_name = "org.bansheeproject.Banshee.PlayerEngine"
dbus_listen_signal = "EventChanged"

# Send data to an awesome widget
dbus_send_name = "org.naquadah.awesome.awful"
dbus_send_path = "/org/naquadah/awesome/awful/Remote"
dbus_send_cmd = "Eval"

import dbus, sys

def help_exit():
    sys.stderr.write('''Args: %s <command> [track-format] [err-format]
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

def get_status(track_format, err_format):
    # False: if banshee is closed, dont start it
    banshee = get_dbus_obj(banshee_dbus_name, banshee_dbus_engine_path, False)
    try:
        if not banshee:
            return unicode(err_format % "Not Running").encode("utf-8")
        # in case no track is even selected..
        state = banshee.GetCurrentState()
        if state == "idle":
            return unicode(err_format % "Idle").encode("utf-8")
        elif state == "notready":
            return unicode(err_format % "Loading...").encode("utf-8")
        else:
            track = banshee.GetCurrentTrack()
            return unicode(track_format % track).encode("utf-8")
    except KeyError, e:
        return unicode(err_format % ("Bad format: Not found: %s" % e)).encode("utf-8")
    except:
        return unicode(err_format % ("Exception: %s" % sys.exc_info()[1])).encode("utf-8")

def _skip(msg, ignorea, ignoreb):
    #print msg, ignorea, ignoreb
    if msg == "startofstream" or msg == "preparevideowindow": #entered new song or opened banshee
        return False
    #assume song hasnt changed
    #print "SKIP:", msg, get_status(default_track_format, default_err_format)
    return True

class PrintHandler:
    def __init__(self, track_format, err_format):
        self.__track_format = track_format
        self.__err_format = err_format

    def handle(self, msg, ignorea=None, ignoreb=None):
        if _skip(msg, ignorea, ignoreb):
            return

        print get_status(self.__track_format, self.__err_format)

class DbusHandler:
    def __init__(self, dbus_name, dbus_path, dbus_cmd,
                 track_format, err_format):
        self.__dbus_name = dbus_name
        self.__dbus_path = dbus_path
        self.__dbus_cmd = dbus_cmd
        self.__track_format = track_format
        self.__err_format = err_format

    def handle(self, msg, ignorea=None, ignoreb=None):
        if _skip(msg, ignorea, ignoreb):
            return

        sendme = get_status(self.__track_format, self.__err_format)
        #print "SEND:", sendme

        out = get_dbus_obj(self.__dbus_name, self.__dbus_path)
        interface = self.__dbus_path[1:].replace('/','.')

        err = out.get_dbus_method(self.__dbus_cmd)(sendme, dbus_interface=interface)
        if err:
            print err

def cmd_listen(dbus_out, track_format = default_track_format, err_format = default_err_format):
    # This must come BEFORE calling dbus.SessionBus():
    from dbus.mainloop.glib import DBusGMainLoop
    dbus_loop = DBusGMainLoop()

    bus = dbus.SessionBus(mainloop=dbus_loop)
    if dbus_out:
        b = DbusHandler(dbus_send_name, dbus_send_path, dbus_send_cmd,
                        track_format, err_format)
    else:
        b = PrintHandler(track_format, err_format)

    bus.add_signal_receiver(b.handle,
                            dbus_listen_signal,
                            dbus_listen_name)

    import gobject
    loop = gobject.MainLoop()

    #ping the current status before we start listening for changes
    b.handle("startofstream")

    loop.run()

def cmd_status(track_format = default_track_format, err_format = default_err_format):
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
        if len(args) == 4:
            cmd_listen(False, args[2], args[3])
        if len(args) == 3:
            cmd_listen(False, args[2])
        else:
            cmd_listen(False, )
    elif cmd == "listen_dbus":
        if len(args) == 4:
            cmd_listen(True, args[2], args[3])
        if len(args) == 3:
            cmd_listen(True, args[2])
        else:
            cmd_listen(True)
    else:
        help_exit()

if __name__ == "__main__":
    main(sys.argv)
