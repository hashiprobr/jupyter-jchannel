import os
import subprocess

from argparse import ArgumentParser


def notebooks():
    subprocess.run(['jupyter-lab'])


def tests():
    parser = ArgumentParser()
    parser.add_argument('--coverage', action="store_true")
    args = parser.parse_args()
    if args.coverage:
        subprocess.run(['pytest', '--cov=jchannel', '--cov-report=html:coverage/html-report', '--cov-report=lcov:coverage/lcov.info'])
        os.remove('.coverage')
    else:
        subprocess.run(['pytest'])


def docs():
    subprocess.run(['sphinx-build', '-M', 'html', 'docs/source', 'docs/build'])
