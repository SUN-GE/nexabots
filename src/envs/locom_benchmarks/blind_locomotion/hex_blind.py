import numpy as np
import mujoco_py
import src.my_utils as my_utils
import time
import os
import cv2
from src.envs.locom_benchmarks import hf_gen
import gym
from gym import spaces
from math import acos


class Hexapod(gym.Env):
    MODELPATH = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "hex.xml")

    def __init__(self, hm_fun, *hm_args):
        print("Hexapod on {} env".format(hm_fun.__name__))
        self.hm_fun = hm_fun
        self.hm_args = hm_args

        # External parameters
        self.joints_rads_low = np.array([-0.6, -1.4, -0.8] * 6)
        self.joints_rads_high = np.array([0.6, 0.4, 0.8] * 6)
        self.joints_rads_diff = self.joints_rads_high - self.joints_rads_low

        self.target_vel = 0.4 # Target velocity with which we want agent to move
        self.max_steps = 300

        self.reset()

        #self.observation_space = spaces.Box(low=-1, high=1, dtype=np.float32, shape=(self.obs_dim,))
        #self.action_space = spaces.Box(low=-1, high=1, dtype=np.float32, shape=(self.act_dim,))


    def setupcam(self):
        self.viewer = mujoco_py.MjViewer(self.sim)
        self.viewer.cam.trackbodyid = -1
        self.viewer.cam.distance = self.model.stat.extent * .3
        self.viewer.cam.lookat[0] = -0.1
        self.viewer.cam.lookat[1] = -1
        self.viewer.cam.lookat[2] = 0.5
        self.viewer.cam.elevation = -30


    def get_state(self):
        return self.sim.get_state()


    def set_state(self, qpos, qvel=None):
        qvel = np.zeros(self.q_dim) if qvel is None else qvel
        old_state = self.sim.get_state()
        new_state = mujoco_py.MjSimState(old_state.time, qpos, qvel,
                                         old_state.act, old_state.udd_state)
        self.sim.set_state(new_state)
        self.sim.forward()


    def scale_action(self, action):
        return (np.array(action) * 0.5 + 0.5) * self.joints_rads_diff + self.joints_rads_low


    def scale_joints(self, joints):
        return ((np.array(joints) - self.joints_rads_low) / self.joints_rads_diff) * 2 - 1


    def get_agent_obs(self):
        qpos = self.sim.get_state().qpos.tolist()
        qvel = self.sim.get_state().qvel.tolist()
        contacts = (np.abs(np.array(self.sim.data.cfrc_ext[[4, 7, 10, 13, 16, 19]])).sum(axis=1) > 0.05).astype(
            np.float32)

        # Joints, joint velocities, quaternion, pose velocities (xd,yd,zd,thd,phd,psid), foot contacts
        return np.concatenate((self.scale_joints(qpos[7:]), qvel[6:], qpos[3:7], qvel[:6], contacts))


    def step(self, ctrl):
        # Clip control signal
        ctrl = np.clip(ctrl, -1, 1)

        # Control penalty
        ctrl_pen = np.square(ctrl).mean()

        # Scale control according to joint ranges
        ctrl = self.scale_action(ctrl)

        # TODO: Fix height issue for the blind envs
        # TODO: Change leg contacts to sensors
        # TODO: Make simple rangefinder sensors for variable envs
        # TODO: Make hetero blind envs
        # TODO: Make rgbd envs
        # TODO: Make Decathlon testing envs (3 at least)

        # Step the simulator
        self.sim.data.ctrl[:] = ctrl
        self.sim.forward()
        self.sim.step()
        self.step_ctr += 1

        # Get agent telemetry data
        _, _, _, qw, qx, qy, qz = self.sim.get_state().qpos.tolist()[:7]
        xd, yd, zd, thd, phid, psid = self.sim.get_state().qvel.tolist()[:6]

        # Reward conditions
        velocity_rew = 1. / (abs(xd - self.target_vel) + 1.) - 1. / (self.target_vel + 1.)
        q_yaw = 2 * acos(qw)

        r = velocity_rew * 5 - \
            np.square(q_yaw) * 2.5 - \
            np.square(ctrl_pen) * 0.3 - \
            np.square(zd) * 0.7

        # Reevaluate termination condition
        done = self.step_ctr > self.max_steps  # or abs(y) > 0.3 or abs(yaw) > 0.6 or abs(roll) > 0.8 or abs(pitch) > 0.8

        return self.get_agent_obs(), r, done, None


    def reset(self):
        # Generate environment
        hm = self.hm_fun(*self.hm_args)
        cv2.imwrite(os.path.join(os.path.dirname(os.path.realpath(__file__)), "hm.png"), hm)

        # Load simulator
        while True:
            try:
                self.model = mujoco_py.load_model_from_path(Hexapod.MODELPATH)
                break
            except Exception:
                pass

        self.sim = mujoco_py.MjSim(self.model)
        self.model.opt.timestep = 0.02
        self.viewer = None

        # Height field
        self.hf_data = self.model.hfield_data
        self.hf_ncol = self.model.hfield_ncol[0]
        self.hf_nrow = self.model.hfield_nrow[0]
        self.hf_column_meters = self.model.hfield_size[0][0] * 2
        self.hf_row_meters = self.model.hfield_size[0][1] * 2
        self.hf_height_meters = self.model.hfield_size[0][2]
        self.pixels_per_column = self.hf_ncol / float(self.hf_column_meters)
        self.pixels_per_row = self.hf_nrow / float(self.hf_row_meters)
        self.hf_grid = self.hf_data.reshape((self.hf_nrow, self.hf_ncol))

        local_grid = self.hf_grid[45:55, 5:15]
        max_height = np.max(local_grid) * self.hf_height_meters

        # Environment dimensions
        self.q_dim = self.sim.get_state().qpos.shape[0]
        self.qvel_dim = self.sim.get_state().qvel.shape[0]

        self.obs_dim = 18 + 18 + 4 + 6 + 6 # j, jd, quat, pose_velocity, contacts
        self.act_dim = self.sim.data.actuator_length.shape[0]

        # Set initial position
        init_q = np.zeros(self.q_dim, dtype=np.float32)
        init_q[0] = 0.0
        init_q[1] = 0.0
        init_q[2] = max_height + 0.05
        init_qvel = np.random.randn(self.qvel_dim).astype(np.float32) * 0.1

        # Set environment state
        self.set_state(init_q, init_qvel)
        self.step_ctr = 0

        obs, _, _, _ = self.step(np.zeros(self.act_dim))

        return obs


    def render(self, camera=None):
        if self.viewer is None:
            self.setupcam()
        self.viewer.render()


    def test(self, policy, render=True):
        N = 30
        rew = 0
        for i in range(N):
            obs = self.reset()
            cr = 0
            for j in range(int(self.max_steps)):
                action = policy(my_utils.to_tensor(obs, True)).detach()
                obs, r, done, od, = self.step(action[0].numpy())
                cr += r
                rew += r
                time.sleep(0.000)
                if render:
                    self.render()
            print("Total episode reward: {}".format(cr))
        print("Total average reward = {}".format(rew / N))


    def demo(self):
        for i in range(100000):
            self.sim.forward()
            self.sim.step()
            self.render()


if __name__ == "__main__":
    hex = Hexapod(hf_gen.hm_perlin, 1)
    hex.demo()