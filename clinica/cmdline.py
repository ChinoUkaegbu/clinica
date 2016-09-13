from __future__ import print_function
import argcomplete
from argparse import ArgumentParser
from clinica.engine.cworkflow import *
import sys
import os
import subprocess
from clinica.engine import cmdparser

def visualize(clinicaWorkflow, ids, rebase=False):
    if not clinicaWorkflow.data.has_key('visualize'):
        print("No visualization was defined")
        exit(0)

    class chdir:
        def __init__(self, base):
            self.pwd = os.getcwd()
            os.chdir(base)
        def __del__(self):
            os.chdir(self.pwd)

    change_directory = None
    if rebase is False:
        change_directory = chdir(clinicaWorkflow.base_dir)
    else:
        change_directory = chdir(rebase)

    print(clinicaWorkflow.data['visualize'])
    program, arguments, matches = clinicaWorkflow.data['visualize']

    def run_program(id): subprocess.Popen([program] + arguments.replace("${%s}" % matches, id).strip().split(" "))
    [run_program(id) for id in ids]

def shell(clinicaWorkflow):
    workflow = clinicaWorkflow
    __banner__ = "workflow variable is instantiated for you!"
    namespace = globals().copy()
    namespace.update(locals())

    def load_python_shell():
        import readline
        import code
        shell = code.InteractiveConsole(namespace)
        shell.interact(banner=__banner__)

    def load_ipython_shell():
        from IPython.terminal.embed import InteractiveShellEmbed
        InteractiveShellEmbed(user_ns=namespace,banner1=__banner__)()

    try:
        load_ipython_shell()
    except:
        try:
            load_python_shell()
        except:
            print("Impossible to load ipython or python shell")

def load_conf(args):
    import cPickle

    def load(path):
        file = os.path.join(path, "clinica.pkl")
        if os.path.isfile(file): return cPickle.load(open(file))
        return False

    wk = False

    if len(args) == 0:
        wk = load(os.getcwd())
    elif os.path.isdir(args[0]):
        wk = load(args[0])

    if not wk:
        print("No <clinica.pkl> file found!")
        exit(0)

    return wk

def execute():
    """
    clinica <command> [path=current_directory] [options]
    ex:
    $cd WorkingDir/
    $clinica visualize --id=1,2,3
    """
    parser = ArgumentParser()
    parser.add_argument("cmd", choices=['run','visualize','shell'], nargs=1)
    parser.add_argument("-i", "--id", dest="id",
                      default=False,
                      help="unique identifier")
    parser.add_argument("-r", "--rebase", dest="rebase",
                      default=False,
                      help="unique identifier")
    parser.add_argument("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")

    sub = parser.add_subparsers()

    import inspect
    import clinica.engine.cmdparser
    for name, obj in inspect.getmembers(clinica.engine.cmdparser):
       if name != 'CmdParser' and inspect.isclass(obj):
            x = obj()
            if isinstance(x, clinica.engine.cmdparser.CmdParser):
                run = sub.add_parser(name)
                x.options = run
                x.build()
                # x.options.usage = "Usage: %s run %s [options]" % (x.options.prog, x.name)
                # x.options.print_help()

    def e():
        import inspect
        import clinica.engine.cmdparser
        for name, obj in inspect.getmembers(clinica.engine.cmdparser):
            if name != 'CmdParser' and inspect.isclass(obj):
                x = obj()
                if isinstance(x, clinica.engine.cmdparser.CmdParser):
                    x.options.usage = "Usage: %s run %s [options]" % (x.options.prog, x.name)
                    x.options.print_help()

    # exit(0)
    try:
        def error(x): raise Exception('')
        parser.error = error
        argcomplete.autocomplete(parser)
        args = parser.parse_args()
    except:
        sys.stdout.flush()
        parser.print_help()
        # e()
        exit(0)

    if args.cmd == 'visualize':
        if args.id is None:
            print("Missing --id")
            exit(0)
        visualize(load_conf(args[1:]), args.id.split(","), args.rebase)

    if args.cmd == 'shell':
        shell(load_conf(args[1:]))

    if args.cmd == 'run':
        print('run')


if __name__ == '__main__':
    execute()
