import numpy as np
import gym
import cma
from time import sleep
import quaternion
import torch
import torch as T
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.convert_parameters import vector_to_parameters, parameters_to_vector
import time

class LinearPolicy(nn.Module):
    def __init__(self, obs_dim, act_dim):
        super(LinearPolicy, self).__init__()
        self.fc1 = nn.Linear(obs_dim, act_dim)

    def forward(self, x):
        x = T.tanh(self.fc1(x))
        return x


class NN(nn.Module):
    def __init__(self, obs_dim, act_dim):
        super(NN, self).__init__()
        self.fc1 = nn.Linear(obs_dim, 32)
        self.fc2 = nn.Linear(32, 12)
        self.fc3 = nn.Linear(12, act_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = T.tanh(self.fc3(x))
        return x


def f_wrapper(env, policy):
    def f(w):
        reward = 0
        done = False
        obs, _ = env.reset()

        vector_to_parameters(torch.from_numpy(w).float(), policy.parameters())

        while not done:

            # Get action from policy
            with torch.no_grad():
                act = policy(torch.from_numpy(np.expand_dims(obs, 0)))[0].numpy()

            # Step environment
            obs, rew, done, _ = env.step(act)

            reward += rew

        return -reward
    return f


def train(params):
    env, iters, n_hidden, animate = params

    obs_dim, act_dim = env.obs_dim, env.act_dim
    policy = NN(obs_dim, act_dim).float()
    w = parameters_to_vector(policy.parameters()).detach().numpy()
    es = cma.CMAEvolutionStrategy(w, 0.5)
    f = f_wrapper(env, policy)

    print("Env: {} Action space: {}, observation space: {}, N_params: {}, comments: ...".format("Ant_reach", env.act_dim,
                                                                                  env.obs_dim, len(w)))

    try:
        while not es.stop():
            X = es.ask()
            es.tell(X, [f(x) for x in X])
            es.disp()
    except KeyboardInterrupt:
        print("User interrupted process.")

    return es.result.fbest


from envs.ant_reach.ant_reach import AntReach

env = AntReach()
train((env, 3000, 7, True))


