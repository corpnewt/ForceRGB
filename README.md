# ForceRGB
```
usage: ForceRGB.py [-h] [-d DISPLAY_IS_TV]

options:
  -h, --help            show this help message and exit
  -d, --display-is-tv DISPLAY_IS_TV
                        optionally sets the explicit value for the DisplayIsTV
                        property - accepts prompt, none, true, or false -
                        default is prompt
```

***

ForceRGB is a script for macOS which downloads and automates the process of running adaugherity's [patch-edid.rb](https://gist.github.com/adaugherity/7435890) script.  It can optionally set the `DisplayIsTV` property to override system's display detection - this can be useful for forcing Night Shift on TVs.
