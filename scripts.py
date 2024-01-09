import subprocess

from argparse import ArgumentParser


def notebooks():
    subprocess.run(['jupyter-lab'])


def tests():
    parser = ArgumentParser()
    parser.add_argument('--coverage', action="store_true")
    args = parser.parse_args()
    if args.coverage:
        subprocess.run(['coverage', 'run', '--data-file=coverage/.coverage', '-m', 'unittest', 'discover', 'tests'])
        subprocess.run(['coverage', 'lcov', '--data-file=coverage/.coverage', '-o', 'coverage/lcov.info'])
    else:
        subprocess.run(['python', '-m', 'unittest', 'discover', 'tests'])


def docs():
    subprocess.run(['sphinx-build', '-M', 'html', 'docs/source', 'docs/build'])
