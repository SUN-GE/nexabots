import numpy as np
import cma
from time import sleep
import torch
import torch as T
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.convert_parameters import vector_to_parameters, parameters_to_vector
import time
import mujoco_py

from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import multiprocessing as mp
import os
from copy import deepcopy

import src.my_utils as my_utils
import src.policies as policies
import random
import string

T.set_num_threads(1)

def f_wrapper(env, policy, animate):
    def f(w):
        reward = 0
        done = False
        obs, _ = env.reset()

        vector_to_parameters(torch.from_numpy(w).float(), policy.parameters())

        h_0 = policy.init_hidden()
        while not done:

            # Get action from policy
            with torch.no_grad():
                act, h_1 = policy((my_utils.to_tensor(obs, True), h_0))

            # Step environment
            obs, rew, done, _ = env.step(act.squeeze(0).numpy())

            if animate:
                env.render()

            reward += rew

            h_0 = h_1

        return -reward
    return f


def train(params):
    env, policy, iters, animate, ID = params

    obs_dim, act_dim = env.obs_dim, env.act_dim

    w = parameters_to_vector(policy.parameters()).detach().numpy()
    es = cma.CMAEvolutionStrategy(w, 0.5)
    f = f_wrapper(env, policy, animate)

    print("Env: {}, Policy: {}, Action space: {}, observation space: {},"
          " N_params: {}, comments: ...".format(
        env.__class__.__name__, policy.__class__.__name__, act_dim, obs_dim, len(w)))

    it = 0
    try:
        while not es.stop():
            it += 1
            if it > iters:
                break
            if it % 1000 == 0:
                sdir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                    "agents/{}_{}_{}_es.p".format(env.__class__.__name__, policy.__class__.__name__,
                                                                  ID))
                vector_to_parameters(torch.from_numpy(es.result.xbest).float(), policy.parameters())
                T.save(policy, sdir)
                print("Saved checkpoint")
            X = es.ask()
            es.tell(X, [f(x) for x in X])
            es.disp()
    except KeyboardInterrupt:
        print("User interrupted process.")

    return es.result.fbest


from src.envs.hexapod_mjc import hexapod
env = hexapod.Hexapod()

#from src.envs.ant_feelers_mjc import ant_feelers_mjc
#env = ant_feelers_mjc.AntFeelersMjc()

policy = policies.RNN(env)
ID = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))

TRAIN = False

if TRAIN:
    t1 = time.clock()
    train((env, policy, 100000, True, ID))
    t2 = time.clock()
    print("Elapsed time: {}".format(t2 - t1))
else:
    policy = T.load("agents/Hexapod_RNN_YRA_es.p")
    env.test_recurrent(policy)

print("Done.")

