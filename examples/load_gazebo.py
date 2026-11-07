#!/usr/bin/env python3
"""Load the native SDF with Fortress or modern Gazebo, without ROS."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def prepare_world(family, path):
    suffix = '' if family == 'fortress' else '.modern'
    root = ET.parse(ROOT / f'gazebo/world{suffix}.sdf').getroot()
    world = root.find('world')
    include = world.find('include')
    robot = ET.parse(ROOT / f'gazebo/model{suffix}.sdf').getroot().find('model')
    robot.insert(0, copy.deepcopy(include.find('pose')))
    for uri in robot.findall('.//mesh/uri'):
        uri.text = str((ROOT / 'gazebo' / uri.text).resolve())
    world.remove(include)
    world.append(robot)
    ET.indent(root, space='  ')
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=['fortress', 'modern'], default='fortress')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--iterations', type=int, default=0, help='0: run until stopped')
    parser.add_argument('--partition', default='ranger_piper_assets')
    args = parser.parse_args()
    if args.iterations < 0:
        parser.error('--iterations must be nonnegative')
    cli = ['ign', 'gazebo'] if args.family == 'fortress' else ['gz', 'sim']
    if not shutil.which(cli[0]):
        parser.error(f'Missing {cli[0]}; install the selected Gazebo distribution')
    env = os.environ.copy()
    env['IGN_PARTITION'] = env['GZ_PARTITION'] = args.partition
    with tempfile.TemporaryDirectory(prefix='ranger_piper_') as tmp:
        world = Path(tmp) / 'world.sdf'
        prepare_world(args.family, world)
        command = cli + ['-r']
        if args.headless:
            command.append('-s')
        if args.iterations:
            command += ['--iterations', str(args.iterations)]
        child = subprocess.Popen(command + [str(world)], env=env, start_new_session=True)

        def stop(signum, frame):
            try:
                os.killpg(child.pid, signal.SIGINT)
            except ProcessLookupError:
                pass

        handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            code = child.wait()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=10)
            for signum, handler in handlers.items():
                signal.signal(signum, handler)
        if code not in (0, -signal.SIGINT):
            raise SystemExit(code)


if __name__ == '__main__':
    main()
