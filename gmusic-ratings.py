#!/usr/bin/python

# Copyright 2012  Nicholas Parker
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

#####
# DESCRIPTION:
#  Reads song ratings from file metadata, then applies those ratings to
#  a Google Music library. I just made this for my own personal use; it's
#  probably not as polished as it should be. Hopefully the official
#  gmusic uploader will someday do this automatically.
# PREREQUISITES:
# - Mutagen (for reading tag metadata)
# - gmusicapi (for applying ratings to a GMusic library)
#####

import os
import sys
reload(sys) # required for this to work, apparently:
sys.setdefaultencoding('utf-8')
import cPickle

####
# READING SONGS FROM DISK
####

# this is just my own personal list of files to not complain about, you may want to add more:
ignored_exts = [".jpg", ".m3u", ".png", ".txt", ".sfv", ".nfo", ".epub", ".m4a"]

from mutagen.id3 import ID3
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC

class Song:
    def __init__(self, filename, artist, title, rating):
        self.filename = filename
        self.artist = artist
        self.title = title
        self.rating = rating
        self.gid = ""

    def printsong(self):
        print "%s\t%s\t%s\t%s\t%s" % \
            (self.filename, self.artist, self.title, self.rating, self.gid)

class SongFiles:
    def __init__(self, path):
        self.__by_artist = {}

        cachefile = "musicfiles.pickle"
        if os.path.isfile(cachefile):
            print "Loading cached files..."
            infile = open(cachefile, "rb")
            self.__by_artist = cPickle.load(infile)
            total_found = 0
            for k,v in self.__by_artist.iteritems():
                total_found += len(v)
            print "Found %d music files (%d artists)." % \
                (total_found, len(self.__by_artist))
            return

        def ignored(filename):
            for i in ignored_exts:
                if filename.endswith(i):
                    return True
            return False
        def add(song):
            if not self.__by_artist.has_key(song.artist):
                self.__by_artist[song.artist] = []
            self.__by_artist[song.artist].append(song)

        print "Scanning filesystem..."
        total_found = 0
        for root, dirs, files in os.walk(path):
            for f in files:
                fpath = os.path.join(root, f)
                if f.endswith(".mp3"):
                    add(SongFiles.__song_id3(fpath))
                elif f.endswith(".ogg") or f.endswith(".flac"):
                    try:
                        add(SongFiles.__song_ogg(fpath))
                    except:
                        add(SongFiles.__song_flac(fpath))
                elif not ignored(f):
                    print "Unrecognized filename extension: %s" % fpath
                    continue
                total_found += 1
        print "Found %d music files." % total_found

        print "Writing..."
        outfile = open(cachefile, "wb+")
        cPickle.dump(self.__by_artist, outfile)

    def find_rating(self, gm):
        found = False
        matching_artist = self.__by_artist.get(gm["artist"], [])
        for s in matching_artist:
            if s.title == gm["name"]:
                return s.rating
        return -1

    @staticmethod
    def __song_id3(filename):
        f = ID3(filename)
        artist = f.get("TPE1", ("",))[0]
        title = f.get("TIT2", ("",))[0]
        rating = 0
        for k,v in f.iteritems():
            if k.startswith("POPM"):
                rating = v.rating
                if rating == 0:
                    pass
                elif rating < 64:
                    rating = 1
                elif rating < 128:
                    rating = 2
                elif rating < 192:
                    rating = 3
                elif rating < 255:
                    rating = 4
                else:
                    rating = 5
                break
        return Song(filename, artist, title, rating)

    @staticmethod
    def __adjust_rating_ogg(rating):
        if rating == 0.5:
            return 0
        elif rating > 0.8:
            return 5
        elif rating > 0.6:
            return 4
        elif rating > 0.4:
            return 3
        elif rating > 0.2:
            return 2
        else:
            return 1

    @staticmethod
    def __song_ogg(filename):
        f = OggVorbis(filename)
        artist = f.get("artist", ("",))[0]
        title = f.get("title", ("",))[0]
        rating = 0
        for k,v in f.iteritems():
            if k.startswith("rating"):
                rating = SongFiles.__adjust_rating_ogg(float(v[0]))
                break
        return Song(filename, artist, title, rating)

    @staticmethod
    def __song_flac(filename):
        f = FLAC(filename)
        artist = f.get("artist", ("",))[0]
        title = f.get("title", ("",))[0]
        rating = 0
        for k,v in f.iteritems():
            if k.startswith("rating"):
                rating = SongFiles.__adjust_rating_ogg(float(v[0]))
                break
        return Song(filename, artist, title, rating)

####
# READING/UPDATING SONGS FROM GMUSIC
####

from gmusicapi.api import Api
import getpass

class GMusicRater:
    def __init__(self, files):
        self.__api = Api()
        self.__by_rating = {}
        self.__needs_rating_update = []

        # fill list of songs
        lib = []
        cachefile = "gmusic.pickle"
        if os.path.isfile(cachefile):
            print "Loading cached library..."
            infile = open(cachefile, "rb")
            lib = cPickle.load(infile)
        else:
            self.__log_in()
            print "Getting music..."
            lib = self.__api.get_all_songs()
            print "Writing..."
            outfile = open(cachefile, "wb+")
            cPickle.dump(lib, outfile)

        # order list of songs by rating
        notfound = []
        total_found = 0
        for s in lib:
            r = files.find_rating(s)
            # error finding file:
            if r < 0:
                notfound.append(s)
                continue

            #print "Got rating for %s: %s" % (s["title"], s["rating"])
            # file rating is different from cloud rating:
            if not r == s["rating"]:
                s["rating"] = r
                self.__needs_rating_update.append(s)
            if not self.__by_rating.has_key(r):
                self.__by_rating[r] = []
            self.__by_rating[r].append(s)
            total_found += 1

        print "Found %d cloud songs, %d of which need rating updates." % \
            (total_found, len(self.__needs_rating_update))
        print "Not found on disk: %d" % len(notfound)
        for s in notfound:
            print "  %s - %s" % (s["artist"], s["title"])

    def __log_in(self):
        if self.__api.is_authenticated():
            return

        print "Logging in..."
        email = raw_input("Email: ")
        password = getpass.getpass()
        if not self.__api.login(email, password):
            print "couldnt log in"
            sys.exit(1)

    def reset_playlists(self):
        self.__log_in()
        playlists = self.__api.get_all_playlist_ids(auto=False, user=True)["user"]
        print "Got %d playlists:" % len(playlists)
        for k,v in playlists.iteritems():
            print "  Deleting %s (%s)" % (k, v)
            for playlistid in v:
                self.__api.delete_playlist(playlistid)

        def get_ids(slist):
            ret = []
            for s in slist:
                ret.append(s["id"]);
            return ret
        awesome_songids = get_ids(self.__by_rating.get(5, []))
        good_songids = awesome_songids + get_ids(self.__by_rating.get(4, []))
        unrated_songids = get_ids(self.__by_rating.get(0, []))

        awesome_pid = self.__api.create_playlist("Awesome")
        print "Awesome %s -> %d songs" % (awesome_pid, len(awesome_songids))
        self.__api.add_songs_to_playlist(awesome_pid, awesome_songids)

        good_pid = self.__api.create_playlist("Good")
        print "Good %s -> %d songs" % (good_pid, len(good_songids))
        self.__api.add_songs_to_playlist(good_pid, good_songids)

        unrated_pid = self.__api.create_playlist("Unrated")
        print "Unrated %s -> %d songs" % (unrated_pid, len(unrated_songids))
        self.__api.add_songs_to_playlist(unrated_pid, unrated_songids)

    def update_ratings(self):
        total = len(self.__needs_rating_update)
        if total == 0:
            return
        self.__log_in()
        print "Updating %d songs..." % total
        # divide updates into chunks.
        start = 0
        chunksz = 100 # could probably be larger, wasn't tested for max possible
        while start < total:
            end = start + chunksz
            if end >= total:
                end = total
            print "%d - %d" % (start, end)
            self.__api.change_song_metadata(self.__needs_rating_update[start:end])
            start = end

    def logout(self):
        if self.__api.is_authenticated():
            print "Logging out..."
            self.__api.logout()

####
# MAIN
####

def main(argv):
    if len(argv) < 2 or not os.path.isdir(argv[1]):
        print "Provide directory: %s <dir>" % argv[0]
        sys.exit(1)

    files = SongFiles(argv[1])
    cloud = GMusicRater(files)
    cloud.reset_playlists()
    cloud.update_ratings()
    cloud.logout()

if __name__ == "__main__":
    main(sys.argv)
