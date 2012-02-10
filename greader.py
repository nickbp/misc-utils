#!/usr/bin/python

# Produces the unread count for Google Reader. Requires one-time user
# credentials in a netrc file. Use "Authorizing applications & sites" for that.
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

import os.path

### OPTIONS ###

# Specify path to file which will hold a cached auth token, or "" to disable:
token_path = os.path.expanduser("~/.greader_auth_token")
# Specify this if you want to use a file other than ~/.netrc:
netrc_path = ""
# Change this if you want to use a different host from your .netrc:
netrc_host = "www.google.com"
# Set this to True to see any errors (it'll otherwise just produce a zero count):
print_errors = False

### CODE ###

import json, netrc, os, stat, sys, time, urllib, urllib2

# Returns ("user", "password") or raises string in the event of an error
def get_netrc_login(path, host):
    try:
        if path:
            nrc = netrc.netrc(path)
        else:
            nrc = netrc.netrc()
    except netrc.NetrcParseError, e:
        raise Exception("%s:%d: %s" % (e.filename, e.lineno, e.msg))
    except IOError, e:
        raise Exception("Couldn't read .netrc: %s" % os.strerror(e.errno))

    login = nrc.authenticators(host)
    if not login:
        raise Exception("No login for %s in .netrc" % host)
    return login

# Returns "authid" or raises a string in the event of an error
def request_auth_token(email, password, service="reader"):
    req_url = "https://www.google.com/accounts/ClientLogin"
    req_data = urllib.urlencode({"Email": email, "Passwd": password, "service": service})
    req = urllib2.Request(req_url, req_data)
    try:
        resp = urllib2.urlopen(req).read()
    except urllib2.HTTPError, e:
        raise Exception("HTTP Error %s" % e.code)
    except urllib2.URLError, e:
        raise Exception(e.reason)
    print resp
    try:
        resp_dict = dict(x.split("=") for x in resp.split("\n") if x)
        return resp_dict["Auth"]
    except:
        raise Exception("Auth token not found in server response")

def valid_auth_token(token_path):
    if not os.path.isfile(token_path):
        return False
    now = time.time()
    # tokens expire in 2 weeks, so assume a token older than 10 days is invalid
    # (give it some margin)
    return (now - os.path.getmtime(token_path)) <= 10*86400

def request_unread_count(auth_token):
    req_url = "http://www.google.com/reader/api/0/unread-count?output=json"
    req = urllib2.Request(req_url, None,
                          {"Authorization": "GoogleLogin auth=%s" % auth_token})
    try:
        resp = urllib2.urlopen(req).read()
    except urllib2.HTTPError, e:
        raise Exception("HTTP Error %s" % e.code)
    except urllib2.URLError, e:
        raise Exception(e.reason)

    try:
        doc = json.loads(resp)
        counts = doc["unreadcounts"]
        for c in counts:
            if c["id"].endswith("reading-list"):
                return c["count"]
        return 0
    except Exception, e:
        raise Exception("Couldn't parse unread-count response. API change?: %s -> %s" % (resp, str(e)))

def main():
    try:
        (user, _, pw) = get_netrc_login(netrc_path, netrc_host)
        if token_path and valid_auth_token(token_path):
            # get token from file
            auth_token = open(token_path, "r").read().strip()
        else:
            # get token from web, write to file
            auth_token = request_auth_token(user, pw)
            if token_path:
                open(token_path, "w").write("%s\n" % auth_token)
                os.chmod(token_path, stat.S_IWUSR | stat.S_IRUSR)# = 600
        print request_unread_count(auth_token)
    except Exception, e:
        if print_errors:
            print e
        else:
            print "0"
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
