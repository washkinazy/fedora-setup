#!/bin/bash
# Reloads the Logitech HID++ module on resume
# to fix slow cursor movement after suspend
if [ "$1" = "post" ]; then
    sleep 2
    /usr/sbin/modprobe -r hid_logitech_hidpp 2>/dev/null || true
    /usr/sbin/modprobe hid_logitech_hidpp 2>/dev/null || true
fi
