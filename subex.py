import sublime
import sublime_plugin
import re
import functools
from datetime import datetime

from . import call_cmd

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


def column2(window):
    window.run_command('set_layout', {
        'cols': [0.0, 0.5, 1.0],
        'rows': [0.0, 1.0],
        'cells': [[0, 0, 1, 1], [1, 0, 2, 1]]
    })


def new_file(window, name, group, index):
    if window.num_groups() < 2:
        column2(window)
    output_view = window.new_file()
    output_view.set_name(name)
    window.set_view_index(output_view, group, index)
    return output_view


def get_active_view_and_window():
    window = sublime.active_window()
    view = window.active_view()
    return view, window


def get_active_view_line(view, _):
    regions = [region for region in view.sel() if region.empty()]
    region = regions[0] if regions else None
    if region is not None:
        line = view.line(region)
        line_contents = view.substr(line)
        return line_contents


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
                pod_yaml_cmd = "kubectl get pod {} {} -o yaml\n\n".format(pod, self.kubectl_get_pod_namespace)
                self.diag_view.run_command('append', {'characters': pod_log_cmd + pod_yaml_cmd})
                self.diag_view.run_command('move_to', {'to': 'eof'})


def execute_current_line_in_view(view, window):
    current_line = get_active_view_line(view, window)
    if current_line is not None:
        existing_cmd_view = [view for view in window.views() if view.name() == CMD_OUT_VIEW_NAME]
        cmd_out_view = existing_cmd_view[0] if existing_cmd_view else new_file(window, CMD_OUT_VIEW_NAME, 1, 0)

        existing_dia_view = [view for view in window.views() if view.name() == DIAG_OUT_VIEW_NAME]
        dia_out_view = existing_dia_view[0] if existing_dia_view else new_file(window, DIAG_OUT_VIEW_NAME, 1, 1)

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


class MyShellCommand(sublime_plugin.TextCommand):
    executor.start()

    def run(self, edit, output=None):
        view, window = get_active_view_and_window()
        if output == 'file':
            execute_current_line_in_view(view, window)
