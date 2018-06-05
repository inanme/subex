import sublime
import sublime_plugin
import re
import functools
from datetime import datetime

from . import call_cmd

# print(sys.version)
fmt = "%Y-%m-%dT%H:%M:%S.%fZ"

line_break = "-" * 80 + "\n"
first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
executor = call_cmd.Executor()

CMD_OUT_VIEW_NAME = 'Subex Output'
DIAG_OUT_VIEW_NAME = 'Subex Diagnostic Output'


def main_thread(callback, *args, **kwargs):
    sublime.set_timeout_async(functools.partial(callback, *args, **kwargs), 0)


def to_snake_case(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def decorate_string(string):
    now = datetime.now().isoformat()
    return "{} - {} \n".format(now, string)


# cols is an array of values between 0 and 1 that represent the proportional position of each column break
# rows is the same as cols
# cells is an array of arrays, each inner array contains [x1,y1,x2,y2] coordinates of the cell
# https://forum.sublimetext.com/t/set-layout-reference/5713
def set_layout(window):
    window.run_command('set_layout', {
        'cols': [0.0, 0.5, 1.0],
        'rows': [0.0, 0.5, 1.0],
        'cells': [[0, 0, 1, 2], [1, 0, 2, 1], [1, 1, 2, 2]]
    })


def erase(view):
    # some_view.erase(edit, sublime.Region(0, some_view.size())
    view.run_command("select_all")
    view.run_command("right_delete")


def new_file(window, name, group, index):
    if window.num_groups() < 3:
        set_layout(window)
    output_view = window.new_file()
    output_view.set_name(name)
    window.set_view_index(output_view, group, index)
    return output_view


def get_active_view_and_window():
    window = sublime.active_window()
    view = window.active_view()
    return view, window


def get_active_view_line(view, _):
    # print(list(view.sel()))
    regions = [region for region in view.sel() if region.empty()]
    region = regions[0] if regions else None
    if region is not None:
        line = view.line(region)
        line_contents = view.substr(line)
        return line_contents


def get_active_view_word(view, _):
    # print(list(view.sel()))
    regions = [region for region in view.sel() if region.empty()]
    region = regions[0] if regions else None
    if region is not None:
        word = view.word(region)
        word_contents = view.substr(word)
        return word_contents


def get_active_view_selected(view, _):
    # print(list(view.sel()))
    regions = [region for region in view.sel() if not region.empty()]
    region = regions[0] if regions else None
    return view.substr(region) if region else None


def echo_current_line_in_panel(view, window):
    current_line = get_active_view_line(view, window)
    if current_line is not None:
        existing_panel = window.find_output_panel(EchoCommand.cmd_name)
        panel = existing_panel if existing_panel is not None else window.create_output_panel(EchoCommand.cmd_name)
        window.run_command('show_panel', {'panel': EchoCommand.pnl_name})
        panel_settings = panel.settings()
        panel_settings.set('EchoCommand', True)
        panel.run_command('insert', {'characters': decorate_string(current_line),
                                     'force': False,
                                     'scroll_to_end': True})


def echo_current_line_in_view(view, window):
    current_line = get_active_view_line(view, window)
    if current_line is not None:
        existing_view = [view for view in window.views() if view.name() == CMD_OUT_VIEW_NAME]
        output_view = existing_view[0] if existing_view else new_file(window, CMD_OUT_VIEW_NAME, 1, 0)
        output_view.run_command('insert', {'characters': decorate_string(current_line),
                                           'force': False,
                                           'scroll_to_end': True})
        window.focus_view(view)


# http://docs.sublimetext.info/en/latest/reference/commands.html

class OutputHandler:
    def __init__(self, command, out_view, diag_view, window):
        self.command = command
        self.out_view = out_view
        self.diag_view = diag_view
        self.window = window
        self.first_output = True
        self.kubectl_get_pod = False
        for view in [out_view, diag_view]:
            view.run_command('append', {'characters': line_break})
            view.run_command('append', {'characters': decorate_string(self.command)})
        if "kubectlgetpod" in re.sub('\s+', '', self.command):
            self.kubectl_get_pod_namespace = re.sub('\s*kubectl\s+get\s+pods?\s+', '', self.command)
            self.kubectl_get_pod = True

    def process(self, output):
        self.out_view.run_command('append', {'characters': output})
        self.out_view.run_command('move_to', {'to': 'eof'})
        if self.first_output:
            self.first_output = False
        elif self.kubectl_get_pod:
            output_array = re.split('\s+', output)
            if output_array:
                pod = output_array[0]
                pod_log_cmd = "kubectl logs -f {} {}\n".format(pod, self.kubectl_get_pod_namespace)
                pod_del_cmd = "kubectl delete pod {} {}\n".format(pod, self.kubectl_get_pod_namespace)
                pod_desc_cmd = "kubectl describe pod {} {}\n".format(pod, self.kubectl_get_pod_namespace)
                pod_sh_cmd = "kubectl exec -it {} bash {}\n".format(pod, self.kubectl_get_pod_namespace)
                pod_yaml_cmd = "kubectl get pod {} {} -o yaml\n\n".format(pod, self.kubectl_get_pod_namespace)
                self.diag_view.run_command('append', {
                    'characters': pod_log_cmd + pod_del_cmd + pod_desc_cmd + pod_sh_cmd + pod_yaml_cmd})
                self.diag_view.run_command('move_to', {'to': 'eof'})


def get_cmd_dia_views(_, window):
    existing_cmd_view = [view for view in window.views() if view.name() == CMD_OUT_VIEW_NAME]
    cmd_out_view = existing_cmd_view[0] if existing_cmd_view else new_file(window, CMD_OUT_VIEW_NAME, 1, 0)

    existing_dia_view = [view for view in window.views() if view.name() == DIAG_OUT_VIEW_NAME]
    dia_out_view = existing_dia_view[0] if existing_dia_view else new_file(window, DIAG_OUT_VIEW_NAME, 2, 0)

    return cmd_out_view, dia_out_view


def execute_current_line_in_view(view, window, current_line):
    cmd_out_view, dia_out_view = get_cmd_dia_views(view, window)

    if "__clear__" in current_line:
        print('Will clear both')
        erase(cmd_out_view)
        erase(dia_out_view)
    elif "__clear1__" in current_line:
        erase(cmd_out_view)
    elif "__clear2__" in current_line:
        erase(dia_out_view)
    else:
        output_handler = OutputHandler(current_line, cmd_out_view, dia_out_view, window)
        executor.async_execute_string(current_line, output_handler.process)
        window.focus_view(view)


class EchoCommand(sublime_plugin.TextCommand):
    cmd_name = to_snake_case('EchoCommand')
    pnl_name = 'output.' + cmd_name

    def run(self, edit, output=None):
        view, window = get_active_view_and_window()
        if output == 'panel':
            echo_current_line_in_panel(view, window)
        elif output == 'file':
            echo_current_line_in_view(view, window)
        else:
            pass


def to_epoc(numeric_word):
    if len(numeric_word) == 10:
        return datetime.utcfromtimestamp(float(numeric_word)).strftime(fmt)
    elif len(numeric_word) == 13:
        return datetime.utcfromtimestamp(float(numeric_word) / 1000).strftime(fmt)
    elif len(numeric_word) == 16:
        return datetime.utcfromtimestamp(float(numeric_word) / 1000000).strftime(fmt)
    return None


class MyShellCommand(sublime_plugin.TextCommand):
    executor.start()

    def run(self, edit, output=None):
        view, window = get_active_view_and_window()
        cmd_out_view, dia_out_view = get_cmd_dia_views(view, window)
        current_line = get_active_view_line(view, window)
        word = get_active_view_word(view, window)
        selected = get_active_view_selected(view, window)
        if word is not None and word.isnumeric():
            if to_epoc(word) is not None:
                cmd_out_view.run_command('append', {'characters': "{} - {}\n".format(word, to_epoc(word))})
                cmd_out_view.run_command('move_to', {'to': 'eof'})
            return
        if selected is not None:
            cmd_out_view.run_command('append', {'characters': "{} - {}\n".format(selected, datetime.strptime(selected, fmt).timestamp())})
            cmd_out_view.run_command('move_to', {'to': 'eof'})
            return
        if output == 'file' and current_line is not None:
            execute_current_line_in_view(view, window, current_line)
            return
