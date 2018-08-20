#!/usr/bin/python2 -u
#
# Script to drive rpmfusion rebuild of packages corrupted by bad binutils
# versions. Based on Fedora releng find-bad-builds.py and:
#
# find-failures.py - A utility to discover failed builds in a given tag
#                    Output is currently rough html
#
# Copyright (C) 2013 Red Hat Inc,
# SPDX-License-Identifier:	GPL-2.0+
#
# Authors:
#     Jesse Keating <jkeating@redhat.com>
#     Ralph Bean <rbean@redhat.com>
#

from __future__ import print_function

import sys

import koji
import operator
import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


# Set some variables
# Some of these could arguably be passed in as args.
tagglob = 'f29*' # glob matching tags to check

# Date range within which bad builds may be found
epoch_start = '2018-07-26 13:00:00.000000'
epoch_end = '2018-07-31 00:00:00.000000'

# the binutils versions that caused bad builds
bad_binutils_ver = '2.31.1'
bad_binutils_rels = ['4.fc29', '5.fc29', '6.fc29', '7.fc29']

rebuilddict = {} # dict of owners to lists of packages needing rebuild.
rebuilds = [] # raw list of packages needing rebuild.

def retry_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_builds(kojisession, buildtag):
    """This function returns list of all builds since epoch within
    buildtag that match our criteria for suspect builds

    Keyword arguments:
    kojisession -- connected koji.ClientSession instance
    buildtag -- tag where to look for builds
    """

    # Get a list of builds in our build tag
    destbuilds = kojisession.listTagged(buildtag, latest=True, inherit=False)

    suspects = [] # raw list of potential rebuilds.

    for build in destbuilds:
        if (build['creation_time'] > epoch_start) and (build['creation_time'] < epoch_end):
            suspects.append(build)
    print("Checking {} builds in tag {}".format(len(suspects),buildtag), file=sys.stderr)

    needbuild = []

    for build in suspects:
        sys.stderr.write('.')
        for task in kojisession.getTaskChildren(build['task_id']):
            if build in needbuild:
                continue
            if task['method'] == 'buildArch':
                for rootid in kojisession.listBuildroots(taskID=task['id']):
                    for pkg in kojisession.listRPMs(componentBuildrootID=rootid['id']):
                        if (pkg['name'] == 'binutils') and (pkg['version'] == bad_binutils_ver):
                            if pkg['release'] in bad_binutils_rels:
                                #print("task {}: found bad binutils version {}-{}".format(
                                #       task['id'],pkg['version'],pkg['release']), file=sys.stderr)
                                sys.stderr.write('\b!')
                                needbuild.append(build)
    return needbuild


if __name__ == '__main__':
    # Create a koji session
    kojisession = koji.ClientSession('http://koji.rpmfusion.org/kojihub')

    taglist = kojisession.search(terms=tagglob, type="tag", matchType="glob")

    builds = []
    for tag in taglist:
        builds.extend(get_builds(kojisession, tag['name']))

    # Generate the dict with the failures and urls
    for build in builds:
        taskurl = 'http://koji.rpmfusion.org/koji/taskinfo?taskID=%s' % build['task_id']
        owner = build['owner_name']
        pkg = build['name']
        if not pkg in rebuilds:
            rebuilds.append(pkg)
        rebuilddict.setdefault(owner, {})[pkg] = taskurl

    now = datetime.datetime.now()
    now_str = "%s UTC" % str(now.utcnow())
    print('\nPackages that need rebuilding as of {} ({} total)'.format(now_str,len(rebuilds)))

    # Print the results
    for owner in sorted(rebuilddict.keys()):
        print()
        print("{} ({}):".format(owner, len(rebuilddict[owner])))
        for pkg in sorted(rebuilddict[owner].keys()):
            if(len(pkg) > 15):
                print("  {}\n                  {}".format(pkg,rebuilddict[owner][pkg]))
            else:
                print("  {0:<15} {1}".format(pkg,rebuilddict[owner][pkg]))

