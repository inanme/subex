import sublime
import sublime_plugin
import re
import os
import sys
import subprocess

print(sys.version)

SEPARATOR3 = '🥺'
SEPARATOR1 = '🤔'
SEPARATOR2 = '➤'
SEPARATOR = '⫸'
BLOCK_SEPARATOR = "----"

my_env = os.environ.copy()
my_env.update({"PATH": "/usr/local/bin:/usr/bin:/bin"})


class BcCommand(sublime_plugin.TextCommand):
    def run(self, edit, output=None):
        extractions = []
        for index, region in enumerate(
                self.view.find_all(pattern=r"(?s)🤔(.*?)🥺", extractions=extractions, fmt="\\1")):
            text = self.view.substr(region)
            print(text)
            block = extractions[index]
            if block:
                # expression = re.split(SEPARATOR, text)[0]
                bc = subprocess.Popen(["bc", "-l"],
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      env=my_env)
                stdout, stderr = bc.communicate(bytes("scale=2;" + block, "ASCII"))
                bc.stdin.close()
                print(stdout, stderr)
                self.view.replace(edit, region, text + SEPARATOR + str(stdout.strip(), "ASCII"))

    def run1(self, edit, output=None):
        file_region = sublime.Region(0, self.view.size())
        for line_region in self.view.lines(file_region):
            # Alternatively, use view.insert() here if you're not
            # concerned about tabs getting converted to spaces.
            text = self.view.substr(line_region)
            if text.strip():
                expression = re.split(SEPARATOR, text)[0]
                bc = subprocess.Popen(["bc", "-l"],
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      env=my_env)
                stdout, stderr = bc.communicate(bytes("scale=2;" + expression + "\n", "ASCII"))
                bc.stdin.close()
                print(stdout, stderr)
                self.view.replace(edit, line_region, expression + SEPARATOR + str(stdout.strip(), "ASCII"))
