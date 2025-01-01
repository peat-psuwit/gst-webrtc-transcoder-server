#!/usr/bin/env python3

# Idea comes from yt_dlp.
# Execute with
# $ python3 -m node_gst_transcoder_server

import sys

if __package__ is None and not getattr(sys, 'frozen', False):
    # direct call of __main__.py
    import os.path
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import node_gst_transcoder_server

if __name__ == '__main__':
    node_gst_transcoder_server.main()
