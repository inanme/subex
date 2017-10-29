import sublime
import sublime_plugin
import re

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def to_snake_case(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


class SubexTextCommand(sublime_plugin.TextCommand):
    @staticmethod
    def get_active_view_and_window():
        window = sublime.active_window()
        view = window.active_view()
        return view, window

    def get_active_view_full_line(self):
        view, window = self.get_active_view_and_window()
        for region in view.sel():
            if region.empty():
                line = self.view.full_line(region)
                line_contents = self.view.substr(line)
                return line_contents


class EchoCommand(SubexTextCommand):
    cmd_name = to_snake_case('EchoCommand')
    pnl_name = 'output.' + cmd_name
    vw_name = 'Subex Output'

    def run(self, edit, output=None):
        if output == 'panel':
            self.echo_current_line_in_panel()
        elif output == 'file':
            self.echo_current_line_in_view()
        else:
            pass

    def echo_current_line_in_panel(self):
        current_line = self.get_active_view_full_line()
        if current_line is not None:
            view, window = self.get_active_view_and_window()
            existing_panel = window.find_output_panel(EchoCommand.cmd_name)
            panel = existing_panel if existing_panel is not None else window.create_output_panel(EchoCommand.cmd_name)
            window.run_command('show_panel', {'panel': EchoCommand.pnl_name})
            panel_settings = panel.settings()
            panel_settings.set('EchoCommand', True)
            panel.run_command('insert', {'characters': current_line, 'force': False, 'scroll_to_end': True})

    def column2(self, window):
        window.run_command('set_layout', {
            'cols': [0.0, 0.5, 1.0],
            'rows': [0.0, 1.0],
            'cells': [[0, 0, 1, 1], [1, 0, 2, 1]]
        })

    def new_file(self, window):
        if window.num_groups() < 2:
            self.column2(window)
        output_view = window.new_file()
        output_view.set_name(EchoCommand.vw_name)
        window.set_view_index(output_view, 1, 0)
        return output_view

    def echo_current_line_in_view(self):
        cr_view, window = self.get_active_view_and_window()
        current_line = self.get_active_view_full_line()
        if current_line is not None:
            existing_view = [view for view in window.views() if view.name() == EchoCommand.vw_name]
            output_view = existing_view[0] if existing_view else self.new_file(window)
            output_view.run_command('insert', {'characters': current_line, 'force': False, 'scroll_to_end': True})
            window.focus_view(cr_view)
