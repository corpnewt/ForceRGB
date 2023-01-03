#!/usr/bin/env python
import os, sys, datetime, shutil
from Scripts import *

class RGB:
    def __init__(self):
        self.u = utils.Utils("ForceRGB")
        self.d = downloader.Downloader()
        self.r = run.Run()
        self.url = "https://gist.githubusercontent.com/adaugherity/7435890/raw/66c54c17b179809b028b58a2ca7af0b9540d05b6/patch-edid.rb"
        self.scripts = "Scripts"
        if self.r.run({"args":["sw_vers","-productVersion"]})[0].strip() < "10.15":
            self.dest = "/System/Library/Displays/Contents/Resources/Overrides"
        else:
            self.dest = "/Library/Displays/Contents/Resources/Overrides"

    def _get_timestamp(self):
        return "-{:%Y-%m-%d %H.%M.%S}".format(datetime.datetime.now())

    def _download(self, url, dest):
        print("Downloading {}...".format(os.path.basename(url)))
        self.d.stream_to_file(url, os.path.join(dest,os.path.basename(url)), False)

    def _check_script(self):
        s_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts)
        s_name = os.path.basename(self.url)
        if not os.path.exists(os.path.join(s_path,s_name)):
            # Try to download
            self._download(self.url, s_path)
        if os.path.exists(os.path.join(s_path,s_name)):
            return os.path.join(s_path,s_name)
        return None

    def _check_out(self, out, prefix=" - "):
        if out[2] != 0:
            print("{}Failed: {}".format(out[1]))
            exit(1)

    def main(self):
        s_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts)
        self.u.head()
        print("")
        print("Gathering resources...")
        s = self._check_script()
        if not s:
            print("Script missing and failed to download.  Aborting...")
            exit(1)
        print("Cleaning Scripts folder...")
        for d in os.listdir(s_path):
            if d.lower().startswith("displayvendorid"):
                print(" - Removing {}...".format(d))
                try:
                    shutil.rmtree(os.path.join(s_path, d),ignore_errors=True)
                except Exception as e:
                    print(" ---> Failed: {}".format(e))
                    exit(1)
        print("Running {}...".format(os.path.basename(s)))
        # Uses ruby - set our Scripts dir as the default
        cwd = os.getcwd()
        os.chdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts))
        # Run the script
        print("")
        print("-------------------------------------------------------")
        print("-------------------- Running Patch --------------------")
        print("-------------------------------------------------------")
        print("")
        out = self.r.run({"args":["ruby",s],"stream":True})
        self._check_out(out)
        print("")
        print("-------------------------------------------------------")
        print("---------------------- Patch End ----------------------")
        print("-------------------------------------------------------")
        print("")
        if out[2] != 0:
            # Errored out
            print("Script returned an error.  Aborting...")
            exit(1)
        # We'll need to copy the directory - gather it up
        print("Scanning and copying results...")
        print(" - Verifying {}...".format(self.dest))
        if not os.path.isdir(self.dest):
            print(" --> Does not exist, attempting to create...")
            out = self.r.run({"args":["mkdir","-p",self.dest],"sudo":True})
            self._check_out(out,prefix=" --> ")
        for d in os.listdir(s_path):
            if d.lower().startswith("displayvendorid"):
                print("Located {}.".format(d))
                if os.path.exists(os.path.join(self.dest, d)):
                    print(" - Already exists at destination.")
                    print(" - Backing up with timestamp...")
                    self.r.run({"args":["mv",os.path.join(self.dest,d),os.path.join(self.dest,d+self._get_timestamp())],"sudo":True})
                print(" - Copying...")
                out = self.r.run({"args":["cp","-r",os.path.join(s_path,d),os.path.join(self.dest,d)],"sudo":True})
                self._check_out(out,prefix=" --> ")
                print(" - Removing original...")
                out = self.r.run({"args":["rm","-Rf",os.path.join(s_path,d)],"sudo":True})
                self._check_out(out,prefix=" --> ")
        print("")
        print("Done.")
        print("")
        exit()

r = RGB()
r.main()
