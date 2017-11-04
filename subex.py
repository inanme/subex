import sublime
import sublime_plugin
import re
import functools
from datetime import datetime

from . import call_cmd

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
executor = call_cmd.Executor()


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


def new_file(window, name):
    if window.num_groups() < 2:
        column2(window)
    output_view = window.new_file()
    output_view.set_name(name)
    window.set_view_index(output_view, 1, 0)
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
        existing_view = [view for view in window.views() if view.name() == EchoCommand.vw_name]
        output_view = existing_view[0] if existing_view else new_file(window, EchoCommand.vw_name)
        output_view.run_command('insert', {'characters': decorate_string(current_line),
                                           'force': False,
                                           'scroll_to_end': True})
        window.focus_view(view)


line_break = "-" * 80 + "\n"


class OutputHandler:
    def __init__(self, command, view, window):
        self.command = command
        self.view = view
        self.window = window
        self.first_output = True

    def process(self, output):
        if self.first_output:
            self.view.run_command('insert', {'characters': line_break,
                                             'force': False,
                                             'scroll_to_end': True})
            self.view.run_command('insert', {'characters': decorate_string(self.command),
                                             'force': False,
                                             'scroll_to_end': True})
            self.first_output = False

        self.view.run_command('insert', {'characters': output,
                                         'force': False,
                                         'scroll_to_end': True})


def execute_current_line_in_view(view, window):
    current_line = get_active_view_line(view, window)
    if current_line is not None:
        existing_view = [view for view in window.views() if view.name() == EchoCommand.vw_name]
        output_view = existing_view[0] if existing_view else new_file(window, EchoCommand.vw_name)
        output_handler = OutputHandler(current_line, output_view, window)
        executor.async_execute_string(current_line, output_handler.process)
        window.focus_view(view)


# class EchoCommand(sublime_plugin.TextCommand):
#     cmd_name = to_snake_case('EchoCommand')
#     pnl_name = 'output.' + cmd_name
#     vw_name = 'Subex Output'
#
#     def run(self, edit, output=None):
#         view, window = get_active_view_and_window()
#         if output == 'panel':
#             echo_current_line_in_panel(view, window)
#         elif output == 'file':
#             echo_current_line_in_view(view, window)
#         else:
#             pass


class MyShellCommand(sublime_plugin.TextCommand):
    executor.start()

    def run(self, edit, output=None):
        view, window = get_active_view_and_window()
        if output == 'file':
            execute_current_line_in_view(view, window)
