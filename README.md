# rpmfusion-f29rebuild
Code to drive the targeted rebuild of packages built using one of Fedora's bad binutils versions.

As Rathann noted on the rpmfusion-developers list:
> the binutils package in Fedora between versions 2.31.1-4.fc29 and
> 2.31.1-7.fc29 (inclusive) was producing broken binaries and any package
> built with any binutils version in the above range needs to be rebuilt.
> See https://bugzilla.redhat.com/show_bug.cgi?id=1609577 and
> https://pagure.io/releng/issue/7670 for more details.

Fedora releng has a [`find_failures.py`](https://pagure.io/releng/blame/scripts/find_failures.py?identifier=master) script they run against their koji environment, which should be adaptable into a tool that will allow us to find suspect builds that need to be invalidated. That'll be our starting point.
