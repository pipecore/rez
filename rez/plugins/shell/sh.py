import sys
import select
import os
import os.path
import subprocess
from rez import module_root_path, plugin_factory
from rez.shells import UnixShell
from rez.util import get_script_path



class SH(UnixShell):
    executable = UnixShell.find_executable('sh')
    file_extension = 'sh'
    norc_arg = '--noprofile'

    @classmethod
    def name(cls):
        return 'sh'

    @classmethod
    def get_startup_sequence(cls, rcfile, norc, stdin, command):
        cls._ignore_bool_option('rcfile', rcfile)
        envvar = None
        files = []

        if command:
            cls._ignore_bool_option('stdin', stdin)
            stdin = False
        if stdin and not select.select([sys.stdin,],[],[],0.0)[0]:  # tests stdin
            stdin = False
        if not (command or stdin):
            if not norc:
                for file in ("~/.profile",):
                    if os.path.exists(os.path.expanduser(file)):
                        files.append(file)
            envvar = 'ENV'
            path = os.getenv(envvar)
            if path and os.path.isfile(os.path.expanduser(path)):
                files.append(path)

        return dict(
            stdin=stdin,
            command=command,
            do_rcfile=False,
            envvar=envvar,
            files=files,
            bind_files=[],
            source_bind_files=False
        )

    def bind_rez_cli(self, recorder):
        recorder.prependenv('PATH', get_script_path())
        curr_prompt = os.getenv("$PS1", "\\h:\\w]$ ")
        recorder.setprompt("\[\e[1m\]$REZ_ENV_PROMPT\[\e[0m\] %s" % curr_prompt)
        completion = os.path.join(module_root_path, "_sys", "bash_completion")
        recorder.source(completion)
        return recorder

    # TODO literal string support
    def setenv(self, key, value):
        return 'export %s="%s"' % (key, value)

    def unsetenv(self, key):
        return "unset %s" % (key,)

    def prependenv(self, key, value):
        return 'export %(key)s="%(value)s%(sep)s$%(key)s"' % dict(
            key=key,
            value=value,
            sep=self._env_sep(key))

    def appendenv(self, key, value):
        return 'export %(key)s="$%(key)s%(sep)s%(value)s"' % dict(
            key=key,
            value=value,
            sep=self._env_sep(key))

    def alias(self, key, value):
        # bash aliases don't export to subshells; so instead define a function,
        # then export that function
        # TODO replace with actual alias now that we have the HOME fix. Should we still
        # provide this as a "strong_alias" or maybe "alias_command" option?
        return "%(key)s() { %(value)s; };export -f %(key)s;" % dict(key=key,
                                                                    value=value)

    def setprompt(self, value):
        return 'export PS1="%s"' % value


class SHFactory(plugin_factory.RezPluginFactory):
    def target_type(self):
        return SH