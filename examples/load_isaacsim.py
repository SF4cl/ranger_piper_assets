#!/usr/bin/env python3
"""Load the USD asset with Isaac Sim 5.x and hold its reference pose."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--steps', type=int, default=0,
                        help='0: until the window closes; headless defaults to 1500')
    args = parser.parse_args()
    if args.steps < 0:
        parser.error('--steps must be nonnegative')

    from isaacsim import SimulationApp

    app = SimulationApp({'headless': args.headless})
    try:
        # Simulator modules must be imported after SimulationApp starts.
        import numpy as np
        from isaacsim.core.api import World
        from isaacsim.core.api.objects import GroundPlane
        from isaacsim.core.api.robots import Robot
        from isaacsim.core.utils.stage import add_reference_to_stage
        from isaacsim.core.utils.types import ArticulationAction
        from pxr import UsdLux

        cfg = json.loads((ROOT / 'common/robot.json').read_text())
        world = World(stage_units_in_meters=1., physics_dt=.002, rendering_dt=1/60)
        world.scene.add(GroundPlane(prim_path='/World/GroundPlane', size=30.))
        UsdLux.DomeLight.Define(world.stage, '/World/Light').CreateIntensityAttr(700.)
        add_reference_to_stage(str(ROOT / 'isaacsim/robot.usd'), '/World/Robot')
        robot = world.scene.add(Robot(
            prim_path='/World/Robot', name='ranger_piper',
            position=np.array([0., 0., cfg['spawn_height_m']]),
        ))
        world.reset()
        names = robot.dof_names
        initial = np.array([cfg['initial_positions'][name] for name in names])
        robot.set_joint_positions(initial)
        robot.set_joint_velocities(np.zeros(len(names)))
        robot.get_articulation_controller().set_gains(
            kps=np.array([cfg['drives'][name]['kp'] for name in names]),
            kds=np.array([cfg['drives'][name]['kd'] for name in names]),
        )
        # Set position targets for steering/arm/fingers, zero velocity for wheels.
        for mode in ('position', 'velocity'):
            indices = np.array([i for i, name in enumerate(names)
                                if cfg['drives'][name]['mode'] == mode])
            targets = initial[indices] if mode == 'position' else np.zeros(len(indices))
            values = {'joint_positions' if mode == 'position' else 'joint_velocities': targets}
            robot.apply_action(ArticulationAction(joint_indices=indices, **values))
        if not args.headless:
            from isaacsim.core.utils.viewports import set_camera_view

            set_camera_view(eye=np.array([1.4, 1.5, 1.15]), target=np.array([0., 0., .45]))
        limit = args.steps or (1500 if args.headless else None)
        step = 0
        while app.is_running() and (limit is None or step < limit):
            world.step(render=not args.headless)
            step += 1
        print(f'Isaac Sim: {len(names)} joints, {step} physics steps', flush=True)
    except Exception:
        # Kit shutdown can hide pending tracebacks; print before closing it.
        import traceback

        traceback.print_exc()
        sys.stderr.flush()
        raise
    finally:
        app.close()


if __name__ == '__main__':
    main()
