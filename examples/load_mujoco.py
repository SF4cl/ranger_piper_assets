#!/usr/bin/env python3
"""Load the MuJoCo scene and hold its reference pose."""
import argparse
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--steps', type=int, default=0,
                        help='0: until the window closes; headless defaults to 1500')
    args = parser.parse_args()
    if args.steps < 0:
        parser.error('--steps must be nonnegative')

    import mujoco

    model = mujoco.MjModel.from_xml_path(str(ROOT / 'mujoco/scene.xml'))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)
    limit = args.steps or (1500 if args.headless else None)
    viewer = None
    try:
        if not args.headless:
            import mujoco.viewer

            viewer = mujoco.viewer.launch_passive(model, data)
            viewer.cam.distance = 1.8
            viewer.cam.lookat[:] = [0, 0, .45]
            viewer.cam.azimuth = 135
            viewer.cam.elevation = -20
        step = 0
        while limit is None or step < limit:
            if viewer is not None and not viewer.is_running():
                break
            started = time.monotonic()
            mujoco.mj_step(model, data)
            step += 1
            if viewer is not None:
                viewer.sync()
                time.sleep(max(0, model.opt.timestep - (time.monotonic() - started)))
        print(f'MuJoCo: {model.nu} actuators, {data.time:.3f} simulated seconds')
    finally:
        if viewer is not None:
            viewer.close()


if __name__ == '__main__':
    main()
