/*
  compiz-is-wrong - Demonstrates compiz's current problems with window margins.
  Copyright (C) 2011  Nicholas Parker

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.


  BUILD INSTRUCTIONS:

  $ sudo apt-get install libx11-dev
  $ gcc compiz-is-wrong.c -o compiz-is-wrong -lX11


  WHAT YOU GET:

  metacity:

  moving window to x=50 y=50
  window coordinates are:
   interior: x=51 y=79
   decorations: left=1 top=29 border=0
   -> exterior: x=50 y=50 (PASS)

  xfwm:

  moving window to x=50 y=50
  active window is now:
   interior: x=57 y=72
   decorations: left=7 top=22 border=0
   -> exterior: x=50 y=50 (PASS)

  compiz:

  moving window to x=50 y=50
  window coordinates are:
   interior: x=51 y=79
   decorations: left=0 top=0 border=0
   -> exterior: x=51 y=79 (FAIL)
*/

#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <stdio.h>

#define MAX_PROPERTY_VALUE_LEN 4096

unsigned char* get_property(Display *disp, Window win,
		Atom xa_prop_type, const char* prop_name, size_t* out_count) {
	Atom xa_prop_name = XInternAtom(disp, prop_name, 0);
	if (xa_prop_name == None) {
		fprintf(stderr, "Atom not found for %s\n", prop_name);
		return NULL;
	}
	Atom xa_ret_type;
	int ret_format;
	unsigned long ret_nitems, ret_bytes_after;
	unsigned char* ret_prop;

	/* MAX_PROPERTY_VALUE_LEN / 4 explanation (XGetWindowProperty manpage):
	 *
	 * long_length = Specifies the length in 32-bit multiples of the
	 *               data to be retrieved.
	 */
	if (XGetWindowProperty(disp, win, xa_prop_name, 0, MAX_PROPERTY_VALUE_LEN / 4, 0,
					xa_prop_type, &xa_ret_type, &ret_format,
					&ret_nitems, &ret_bytes_after, &ret_prop) != Success) {
		fprintf(stderr, "Cannot get %s property.\n", prop_name);
		return NULL;
	}

	if (xa_ret_type != xa_prop_type) {
		if (xa_ret_type == None) {
			// avoid crash on XGetAtomName(None)
			char *req = XGetAtomName(disp, xa_prop_type);
			//not necessarily an error, can happen if the window in question just lacks the requested property
			XFree(req);
		} else {
			char *req = XGetAtomName(disp, xa_prop_type),
				*got = XGetAtomName(disp, xa_ret_type);
			fprintf(stderr, "Invalid type of %s property: req %s, got %s\n",
					prop_name, req, got);
			XFree(req);
			XFree(got);
		}
		XFree(ret_prop);
		return NULL;
	}

	if (out_count != NULL) {
		*out_count = ret_nitems;
	}
	return ret_prop;
}

#define WIN_X 50
#define WIN_Y 50

int main() {
	XWindowAttributes attr;
	int interior_x, interior_y;

	Display* disp = XOpenDisplay(NULL);
	if (disp == NULL) {
		fprintf(stderr, "get display failed\n");
		return 1;
	}

	{
		Window* active_win = (Window*)get_property(disp, DefaultRootWindow(disp),
				XA_WINDOW, "_NET_ACTIVE_WINDOW", NULL);
		if (active_win == NULL) {
			fprintf(stderr, "get active window failed\n");
			return 1;
		}

		printf("moving window to x=%d y=%d\n", WIN_X, WIN_Y);

		XMoveWindow(disp, *active_win, WIN_X, WIN_Y);

		XFree(active_win);
	}

	/* reset active_win to ensure coord update */

	{
		Window* active_win = (Window*)get_property(disp, DefaultRootWindow(disp),
				XA_WINDOW, "_NET_ACTIVE_WINDOW", NULL);
		if (active_win == NULL) {
			fprintf(stderr, "get active window failed\n");
			return 1;
		}

		if (XGetWindowAttributes(disp, *active_win, &attr) == 0) {
			fprintf(stderr, "get attributes failed\n");
			return 1;
		}

		Window tmp;
		if (XTranslateCoordinates(disp, *active_win, attr.root, 0, 0,
						&interior_x, &interior_y, &tmp) == 0) {
			fprintf(stderr, "coordinate transform failed\n");
			return 1;
		}

		XFree(active_win);
	}

	XCloseDisplay(disp);

	printf("window coordinates are:\n");
	printf(" interior: x=%d y=%d\n",
			interior_x, interior_y);
	printf(" decorations: left=%d top=%d border=%d\n",
			attr.x, attr.y, attr.border_width);
	int ext_x = interior_x - attr.x - attr.border_width,
		ext_y = interior_y - attr.y - attr.border_width;
	printf(" -> exterior: x=%d y=%d (%s)\n", ext_x, ext_y,
			(ext_x == WIN_X && ext_y == WIN_Y) ? "PASS" : "FAIL");

	return 0;
}
