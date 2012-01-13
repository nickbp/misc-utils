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

# Various status strings...
closed_status = "Not Running"
loading_status = "Loading..."
idle_status = "Idle"

####

banshee_status_interface = "org.bansheeproject.Banshee"
banshee_status_engine_path = "/org/bansheeproject/Banshee/PlayerEngine"
banshee_status_controller_path = "/org/bansheeproject/Banshee/PlaybackController"

banshee_listen_interface = "org.bansheeproject.Banshee.PlayerEngine"
banshee_listen_signal = "EventChanged"

shutdown_listen_interface = "org.freedesktop.DBus"
shutdown_listen_signal = "NameOwnerChanged"

# Send data to an awesome widget
dbus_send_interface = "org.naquadah.awesome.awful"
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

def _format_msg(err_format, msg, form = None):
    try:
        if form:
            return unicode(form % msg).encode("utf-8")
        else:
            return unicode(err_format % msg).encode("utf-8")
    except KeyError, e:
        return unicode(err_format % ("Bad format: Not found: %s" % e)).encode("utf-8")
    except:
        return unicode(err_format % ("Exception: %s" % sys.exc_info()[1])).encode("utf-8")

def get_status(track_format, err_format):
    # False: if banshee is closed, dont start it
    banshee = get_dbus_obj(banshee_status_interface, banshee_status_engine_path, False)
    if not banshee:
        return _format_msg(err_format, closed_status)
    # in case no track is even selected..
    state = banshee.GetCurrentState()
    if state == "idle":
        return _format_msg(err_format, idle_status)
    elif state == "notready":
        return _format_msg(err_format, loading_status)
    else:
        track = banshee.GetCurrentTrack()
        return _format_msg(err_format, track, track_format)

class PrintSender:
    def send(self, sendme):
        print sendme

class DbusSender:
    def __init__(self, dbus_name, dbus_path, dbus_cmd):
        self.__dbus_name = dbus_name
        self.__dbus_path = dbus_path
        self.__dbus_cmd = dbus_cmd

    def send(self, sendme):
        #print "SEND:", sendme
        try:
            out = get_dbus_obj(self.__dbus_name, self.__dbus_path)
        except:
            print "DBus Exception: %s" % sys.exc_info()[1]
            return
        interface = self.__dbus_path[1:].replace('/','.')

        err = out.get_dbus_method(self.__dbus_cmd)(sendme, dbus_interface=interface)
        if err:
            print err

class Handler:
    def __init__(self, sender, track_format, err_format):
        self.__sender = sender
        self.__track_format = track_format
        self.__err_format = err_format

    def handle_banshee(self, msg, ignorea=None, ignoreb=None):
        #entered new song or opened banshee
        if not msg == "startofstream" and not msg == "preparevideowindow":
            #print "SKIP:", msg
            return
        self.__sender.send(get_status(self.__track_format, self.__err_format))

    def handle_owner(self, name, old_owner, new_owner):
        if not name == banshee_status_interface:
            return

        if old_owner == "":
            # banshee is starting
            self.__sender.send(_format_msg(self.__err_format, loading_status))
        elif new_owner == "":
            # banshee is closing
            self.__sender.send(_format_msg(self.__err_format, closed_status))

def cmd_listen(dbus_out, track_format = default_track_format, err_format = default_err_format):
    # This must come BEFORE calling dbus.SessionBus():
    from dbus.mainloop.glib import DBusGMainLoop
    dbus_loop = DBusGMainLoop()

    bus = dbus.SessionBus(mainloop=dbus_loop)
    if dbus_out:
        sender = DbusSender(dbus_send_interface, dbus_send_path, dbus_send_cmd)
    else:
        sender = PrintSender()
    handler = Handler(sender, track_format, err_format)

    bus.add_signal_receiver(handler.handle_banshee, banshee_listen_signal, banshee_listen_interface)
    bus.add_signal_receiver(handler.handle_owner, shutdown_listen_signal, shutdown_listen_interface)

    import gobject
    loop = gobject.MainLoop()

    #ping the current status before we start listening for changes
    handler.handle_banshee("startofstream")

    loop.run()

def cmd_status(track_format = default_track_format, err_format = default_err_format):
    print get_status(track_format, err_format)

def cmd_play():
    banshee = get_dbus_obj(banshee_status_interface, banshee_status_engine_path)
    if banshee:
        banshee.TogglePlaying()
    cmd_status()

def cmd_stop():
    # Don't start banshee to stop it...
    banshee = get_dbus_obj(banshee_status_interface, banshee_status_engine_path, False)
    if banshee:
        banshee.Close()
    cmd_status()

def cmd_next():
    # Not sure what the 'restart' bool is for
    banshee = get_dbus_obj(banshee_status_interface, banshee_status_controller_path)
    if banshee:
        banshee.Next(True)
    cmd_status()

def cmd_prev():
    # Not sure what the 'restart' bool is for
    banshee = get_dbus_obj(banshee_status_interface, banshee_status_controller_path)
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
