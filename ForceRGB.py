#!/usr/bin/env python
import os, datetime, shutil, argparse, platform, subprocess
from Scripts import utils, run, downloader, plist

class RGB:
    def __init__(self):
        self.u = utils.Utils("ForceRGB")
        self.d = downloader.Downloader()
        self.r = run.Run()
        self.url = "https://gist.githubusercontent.com/adaugherity/7435890/raw/3403436446665aec2b5cf423ea4a5af63125e5af/patch-edid.rb"
        self.scripts = "Scripts"
        if self.r.run({"args":["sw_vers","-productVersion"]})[0].strip() < "10.15":
            self.dest = "/System/Library/Displays/Contents/Resources/Overrides"
        else:
            self.dest = "/Library/Displays/Contents/Resources/Overrides"

    def _is_apple_silicon(self):
        """Detect if running on Apple Silicon (M1/M2/M3) or Intel"""
        try:
            # Method 1: Check uname -m
            result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
            if result.returncode == 0:
                arch = result.stdout.strip()
                if arch == 'arm64':
                    return True
                elif arch == 'x86_64':
                    return False
            
            # Method 2: Check platform.machine() as fallback
            machine = platform.machine()
            if machine == 'arm64':
                return True
            elif machine in ['x86_64', 'AMD64']:
                return False
                
            # Method 3: Check sysctl as final fallback
            result = subprocess.run(['sysctl', '-n', 'hw.optional.arm64'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() == '1':
                return True
                
        except Exception:
            pass
        
        # Default to Intel if detection fails
        return False

    def _get_script_name(self):
        """Get the appropriate script name based on CPU architecture"""
        if self._is_apple_silicon():
            return "patch-edid-m1.rb"
        else:
            return "patch-edid.rb"

    def _get_latest_url(self):
        # Queries https://gist.github.com/adaugherity/7435890 directly and parses for
        # the latest revision
        print("Locating the latest revision of the patch edid script...")
        source_url = "https://gist.github.com/adaugherity/7435890"
        latest_url = revision = None
        try:
            source_html = self.d.get_string(source_url,progress=False)
            revision_primed = False
            for line in source_html.split("\n"):
                if '<a href="/adaugherity/7435890/raw/' in line:
                    latest_url = "https://gist.githubusercontent.com{}".format(line.split('"')[1].split('"')[0])
                elif line.strip() == "Revisions":
                    revision_primed = True
                elif revision_primed and 'class="Counter">' in line:
                    revision = line.split('class="Counter">')[1].split("<")[0]
                    revision_primed = False
                if latest_url and revision:
                    break # Got what we needed, bail
        except:
            pass
        if latest_url:
            print(" - Located {}{}".format(
                os.path.basename(latest_url),
                "" if not revision else " revision {}".format(revision)
            ))
            return latest_url
        print(" - Not located, using the last known revision...")
        return self.url

    def _get_timestamp(self):
        return "-{:%Y-%m-%d %H.%M.%S}".format(datetime.datetime.now())

    def _download(self, url, dest):
        print("Downloading {}...".format(os.path.basename(url)))
        self.d.stream_to_file(url, os.path.join(dest,os.path.basename(url)), False)

    def _check_script(self):
        s_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts)
        
        # Determine which script to use based on architecture
        is_arm = self._is_apple_silicon()
        script_name = self._get_script_name()
        
        if is_arm:
            # For Apple Silicon, check if our custom script exists
            arm_script_path = os.path.join(s_path, script_name)
            if os.path.exists(arm_script_path):
                print(f"Using Apple Silicon compatible script: {script_name}")
                return arm_script_path
            else:
                print(f"Apple Silicon detected but {script_name} not found!")
                print("The custom Apple Silicon script should be included in the Scripts directory.")
                return None
        else:
            # For Intel, download the original script if needed
            s_name = os.path.basename(self.url)
            intel_script_path = os.path.join(s_path, s_name)
            if not os.path.exists(intel_script_path):
                # Try to download
                latest_url = self._get_latest_url()
                self._download(latest_url, s_path)
            if os.path.exists(intel_script_path):
                print(f"Using Intel compatible script: {s_name}")
                return intel_script_path
            return None

    def _check_out(self, out, prefix=" - "):
        if out[2] != 0:
            print("{}Failed: {}".format(prefix,out[1]))
            exit(1)

    def main(self, display_is_tv="prompt"):
        s_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.scripts)
        self.u.head()
        print("")
        
        # Detect and display architecture
        is_arm = self._is_apple_silicon()
        arch_name = "Apple Silicon (ARM64)" if is_arm else "Intel (x86_64)"
        print(f"Detected CPU Architecture: {arch_name}")
        print("")
        
        print("Gathering resources...")
        s = self._check_script()
        if not s:
            print("Script missing and failed to download.  Aborting...")
            exit(1)
            
        # Modified cleanup - preserve DisplayVendorID directories temporarily
        print("Cleaning Scripts folder...")
        preserved_dirs = []
        for d in os.listdir(s_path):
            if d.lower().startswith("displayvendorid"):
                # Instead of removing, just note them for later cleanup
                preserved_dirs.append(d)
                print(" - Found existing {}... (will clean after processing)".format(d))
                
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
        out = self.r.run({"args":["ruby", os.path.basename(s)],"stream":True})
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
            
        # Check if we want to force the DisplayIsTV property
        if display_is_tv == "prompt":
            print("The DisplayIsTV property can be forced to False in order to use night shift")
            print("even if the display is a TV.")
            print("")
            print("1. Omit DisplayIsTV and let the OS detect the display type")
            print("2. Force DisplayIsTV to True")
            print("3. Force DisplayIsTV to False")
            print("")
            print("Q. Quit")
            print("")
            while True:
                got = self.u.grab("Please select an option:  ")
                if not len(got):
                    continue
                got = got.lower()
                if got == "q":
                    self.u.custom_quit()
                if not got in ("1","2","3"):
                    continue
                if got == "1":
                    display_is_tv = None
                elif got == "2":
                    display_is_tv = True
                else:
                    display_is_tv = False
                break
            print("")
            
        # We'll need to copy the directory - gather it up
        print("Scanning and copying results...")
        print(" - Verifying {}...".format(self.dest))
        if not os.path.isdir(self.dest):
            print(" --> Does not exist, attempting to create...")
            out = self.r.run({"args":["mkdir","-p",self.dest],"sudo":True})
            self._check_out(out,prefix=" --> ")
            
        # Find newly created DisplayVendorID directories
        current_dirs = [d for d in os.listdir(s_path) 
                       if os.path.isdir(os.path.join(s_path, d)) and d.lower().startswith("displayvendorid")]
        
        if not current_dirs:
            print("No DisplayVendorID directories found. The script may not have detected any external displays.")
            print("This is normal on Apple Silicon if no compatible external displays are connected.")
            
        for d in current_dirs:
            print("Located {}.".format(d))
            if display_is_tv is not None:
                print(" - Setting DisplayIsTV to {}...".format(display_is_tv))
                target = next((x for x in os.listdir(os.path.join(s_path,d)) if x.lower().startswith("displayproductid-")),None)
                if not target:
                    print(" -> DisplayProductID-X not found.  Aborting...")
                    exit(1)
                target = os.path.join(s_path,d,target)
                if not os.path.isfile(target):
                    print(" -> {} not found.  Aborting...".format(os.path.basename(target)))
                    exit(1)
                try:
                    with open(target,"rb") as f:
                        p_data = plist.load(f)
                except Exception:
                    print(" -> Failed to open {}.  Aborting...".format(os.path.basename(target)))
                    exit(1)
                # Set the prop and write the file
                p_data["DisplayIsTV"] = display_is_tv
                try:
                    with open(target,"wb") as f:
                        plist.dump(p_data,f)
                except Exception:
                    print(" -> Failed to save {}.  Aborting...".format(os.path.basename(target)))
                    exit(1)
            if os.path.exists(os.path.join(self.dest, d)):
                print(" - Already exists at destination.")
                print(" - Backing up with timestamp...")
                self.r.run({"args":["mv",os.path.join(self.dest,d),os.path.join(self.dest,d+self._get_timestamp())],"sudo":True})
            print(" - Copying...")
            out = self.r.run({"args":["cp","-r",os.path.join(s_path,d),os.path.join(self.dest,d)],"sudo":True})
            self._check_out(out,prefix=" --> ")
            
        # Clean up old and newly created DisplayVendorID directories after successful installation
        print("")
        print("Cleaning up DisplayVendorID directories...")
        all_vendor_dirs = preserved_dirs + [d for d in current_dirs if d not in preserved_dirs]
        for d in all_vendor_dirs:
            vendor_path = os.path.join(s_path, d)
            if os.path.exists(vendor_path):
                print(" - Removing {}...".format(d))
                try:
                    shutil.rmtree(vendor_path, ignore_errors=True)
                except Exception as e:
                    print(" ---> Warning: Failed to remove {}: {}".format(d, e))
                    
        print("")
        print("Done.")
        print("")
        self.u.custom_quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--display-is-tv",
        help=(
            "optionally sets the explicit value for the DisplayIsTV property"
            " - accepts prompt, none, true, or false - default is prompt"
        )
    )
    args = parser.parse_args()
    display_is_tv = "prompt"
    if args.display_is_tv:
        # Make sure it's valid
        tv_check = args.display_is_tv.lower()
        if tv_check in ("y","1","on","yes","true"):
            display_is_tv = True
        elif tv_check in ("n","0","no","off","false"):
            display_is_tv = False
        elif tv_check in ("none","null","omit"):
            display_is_tv = None
        elif tv_check in ("p","prompt","ask"):
            pass # Leave it as "prompt"
        else:
            # Didn't get a valid value - throw an error
            print("Invalid value for --display-is-tv:\n  Only prompt, none, true, or false can be passed.")
            exit(1)
    r = RGB()
    r.main(display_is_tv=display_is_tv)
