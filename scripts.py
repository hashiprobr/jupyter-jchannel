import os
import subprocess

from argparse import ArgumentParser


def notebooks():
    subprocess.run(['jupyter-lab'])


def tests():
    parser = ArgumentParser()
    parser.add_argument('--path', action='store')
    parser.add_argument('--coverage', action='store_true')

    input = parser.parse_args()

    output = ['pytest']

    if input.path is not None:
        output.append(input.path)

    if input.coverage:
        output.extend(['--cov-branch', '--cov=jchannel', '--cov-report=html:coverage/html-report', '--cov-report=lcov:coverage/lcov.info'])

    subprocess.run(output)

    if input.coverage:
        os.remove('.coverage')


def docs():
    subprocess.run(['sphinx-build', '-M', 'html', 'docs/source', 'docs/build'])
