"""
Classic cart-pole system implemented by Rich Sutton et al.
Copied from https://webdocs.cs.ualberta.ca/~sutton/book/code/pole.c
"""
import os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
os.sys.path.insert(0, parentdir)

import math
import numpy as np
import pybullet as p

import numpy as np
import cv2
import src.my_utils as my_utils
import time
import socket


class CartPoleBulletEnv():
    def __init__(self, animate=False):
        if (animate):
          p.connect(p.GUI)
        else:
          p.connect(p.DIRECT)

        # Simulator parameters
        self.max_steps = 300
        self.obs_dim = 4
        self.act_dim = 1

        self.cartpole = p.loadURDF(os.path.join(os.path.dirname(os.path.realpath(__file__)), "cartpole.urdf"),
                                   [0, 0, 0])
        self.timeStep = 0.02
        p.setGravity(0, 0, -9.8)
        p.setTimeStep(self.timeStep)
        p.setRealTimeSimulation(0)


    def step(self, ctrl):
        #p.setJointMotorControl2(self.cartpole, 0, p.TORQUE_CONTROL, force=ctrl)
        p.stepSimulation()

        self.step_ctr += 1

        # x, x_dot, theta, theta_dot
        self.state = p.getJointState(self.cartpole, 0)[0:2] + p.getJointState(self.cartpole, 1)[0:2]
        self.state = np.array(self.state)

        done = self.step_ctr > self.max_steps

        # Penalize angle deviation and cart from center
        r = np.square(self.state[0]) + np.square(self.state[2])

        return self.state, r, done, None


    def reset(self):
        self.step_ctr = 1
        p.resetSimulation()

        obs, _, _, _ = self.step(np.zeros(self.act_dim))
        return obs


    def test(self, policy):
        self.render_prob = 1.0
        total_rew = 0
        for i in range(100):
            obs = self.reset()
            cr = 0
            for j in range(self.max_steps):
                action = policy(my_utils.to_tensor(obs, True)).detach()
                obs, r, done, od, = self.step(action[0].numpy())
                cr += r
                total_rew += r
                time.sleep(0.001)
                self.render()
            print("Total episode reward: {}".format(cr))
        print("Total reward: {}".format(total_rew))


    def test_recurrent(self, policy):
        total_rew = 0
        self.render_prob = 1.0
        for i in range(100):
            obs = self.reset()
            h = None
            cr = 0
            for j in range(self.max_steps):
                action, h_ = policy((my_utils.to_tensor(obs, True), h))
                h = h_
                obs, r, done, od, = self.step(action[0].detach().numpy())
                cr += r
                total_rew += r
                time.sleep(0.001)
                self.render()
            print("Total episode reward: {}".format(cr))
        print("Total reward: {}".format(total_rew))


    def demo(self):
        for i in range(100):
            self.reset()
            for j in range(self.max_steps):
                self.step(np.random.rand(self.act_dim) * 2 - 1)


if __name__ == "__main__":
    env = CartPoleBulletEnv(animate=True)
    env.demo()