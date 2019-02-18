import torch.nn as nn
import torch.nn.functional as F
import torch as T
import numpy as np
from copy import deepcopy

class Baseline(nn.Module):
    def __init__(self, N):
        super(Baseline, self).__init__()
        self.N_links = int(N / 2)
        self.fc1 = nn.Linear(93, 40)

    def forward(self, x):
        x = self.fc1(x)
        return x


class NN(nn.Module):
    def __init__(self, env):
        super(NN, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.fc1 = nn.Linear(self.obs_dim, 42)
        self.fc2 = nn.Linear(42, 42)
        self.fc3 = nn.Linear(42, self.act_dim)


    def forward(self, x):
        x = T.tanh(self.fc1(x))
        x = T.tanh(self.fc2(x))
        x = self.fc3(x)
        return x


class NN_D(nn.Module):
    def __init__(self, env):
        super(NN_D, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim
        self.hid_dim = 12

        self.fc1 = nn.Linear(self.obs_dim, self.hid_dim)
        self.fc2 = nn.Linear(self.hid_dim, self.hid_dim)
        self.fc3 = nn.Linear(self.hid_dim, self.act_dim)


    def forward(self, x):
        x = T.tanh(self.fc1(x))
        x = T.tanh(self.fc2(x))
        x = F.softmax(self.fc3(x))
        x = T.argmax(x, 1, keepdim=True)
        return x


class RND_D(nn.Module):
    def __init__(self, env):
        super(RND_D, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.dummy = nn.Linear(1,1)


    def forward(self, _):
        x = T.randn(1, self.act_dim)
        return T.argmax(x, 1, keepdim=True)


class RND(nn.Module):
    def __init__(self, env):
        super(RND, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.dummy = nn.Linear(1,1)


    def forward(self, _):
        return T.randn(1, self.act_dim)


    def sample_action(self, _):
        return self.forward(None)


class ConvPolicy14(nn.Module):
    def __init__(self, N):
        super(ConvPolicy14, self).__init__()
        self.N_links = int(N / 2)

        # rep conv
        self.conv_1 = nn.Conv1d(12, 6, kernel_size=3, stride=1)
        self.conv_2 = nn.Conv1d(6, 8, kernel_size=3, stride=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)
        self.downsample = nn.AdaptiveAvgPool1d(3)
        self.pool = nn.AdaptiveAvgPool1d(1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(13, 10, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(10, 10, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(10, 6, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_3 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_4 = nn.ConvTranspose1d(18, 6, kernel_size=3, stride=1, padding=1)

        self.afun = F.tanh


    def forward(self, x):
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]

        # (psi, psid)
        ext_obs = T.cat((obs[:, 3:7], obsd[:, -1:]), 1)

        # Joints angles
        jl = T.cat((T.zeros(1, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((1, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(1, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]), 1)
        jdlrs = jdl.view((1, 6, -1))

        jcat = T.cat((jlrs, jdlrs), 1) # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(jcat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_c3, ext_obs.unsqueeze(2)),1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc3 = self.afun(self.deconv_3(fm_dc2))
        fm_dc4 = self.deconv_4(T.cat((fm_dc3, jcat), 1))

        acts = fm_dc4.squeeze(2).view((1, -1))

        return acts[:, 2:]


class ConvPolicy8(nn.Module):
    def __init__(self):
        super(ConvPolicy8, self).__init__()
        self.N_links = int(8 / 2)

        # rep conv
        self.conv_1 = nn.Conv1d(12, 4, kernel_size=3, stride=1, padding=1)
        self.conv_2 = nn.Conv1d(4, 8, kernel_size=3, stride=1, padding=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)
        self.conv_4 = nn.Conv1d(8, 8, kernel_size=2, stride=1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(13, 8, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(8, 8, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(8, 4, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(4, 4, kernel_size=3, stride=1, padding=1)
        self.deconv_3 = nn.ConvTranspose1d(4, 8, kernel_size=3, stride=1, padding=1)
        self.deconv_4 = nn.ConvTranspose1d(14, 6, kernel_size=3, stride=1, padding=1)

        self.afun = T.tanh

    def forward(self, x):
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]

        # (psi, psid)
        ext_obs = T.cat((obs[:,3:7], obsd[:, -1:]), 1)

        # Joints angles
        jl = T.cat((T.zeros(1, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((1, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(1, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]), 1)
        jdlrs = jdl.view((1, 6, -1))

        jcat = T.cat((jlrs, jdlrs), 1) # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(jcat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))
        fm_c4 = self.afun(self.conv_4(fm_c3))

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_c4, ext_obs.unsqueeze(2)),1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc3 = self.afun(self.deconv_3(fm_dc2))
        fm_upsampled = F.interpolate(fm_dc3, size=4)
        fm_dc4 = self.afun(self.deconv_4(T.cat((fm_upsampled, jlrs), 1)))

        acts = fm_dc4.squeeze(2).view((1, -1))

        return acts[:, 2:]


class RecPolicy(nn.Module):
    def __init__(self, N):
        super(RecPolicy, self).__init__()

        # Amount of cells that the centipede has
        self.N_links = int(N / 2)

        # Cell RNN hidden
        self.n_hidden = 8

        # RNN for upwards pass
        self.r_up = nn.RNNCell(12, self.n_hidden)

        # Global obs
        self.fc_obs_1 = nn.Linear(13, self.n_hidden)
        self.fc_obs_2 = nn.Linear(self.n_hidden, self.n_hidden)

        # RNN for backwards pass
        self.r_down = nn.RNNCell(self.n_hidden, self.n_hidden)

        # From hidden to cell actions
        self.cell_unfc1 = nn.Linear(self.n_hidden * 2, 6)

        # Last conv layer to join with local observations
        #self.unconv_act = nn.Conv1d(3, 1, 1)

        self.afun = T.tanh


    def forward(self, x):
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]
        obs_cat = T.cat((obs, obsd), 1)

        jl = T.cat((T.zeros(1, 2), x[:, 7:7 + self.N_links * 6 - 2]),1)
        jdl = T.cat((T.zeros(1, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]),1)

        h = T.zeros(1, self.n_hidden)

        h_up = []
        for i in reversed(range(self.N_links)):
            h_up.append(h)
            shift = 6 * i
            j = jl[:, shift:shift + 6]
            jd = jdl[:, shift:shift + 6]
            local_c = T.cat((j, jd), 1)
            h = self.r_up(local_c, h)

        h_up.reverse()
        h = self.afun(self.fc_obs_2(self.afun(self.fc_obs_1(obs_cat))))

        acts = []
        for i in range(self.N_links):
            shift = 6 * i
            j = jl[:, shift:shift + 6]
            jd = jdl[:, shift:shift + 6]
            jcat = T.cat((j.unsqueeze(1),jd.unsqueeze(1)), 1)


            # act_h = self.cell_unfc1(T.cat((h, h_up[i]), 1))
            # act_cat = T.cat((jcat, act_h.unsqueeze(1)), 1)
            # act_final = self.unconv_act(act_cat).squeeze(1)

            act_final = self.cell_unfc1(T.cat((h, h_up[i]), 1))
            acts.append(act_final)
            h = self.r_down(h_up[i], h)

        return T.cat(acts, 1)[:, 2:]


class StatePolicy(nn.Module):
    def __init__(self, env):
        super(StatePolicy, self).__init__()
        self.N_links = env.N_links
        self.act_dim = self.N_links * 6 - 2

        # Rep conv
        self.conv_1 = nn.Conv1d(7, 7, kernel_size=3, stride=1, padding=1)

        # Obs to state
        self.comp_mat = nn.Parameter(T.randn(1, 10, 1, 3))

        # State to action
        self.act_mat = nn.Parameter(T.randn(1, 6, 1, 2))

        # States
        self.reset()

        self.afun = T.tanh

    def forward(self, x):
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]

        # (psi, psid)
        ext_rs = T.cat((obs[0,3:7].view(1,1,1,4), obsd[:, 0:1].view(1,1,1,1)), 3).repeat(1,1,self.N_links,1)

        # Joints angles
        jl = T.cat((T.zeros(1, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((1, 6, self.N_links, 1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(1, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]), 1)
        jdlrs = jdl.view((1, 6, self.N_links, 1))

        obscat = T.cat((T.cat((jlrs, jdlrs), 3), ext_rs), 1) # Concatenate j and jd so that they are 2 parallel channels

        comp_mat_full = self.comp_mat.repeat(1,1,self.N_links,1)
        states = self.states
        for i in range(3):
            # Concatenate observations with states
            x = T.cat((obscat, states), 3)

            # Multiply elementwise through last layer to get prestate map
            x = self.afun((x * comp_mat_full).sum(3))

            # Convolve prestate map to get new states
            states = self.afun(self.conv_1(x).unsqueeze(3))

        # Turn states into actions
        acts = self.act_mat.repeat(1,1,self.N_links,1) * T.cat((states[:,:6,:,:], jdlrs), 3)
        acts = acts.sum(3).view((1, -1))

        return acts[:, 2:]

    def reset(self):
        self.states = T.randn(1, 7, self.N_links, 1)


class PhasePolicy(nn.Module):
    def __init__(self, N):
        super(PhasePolicy, self).__init__()
        self.N_links = int(N / 2)

        # Set phase states
        self.reset()

        # Increment matrix which will be added to phases every step
        self.step_increment = T.ones(1, 6, self.N_links) * 0.01

        self.conv_obs = nn.Conv1d(10, 6, kernel_size=3, stride=1, padding=1)
        self.conv_phase = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)

        self.afun = T.tanh


    def step_phase(self):
        self.phases = T.fmod(self.phases + self.step_increment, 2)


    def modify_phase(self, mask):
        self.phases = T.fmod(self.phases + mask, np.pi)


    def reset(self):
        self.phases = T.randn(1, 6, self.N_links) * 0.01


    def forward(self, x):
        obs = x[:, :7]

        # (psi, psid)
        ext_rs = obs[0,3:7].view(1,4,1).repeat(1,1,self.N_links)

        # Joints angles
        jl = T.cat((T.zeros(1, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((1, 6, self.N_links))

        obscat = T.cat((jlrs, ext_rs), 1) # Concatenate j and jd so that they are 2 parallel channels

        phase_fm = self.afun(self.conv_obs(obscat))
        phase_deltas = self.afun(self.conv_phase(phase_fm))

        self.modify_phase(phase_deltas)
        self.step_phase()

        # Phases directly translate into torques
        acts = self.phases.view(1,-1) - 1

        # Phases are desired angles
        #acts = (((self.phases - (np.pi / 2)) - jlrs) * 0.1).view(1,-1)


        return acts[:, 2:]


class ConvPolicy_Iter_PG(nn.Module):
    def __init__(self, env):
        super(ConvPolicy_Iter_PG, self).__init__()
        self.N_links = env.N_links
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(17, 6, kernel_size=3, stride=1, padding=1)
        self.conv_2 = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)
        self.conv_3 = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)
        self.conv_4 = nn.Conv1d(12, 6, kernel_size=3, stride=1, padding=1)
        #self.conv_5 = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)

        self.afun = F.selu
        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        M = x.shape[0]
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]

        # (psi, psid)
        ext_obs = T.cat((obs[:, 3:7], obsd[:, -1:]), 1).unsqueeze(2)
        ext_obs_rep = ext_obs.repeat((1, 1, self.N_links))

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(M, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]), 1)
        jdlrs = jdl.view((M, 6, -1))

        ocat = T.cat((jlrs, jdlrs, ext_obs_rep), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(ocat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))
        fm_c4 = self.conv_4(T.cat((fm_c3, jlrs), 1))

        acts = fm_c4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class ConvPolicy_Iter_PG_new(nn.Module):
    def __init__(self, env):
        super(ConvPolicy_Iter_PG_new, self).__init__()
        self.N_links = env.N_links
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(20, 6, kernel_size=3, stride=1, padding=1)
        self.conv_2 = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)
        self.conv_3 = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)
        self.conv_4 = nn.Conv1d(14, 6, kernel_size=3, stride=1, padding=1)

        self.afun = F.selu
        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        # Batch dimension
        M = x.shape[0]

        # z, qw, qx, qy, qz [b,5]
        obs = x[:, :5]

        # xd, yd, xz, xangd, yangd, zangd [b, 6]
        obsd = x[:, 5 + self.N_links * 6 - 2: 5 + self.N_links * 6 - 2 + 6]

        # qw, qx, qy, qz, xd, yd [b, 6]
        ext_obs = T.cat((obs[:, 1:5], obsd[:, 0:2]), 1).unsqueeze(2)
        ext_obs_rep = ext_obs.repeat((1, 1, self.N_links))

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 5:5 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(M, 2), x[:, 5 + self.N_links * 6 - 2 + 6:5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2]), 1)
        jdlrs = jdl.view((M, 6, -1))

        # Contacts
        jcl = x[:, 5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2:]
        jclrs = jcl.view((M, 2, -1))

        ocat = T.cat((jlrs, jdlrs, ext_obs_rep, jclrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(ocat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))
        fm_c4 = self.conv_4(T.cat((fm_c3, jlrs, jclrs), 1))

        acts = fm_c4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class ConvPolicy_Iter_PG_c(nn.Module):
    def __init__(self, env):
        super(ConvPolicy_Iter_PG_c, self).__init__()
        self.N_links = env.N_links
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(20, 6, kernel_size=3, stride=1, padding=1)

        self.afun = F.selu
        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        # Batch dimension
        M = x.shape[0]

        # z, qw, qx, qy, qz [b,5]
        obs = x[:, :5]

        # xd, yd, xz, xangd, yangd, zangd [b, 6]
        obsd = x[:, 5 + self.N_links * 6 - 2: 5 + self.N_links * 6 - 2 + 6]

        # qw, qx, qy, qz, xd, yd [b, 6]
        ext_obs = T.cat((obs[:, 1:5], obsd[:, 0:2]), 1).unsqueeze(2)
        ext_obs_rep = ext_obs.repeat((1, 1, self.N_links))

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 5:5 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(M, 2), x[:, 5 + self.N_links * 6 - 2 + 6:5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2]), 1)
        jdlrs = jdl.view((M, 6, -1))

        # Contacts
        jcl = x[:, 5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2:]
        jclrs = jcl.view((M, 2, -1))

        ocat = T.cat((jlrs, jdlrs, ext_obs_rep, jclrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = T.tanh(self.conv_1(ocat))

        acts = fm_c1.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class ConvPolicy8_PG(nn.Module):
    def __init__(self, env):
        super(ConvPolicy8_PG, self).__init__()
        self.N_links = 4
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(12, 4, kernel_size=3, stride=1, padding=1)
        self.conv_2 = nn.Conv1d(4, 8, kernel_size=3, stride=1, padding=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)
        self.conv_4 = nn.Conv1d(8, 8, kernel_size=2, stride=1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(13, 8, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(8, 8, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(8, 4, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(4, 4, kernel_size=3, stride=1, padding=1)
        self.deconv_3 = nn.ConvTranspose1d(4, 8, kernel_size=3, stride=1, padding=1)
        self.deconv_4 = nn.ConvTranspose1d(14, 6, kernel_size=3, stride=1, padding=1)

        self.upsample = nn.Upsample(size=4)

        self.afun = F.selu

        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        N = x.shape[0]
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]

        # (psi, psid)
        ext_obs = T.cat((obs[:, 3:7], obsd[:, -1:]), 1)

        # Joints angles
        jl = T.cat((T.zeros(N, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((N, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(N, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]), 1)
        jdlrs = jdl.view((N, 6, -1))

        jcat = T.cat((jlrs, jdlrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(jcat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))
        fm_c4 = self.afun(self.conv_4(fm_c3))

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_c4, ext_obs.unsqueeze(2)), 1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc3 = self.afun(self.deconv_3(fm_dc2))
        fm_upsampled = F.interpolate(fm_dc3, size=4)
        fm_dc4 = self.deconv_4(T.cat((fm_upsampled, jlrs), 1))

        acts = fm_dc4.squeeze(2).view((N, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class ConvPolicy14_PG(nn.Module):
    def __init__(self, env):
        super(ConvPolicy14_PG, self).__init__()
        self.N_links = 7

        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(12, 6, kernel_size=3, stride=1)
        self.conv_2 = nn.Conv1d(6, 8, kernel_size=3, stride=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)
        self.downsample = nn.AdaptiveAvgPool1d(3)
        self.pool = nn.AdaptiveAvgPool1d(1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(13, 10, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(10, 10, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(10, 6, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_3 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_4 = nn.ConvTranspose1d(18, 6, kernel_size=3, stride=1, padding=1)

        self.afun = F.selu

        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        M = x.shape[0]
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]
        self.log_std = T.zeros(1, self.act_dim)
        # (psi, psid)
        ext_obs = T.cat((obs[:, 3:7], obsd[:, -1:]), 1)

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(M, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]), 1)
        jdlrs = jdl.view((M, 6, -1))

        jcat = T.cat((jlrs, jdlrs), 1) # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(jcat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_c3, ext_obs.unsqueeze(2)),1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc3 = self.afun(self.deconv_3(fm_dc2))
        fm_dc4 = self.deconv_4(T.cat((fm_dc3, jcat), 1))

        acts = fm_dc4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class ConvPolicy30_PG(nn.Module):
    def __init__(self, env):
        super(ConvPolicy30_PG, self).__init__()
        self.N_links = 15
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(12, 6, kernel_size=3, stride=1)
        self.conv_2 = nn.Conv1d(6, 8, kernel_size=3, stride=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)
        self.downsample = nn.AdaptiveAvgPool1d(5)
        self.pool = nn.AdaptiveAvgPool1d(1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(13, 10, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(10, 10, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(10, 6, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_3 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_4 = nn.ConvTranspose1d(18, 6, kernel_size=3, stride=1, padding=1)
        self.upsample = nn.Upsample(size=13)

        self.afun = F.selu

        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        M = x.shape[0]
        obs = x[:, :7]
        obsd = x[:, 7 + self.N_links * 6 - 2: 7 + self.N_links * 6 - 2 + 6]

        # (psi, psid)
        ext_obs = T.cat((obs[:, 3:7], obsd[:, -1:]), 1)

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 7:7 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(M, 2), x[:, 7 + self.N_links * 6 - 2 + 6:]), 1)
        jdlrs = jdl.view((M, 6, -1))

        jcat = T.cat((jlrs, jdlrs), 1) # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(jcat))
        fm_c1_ds = self.downsample(fm_c1)
        fm_c2 = self.afun(self.conv_2(fm_c1_ds))
        fm_c3 = self.afun(self.conv_3(fm_c2))

        # Avg pool through link channels
        fm_links = self.pool(fm_c3) # (1, N, 1)

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_links, ext_obs.unsqueeze(2)),1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc2_us = self.upsample(fm_dc2)
        fm_dc3 = self.afun(self.deconv_3(fm_dc2_us))
        fm_dc4 = self.deconv_4(T.cat((fm_dc3, jcat), 1)) # Change jcat to jlrs

        acts = fm_dc4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class NN_PG(nn.Module):
    def __init__(self, env):
        super(NN_PG, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.fc1 = nn.Linear(self.obs_dim, 64)
        #self.bn1 = nn.BatchNorm1d(64)
        self.fc2 = nn.Linear(64, 64)
        #self.bn2 = nn.BatchNorm2d(64)
        self.fc3 = nn.Linear(64, self.act_dim)

        #self.log_std = nn.Parameter(T.zeros(1, self.act_dim))
        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        x = F.selu(self.fc1(x))
        x = F.selu(self.fc2(x))
        x = self.fc3(x)
        return x


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class NN_PG_MICRO(nn.Module):
    def __init__(self, env):
        super(NN_PG_MICRO, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.fc1 = nn.Linear(self.obs_dim, 24)
        self.fc2 = nn.Linear(24, self.act_dim)

        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        x = T.tanh(self.fc1(x))
        x = T.tanh(self.fc2(x))
        return x


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class NN_PG_D(nn.Module):
    def __init__(self, env):
        super(NN_PG_D, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.hid_dim = 8
        self.fc1 = nn.Linear(self.obs_dim, self.hid_dim)
        self.fc2 = nn.Linear(self.hid_dim, self.hid_dim)
        self.fc3 = nn.Linear(self.hid_dim, self.act_dim)


    def forward(self, x):
        x = F.selu(self.fc1(x))
        x = F.selu(self.fc2(x))
        x = F.softmax(self.fc3(x))
        return x


    def sample_action(self, s):
        x = self.forward(s)
        return x.multinomial(1)


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_softmax = self.forward(batch_states)
        return T.log(action_softmax.gather(1, batch_actions.long()))


class NN_PG_F(nn.Module):
    def __init__(self, env):
        super(NN_PG_F, self).__init__()
        self.obs_dim = env.obs_dim - 7 * 5 - 6 * 5 + 6 - 2
        self.act_dim = env.act_dim

        self.fc1 = nn.Linear(self.obs_dim, 64)
        #self.bn1 = nn.BatchNorm1d(64)
        self.fc2 = nn.Linear(64, 64)
        #self.bn2 = nn.BatchNorm2d(64)
        self.fc3 = nn.Linear(64, self.act_dim)

        #self.log_std = nn.Parameter(T.zeros(1, self.act_dim))
        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        x = F.selu(self.fc1(x))
        x = F.selu(self.fc2(x))
        x = self.fc3(x)
        return x


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class CNN_PG(nn.Module):
    def __init__(self, env):
        super(CNN_PG, self).__init__()
        self.obs_dim = env.obs_dim - (24**2 * 2)
        self.act_dim = env.act_dim

        self.conv1 = nn.Conv2d(2, 8, 5, 1, 2)
        self.conv2 = nn.Conv2d(8, 8, 5, 1, 2)
        self.conv3 = nn.Conv2d(8, 8, 3, 1, 1)

        self.fcc = nn.Linear(6 * 6 * 8, 32)
        self.fcj = nn.Bilinear(32, self.obs_dim, 48)

        self.fc1 = nn.Linear(48, 48)
        self.fc2 = nn.Linear(48, self.act_dim)

        #self.log_std = nn.Parameter(T.zeros(1, self.act_dim))
        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        x_obs = x[:, :self.obs_dim]
        x_img = x[:, self.obs_dim:].view(x.shape[0], 2, 24, 24)

        c = F.avg_pool2d(F.selu(self.conv1(x_img)), 2)
        c = F.avg_pool2d(F.selu(self.conv2(c)), 2)
        c = F.selu(self.conv3(c))
        c = c.view(x.shape[0], 6 * 6 * 8)
        c = F.selu(self.fcc(c))

        x = self.fcj(c, x_obs)

        x = F.selu(self.fc1(x))
        x = self.fc2(x)
        return x


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class RNN_PG(nn.Module):
    def __init__(self, env):
        super(RNN_PG, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim
        self.hid_dim = 64

        self.rnn = nn.LSTMCell(self.obs_dim, self.hid_dim)
        self.batch_rnn = nn.LSTM(input_size=self.obs_dim,
                                hidden_size=self.hid_dim,
                                batch_first=True)


        self.fc1 = nn.Linear(self.obs_dim, self.obs_dim)
        self.fc2 = nn.Linear(self.hid_dim, self.act_dim)

        self.log_std = T.zeros(1, self.act_dim)


    def print_info(self):
        print("-------------------------------")
        print("w_hh", self.batch_rnn.weight_hh_l0.data.max(), self.batch_rnn.weight_hh_l0.data.min())
        print("w_ih", self.batch_rnn.weight_ih_l0.data.max(), self.batch_rnn.weight_ih_l0.data.min())
        print("b_hh", self.batch_rnn.bias_hh_l0.data.max(), self.batch_rnn.bias_hh_l0.data.min())
        print("b_ih", self.batch_rnn.bias_ih_l0.data.max(), self.batch_rnn.bias_ih_l0.data.min())
        print("w_fc1", self.fc1.weight.data.max(), self.fc1.weight.data.min())
        print("b_fc1", self.fc1.bias.data.max(), self.fc1.weight.data.min())
        print("w_fc2", self.fc2.weight.data.max(), self.fc2.weight.data.min())
        print("b_fc2", self.fc2.bias.data.max(), self.fc1.weight.data.min())
        print("---")
        print("w_hh grad", self.batch_rnn.weight_hh_l0.grad.max(), self.batch_rnn.weight_hh_l0.grad.min())
        print("w_ih grad", self.batch_rnn.weight_ih_l0.grad.max(), self.batch_rnn.weight_ih_l0.grad.min())
        print("b_hh grad", self.batch_rnn.bias_hh_l0.grad.max(), self.batch_rnn.bias_hh_l0.grad.min())
        print("b_ih grad", self.batch_rnn.bias_ih_l0.grad.max(), self.batch_rnn.bias_ih_l0.grad.min())
        print("w_fc1 grad", self.fc1.weight.grad.max(), self.fc1.weight.grad.min())
        print("b_fc1 grad", self.fc1.bias.grad.max(), self.fc1.bias.grad.min())
        print("w_fc2 grad", self.fc2.weight.grad.max(), self.fc2.weight.grad.min())
        print("b_fc2 grad", self.fc2.bias.grad.max(), self.fc2.bias.grad.min())
        print("-------------------------------")


    def rnn_params(self):
        return self.batch_rnn.parameters()


    def policy_params(self):
        return list(self.fc1.parameters()) + list(self.fc2.parameters())


    def clip_grads(self, bnd=1):
        self.batch_rnn.weight_hh_l0.grad.clamp_(-bnd, bnd)
        self.batch_rnn.weight_ih_l0.grad.clamp_(-bnd, bnd)
        self.batch_rnn.bias_hh_l0.grad.clamp_(-bnd, bnd)
        self.batch_rnn.bias_ih_l0.grad.clamp_(-bnd, bnd)
        self.fc1.weight.grad.clamp_(-bnd, bnd)
        self.fc1.bias.grad.clamp_(-bnd, bnd)
        self.fc2.weight.grad.clamp_(-bnd, bnd)
        self.fc2.bias.grad.clamp_(-bnd, bnd)


    def clone_params(self):
        self.rnn.bias_hh.data = deepcopy(self.batch_rnn.bias_hh_l0.data)
        self.rnn.bias_ih.data = deepcopy(self.batch_rnn.bias_ih_l0.data)
        self.rnn.weight_hh.data = deepcopy(self.batch_rnn.weight_hh_l0.data)
        self.rnn.weight_ih.data = deepcopy(self.batch_rnn.weight_ih_l0.data)


    def forward(self, input):
        x, h = input
        x = F.relu(self.fc1(x))
        h_, c_ = self.rnn(x, h)
        x = self.fc2(h_)
        return x, (h_, c_)


    def forward_batch(self, batch_states):
        x = F.relu(self.fc1(batch_states))
        x, _ = self.batch_rnn(x)
        x = self.fc2(x)
        return x


    def sample_action(self, s):
        x, h = self.forward(s)
        return T.normal(x, T.exp(self.log_std)), h


    def log_probs(self, batch_states, batch_hiddens, batch_actions):
        # Get action means from policy
        action_means, _ = self.forward(batch_states, batch_hiddens)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


    def log_probs_batch(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward_batch(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(2, keepdim=True)


class RNN_PG_CELL(nn.Module):
    def __init__(self, env):
        super(RNN_PG_CELL, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim
        self.hid_dim = 16

        self.rnn = nn.LSTMCell(self.obs_dim, self.hid_dim)

        self.fc1 = nn.Linear(self.hid_dim, self.hid_dim)
        self.fc2 = nn.Linear(self.hid_dim, self.act_dim)

        self.log_std = T.zeros(1, self.act_dim)


    def print_info(self):
        print("-------------------------------")
        print("w_hh", self.rnn.weight_hh.data.max(), self.rnn.weight_hh.data.min())
        print("w_ih", self.rnn.weight_ih.data.max(), self.rnn.weight_ih.data.min())
        print("b_hh", self.rnn.bias_hh.data.max(), self.rnn.bias_hh.data.min())
        print("b_ih", self.rnn.bias_ih.data.max(), self.rnn.bias_ih.data.min())
        print("w_fc1", self.fc1.weight.data.max(), self.fc1.weight.data.min())
        print("b_fc1", self.fc1.bias.data.max(), self.fc1.weight.data.min())
        print("w_fc2", self.fc2.weight.data.max(), self.fc2.weight.data.min())
        print("b_fc2", self.fc2.bias.data.max(), self.fc1.weight.data.min())
        print("---")
        print("w_hh grad", self.rnn.weight_hh.grad.max(), self.rnn.weight_hh.grad.min())
        print("w_ih grad", self.rnn.weight_ih.grad.max(), self.rnn.weight_ih.grad.min())
        print("b_hh grad", self.rnn.bias_hh.grad.max(), self.rnn.bias_hh.grad.min())
        print("b_ih grad", self.rnn.bias_ih.grad.max(), self.rnn.bias_ih.grad.min())
        print("w_fc1 grad", self.fc1.weight.grad.max(), self.fc1.weight.grad.min())
        print("b_fc1 grad", self.fc1.bias.grad.max(), self.fc1.bias.grad.min())
        print("w_fc2 grad", self.fc2.weight.grad.max(), self.fc2.weight.grad.min())
        print("b_fc2 grad", self.fc2.bias.grad.max(), self.fc2.bias.grad.min())
        print("-------------------------------")


    def rnn_params(self):
        return self.rnn.parameters()


    def policy_params(self):
        return list(self.fc1.parameters()) + list(self.fc2.parameters())


    def clip_grads(self):
        self.rnn.weight_hh.grad.clamp_(-0.5, 0.5)
        self.rnn.weight_ih.grad.clamp_(-0.5, 0.5)
        self.rnn.bias_hh.grad.clamp_(-0.5, 0.5)
        self.rnn.bias_ih.grad.clamp_(-0.5, 0.5)
        self.fc1.weight.grad.clamp_(-0.5, 0.5)
        self.fc1.bias.grad.clamp_(-0.5, 0.5)
        self.fc2.weight.grad.clamp_(-0.5, 0.5)
        self.fc2.bias.grad.clamp_(-0.5, 0.5)


    def forward(self, input):
        x, h = input
        h_, c_ = self.rnn(x, h)
        x = F.relu(self.fc1(h_))
        x = self.fc2(x)
        return x, (h_, c_)


    def sample_action(self, s):
        x, h = self.forward(s)
        return T.normal(x, T.exp(self.log_std)), h


    def log_probs_batch(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = []
        h = None
        for b in batch_states:
            a_mean, h = self.forward((b, h))
            action_means.append(a_mean)

        action_means = T.stack(action_means)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(2, keepdim=True)


class RNN_PG_D(nn.Module):
    def __init__(self, env):
        super(RNN_PG_D, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim
        self.hid_dim = 8

        self.rnn = nn.LSTMCell(self.obs_dim, self.hid_dim)
        self.batch_rnn = nn.LSTM(input_size=self.obs_dim,
                                hidden_size=self.hid_dim,
                                batch_first=True)


        self.fc1 = nn.Linear(self.hid_dim, self.hid_dim)
        self.fc2 = nn.Linear(self.hid_dim, self.act_dim)

        self.log_std = T.zeros(1, self.act_dim)


    def print_info(self):
        print("-------------------------------")
        print("w_hh", self.batch_rnn.weight_hh_l0.data.max(), self.batch_rnn.weight_hh_l0.data.min())
        print("w_ih", self.batch_rnn.weight_ih_l0.data.max(), self.batch_rnn.weight_ih_l0.data.min())
        print("b_hh", self.batch_rnn.bias_hh_l0.data.max(), self.batch_rnn.bias_hh_l0.data.min())
        print("b_ih", self.batch_rnn.bias_ih_l0.data.max(), self.batch_rnn.bias_ih_l0.data.min())
        print("w_fc1", self.fc1.weight.data.max(), self.fc1.weight.data.min())
        print("b_fc1", self.fc1.bias.data.max(), self.fc1.weight.data.min())
        print("w_fc2", self.fc2.weight.data.max(), self.fc2.weight.data.min())
        print("b_fc2", self.fc2.bias.data.max(), self.fc1.weight.data.min())
        print("---")
        print("w_hh grad", self.batch_rnn.weight_hh_l0.grad.max(), self.batch_rnn.weight_hh_l0.grad.min())
        print("w_ih grad", self.batch_rnn.weight_ih_l0.grad.max(), self.batch_rnn.weight_ih_l0.grad.min())
        print("b_hh grad", self.batch_rnn.bias_hh_l0.grad.max(), self.batch_rnn.bias_hh_l0.grad.min())
        print("b_ih grad", self.batch_rnn.bias_ih_l0.grad.max(), self.batch_rnn.bias_ih_l0.grad.min())
        print("w_fc1 grad", self.fc1.weight.grad.max(), self.fc1.weight.grad.min())
        print("b_fc1 grad", self.fc1.bias.grad.max(), self.fc1.bias.grad.min())
        print("w_fc2 grad", self.fc2.weight.grad.max(), self.fc2.weight.grad.min())
        print("b_fc2 grad", self.fc2.bias.grad.max(), self.fc2.bias.grad.min())
        print("-------------------------------")


    def rnn_params(self):
        return self.batch_rnn.parameters()


    def policy_params(self):
        return list(self.fc1.parameters()) + list(self.fc2.parameters())


    def clip_grads(self):
        self.batch_rnn.weight_hh_l0.grad.clamp_(-0.5, 0.5)
        self.batch_rnn.weight_ih_l0.grad.clamp_(-0.5, 0.5)
        self.batch_rnn.bias_hh_l0.grad.clamp_(-0.5, 0.5)
        self.batch_rnn.bias_ih_l0.grad.clamp_(-0.5, 0.5)
        self.fc1.weight.grad.clamp_(-0.5, 0.5)
        self.fc1.bias.grad.clamp_(-0.5, 0.5)
        self.fc2.weight.grad.clamp_(-0.5, 0.5)
        self.fc2.bias.grad.clamp_(-0.5, 0.5)


    def clone_params(self):
        self.rnn.bias_hh.data = deepcopy(self.batch_rnn.bias_hh_l0.data)
        self.rnn.bias_ih.data = deepcopy(self.batch_rnn.bias_ih_l0.data)
        self.rnn.weight_hh.data = deepcopy(self.batch_rnn.weight_hh_l0.data)
        self.rnn.weight_ih.data = deepcopy(self.batch_rnn.weight_ih_l0.data)


    def forward(self, input):
        x, h = input
        h_, c_ = self.rnn(x, h)
        x = F.selu(self.fc1(h_))
        x = F.softmax(self.fc2(x), 1)
        return x, (h_, c_)


    def forward_batch(self, batch_states):
        outputs, _ = self.batch_rnn(batch_states)
        x = F.selu(self.fc1(outputs))
        x = F.softmax(self.fc2(x), 1)
        return x


    def sample_action(self, s):
        x, h = self.forward(s)
        return x.multinomial(1), h


    def log_probs_batch(self, batch_states, batch_actions):
        # Get action means from policy
        action_softmax = self.forward_batch(batch_states)
        return T.log(action_softmax.gather(2, batch_actions.long()))


class RNN(nn.Module):
    def __init__(self, env):
        super(RNN, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim
        self.hid_dim = 8

        self.rnn = nn.RNNCell(self.hid_dim, self.hid_dim)
        self.fc1 = nn.Linear(self.obs_dim, self.hid_dim)
        self.fc2 = nn.Linear(self.hid_dim, self.act_dim)


    def init_hidden(self):
        return T.zeros((1, self.hid_dim))


    def forward(self, input):
        x, h = input
        x = T.tanh(self.fc1(x))
        h_ = self.rnn(x, h)
        x = self.fc2(h_)
        return x, h_


class C_Linear(nn.Module):
    def __init__(self, env):
        super(C_Linear, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.fc1 = nn.Linear(self.obs_dim, self.act_dim)

        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        return self.fc1(x)


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class C_MLP(nn.Module):
    def __init__(self, env):
        super(C_MLP, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim

        self.fc1 = nn.Linear(self.obs_dim, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, self.act_dim)

        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        x = T.tanh(self.fc1(x))
        x = T.tanh(self.fc2(x))
        x = T.tanh(self.fc3(x))
        return x


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class C_ConvPolicy8_CP(nn.Module):
    def __init__(self, env):
        super(C_ConvPolicy8_CP, self).__init__()
        self.N_links = 4
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(14, 4, kernel_size=3, stride=1, padding=1)
        self.conv_2 = nn.Conv1d(4, 8, kernel_size=3, stride=1, padding=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)
        self.conv_4 = nn.Conv1d(8, 8, kernel_size=2, stride=1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(14, 8, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(8, 8, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(8, 4, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(4, 4, kernel_size=3, stride=1, padding=1)
        self.deconv_3 = nn.ConvTranspose1d(4, 6, kernel_size=3, stride=1, padding=1)
        self.deconv_4 = nn.ConvTranspose1d(20, 6, kernel_size=3, stride=1, padding=1)

        self.upsample = nn.Upsample(size=4)

        self.afun = F.selu

        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        # Batch dimension
        M = x.shape[0]

        # z, qw, qx, qy, qz [b,5]
        obs = x[:, :5]

        # xd, yd, xz, xangd, yangd, zangd [b, 6]
        obsd = x[:, 5 + self.N_links * 6 - 2: 5 + self.N_links * 6 - 2 + 6]

        # qw, qx, qy, qz, xd, yd [b, 6]
        ext_obs = T.cat((obs[:, 1:5], obsd[:, 0:2]), 1).unsqueeze(2)

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 5:5 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat(
            (T.zeros(M, 2), x[:, 5 + self.N_links * 6 - 2 + 6:5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2]), 1)
        jdlrs = jdl.view((M, 6, -1))

        # Contacts
        jcl = x[:, 5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2:]
        jclrs = jcl.view((M, 2, -1))

        ocat = T.cat((jlrs, jdlrs, jclrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(ocat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))
        fm_c4 = self.afun(self.conv_4(fm_c3))

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_c4, ext_obs), 1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc3 = self.afun(self.deconv_3(fm_dc2))
        fm_upsampled = F.interpolate(fm_dc3, size=4)
        fm_dc4 = T.tanh(self.deconv_4(T.cat((fm_upsampled, ocat), 1)))

        acts = fm_dc4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class C_ConvPolicy14_CP(nn.Module):
    def __init__(self, env):
        super(C_ConvPolicy14_CP, self).__init__()
        self.N_links = 7

        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(14, 6, kernel_size=3, stride=1)
        self.conv_2 = nn.Conv1d(6, 8, kernel_size=3, stride=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(14, 10, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(10, 10, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(10, 6, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_3 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_4 = nn.ConvTranspose1d(20, 6, kernel_size=3, stride=1, padding=1)

        self.afun = F.selu

        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        # Batch dimension
        M = x.shape[0]

        # z, qw, qx, qy, qz [b,5]
        obs = x[:, :5]

        # xd, yd, xz, xangd, yangd, zangd [b, 6]
        obsd = x[:, 5 + self.N_links * 6 - 2: 5 + self.N_links * 6 - 2 + 6]

        # qw, qx, qy, qz, xd, yd [b, 6]
        ext_obs = T.cat((obs[:, 1:5], obsd[:, 0:2]), 1).unsqueeze(2)

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 5:5 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat(
            (T.zeros(M, 2), x[:, 5 + self.N_links * 6 - 2 + 6:5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2]), 1)
        jdlrs = jdl.view((M, 6, -1))

        # Contacts
        jcl = x[:, 5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2:]
        jclrs = jcl.view((M, 2, -1))

        ocat = T.cat((jlrs, jdlrs, jclrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(ocat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_c3, ext_obs),1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc3 = self.afun(self.deconv_3(fm_dc2))
        fm_dc4 = T.tanh(self.deconv_4(T.cat((fm_dc3, ocat), 1)))

        acts = fm_dc4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class C_ConvPolicy30_CP(nn.Module):
    def __init__(self, env):
        super(C_ConvPolicy30_CP, self).__init__()
        self.N_links = 15
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(14, 6, kernel_size=3, stride=1)
        self.conv_2 = nn.Conv1d(6, 8, kernel_size=3, stride=1)
        self.conv_3 = nn.Conv1d(8, 8, kernel_size=3, stride=1)
        self.downsample = nn.AdaptiveAvgPool1d(5)
        self.pool = nn.AdaptiveAvgPool1d(1)

        # Embedding layers
        self.conv_emb_1 = nn.Conv1d(14, 10, kernel_size=1, stride=1)
        self.conv_emb_2 = nn.Conv1d(10, 10, kernel_size=1, stride=1)

        self.deconv_1 = nn.ConvTranspose1d(10, 6, kernel_size=3, stride=1)
        self.deconv_2 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_3 = nn.ConvTranspose1d(6, 6, kernel_size=3, stride=1)
        self.deconv_4 = nn.ConvTranspose1d(20, 6, kernel_size=3, stride=1, padding=1)
        self.upsample = nn.Upsample(size=13)

        self.afun = F.selu

        self.log_std = T.zeros(1, self.act_dim)


    def forward(self, x):
        # Batch dimension
        M = x.shape[0]

        # z, qw, qx, qy, qz [b,5]
        obs = x[:, :5]

        # xd, yd, xz, xangd, yangd, zangd [b, 6]
        obsd = x[:, 5 + self.N_links * 6 - 2: 5 + self.N_links * 6 - 2 + 6]

        # qw, qx, qy, qz, xd, yd [b, 6]
        ext_obs = T.cat((obs[:, 1:5], obsd[:, 0:2]), 1).unsqueeze(2)

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 5:5 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat(
            (T.zeros(M, 2), x[:, 5 + self.N_links * 6 - 2 + 6:5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2]), 1)
        jdlrs = jdl.view((M, 6, -1))

        # Contacts
        jcl = x[:, 5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2:]
        jclrs = jcl.view((M, 2, -1))

        ocat = T.cat((jlrs, jdlrs, jclrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(ocat))
        fm_c1_ds = self.downsample(fm_c1)
        fm_c2 = self.afun(self.conv_2(fm_c1_ds))
        fm_c3 = self.afun(self.conv_3(fm_c2))

        # Avg pool through link channels
        fm_links = self.pool(fm_c3) # (1, N, 1)

        # Combine obs with featuremaps
        emb_1 = self.afun(self.conv_emb_1(T.cat((fm_links, ext_obs),1)))
        emb_2 = self.afun(self.conv_emb_2(emb_1))

        # Project back to action space
        fm_dc1 = self.afun(self.deconv_1(emb_2))
        fm_dc2 = self.afun(self.deconv_2(fm_dc1))
        fm_dc2_us = self.upsample(fm_dc2)
        fm_dc3 = self.afun(self.deconv_3(fm_dc2_us))
        fm_dc4 = T.tanh(self.deconv_4(T.cat((fm_dc3, ocat), 1))) # Change jcat to jlrs

        acts = fm_dc4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class C_ConvPolicy_Iter_CP(nn.Module):
    def __init__(self, env):
        super(C_ConvPolicy_Iter_CP, self).__init__()
        self.N_links = env.N_links
        self.act_dim = self.N_links * 6 - 2

        # rep conv
        self.conv_1 = nn.Conv1d(20, 6, kernel_size=3, stride=1, padding=1)
        self.conv_2 = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)
        self.conv_3 = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)
        self.conv_4 = nn.Conv1d(14, 6, kernel_size=3, stride=1, padding=1)

        self.afun = F.selu
        self.log_std = T.zeros(1, self.act_dim)

    def forward(self, x):
        # Batch dimension
        M = x.shape[0]

        # z, qw, qx, qy, qz [b,5]
        obs = x[:, :5]

        # xd, yd, xz, xangd, yangd, zangd [b, 6]
        obsd = x[:, 5 + self.N_links * 6 - 2: 5 + self.N_links * 6 - 2 + 6]

        # qw, qx, qy, qz, xd, yd [b, 6]
        ext_obs = T.cat((obs[:, 1:5], obsd[:, 0:2]), 1).unsqueeze(2)
        ext_obs_rep = ext_obs.repeat((1, 1, self.N_links))

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 5:5 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat((T.zeros(M, 2), x[:, 5 + self.N_links * 6 - 2 + 6:5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2]), 1)
        jdlrs = jdl.view((M, 6, -1))

        # Contacts
        jcl = x[:, 5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2:]
        jclrs = jcl.view((M, 2, -1))

        ocat = T.cat((jlrs, jdlrs, ext_obs_rep, jclrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        fm_c1 = self.afun(self.conv_1(ocat))
        fm_c2 = self.afun(self.conv_2(fm_c1))
        fm_c3 = self.afun(self.conv_3(fm_c2))
        fm_c4 = T.tanh(self.conv_4(T.cat((fm_c3, jlrs, jclrs), 1)))

        acts = fm_c4.squeeze(2).view((M, -1))

        return acts[:, 2:]


    def sample_action(self, s):
        return T.normal(self.forward(s), T.exp(self.log_std))


    def log_probs(self, batch_states, batch_actions):
        # Get action means from policy
        action_means = self.forward(batch_states)

        # Calculate probabilities
        log_std_batch = self.log_std.expand_as(action_means)
        std = T.exp(log_std_batch)
        var = std.pow(2)
        log_density = - T.pow(batch_actions - action_means, 2) / (2 * var) - 0.5 * np.log(2 * np.pi) - log_std_batch

        return log_density.sum(1, keepdim=True)


class C_PhasePolicy_ES(nn.Module):
    def __init__(self, env):
        super(C_PhasePolicy_ES, self).__init__()
        self.N_links = env.N_links
        self.act_dim = self.N_links * 6 - 2

        # Set phase states
        self.reset()

        # Increment matrix which will be added to phases every step
        self.step_increment = T.ones(1, 6, self.N_links) * 0.1

        self.conv_obs = nn.Conv1d(20, 6, kernel_size=3, stride=1, padding=1)
        self.conv_phase = nn.Conv1d(6, 6, kernel_size=3, stride=1, padding=1)

        self.afun = T.tanh


    def step_phase(self):
        self.phases = T.fmod(self.phases + self.step_increment, 2 * np.pi)


    def modify_phase(self, mask):
        self.phases = T.fmod(self.phases + mask, 2 * np.pi)


    def reset(self):
        self.phases = T.randn(1, 6, self.N_links) * 0.1


    def forward(self, x):

        # Batch dimension
        M = x.shape[0]

        # z, qw, qx, qy, qz [b,5]
        obs = x[:, :5]

        # xd, yd, xz, xangd, yangd, zangd [b, 6]
        obsd = x[:, 5 + self.N_links * 6 - 2: 5 + self.N_links * 6 - 2 + 6]

        # qw, qx, qy, qz, xd, yd [b, 6]
        ext_obs = T.cat((obs[:, 1:5], obsd[:, 0:2]), 1).unsqueeze(2)
        ext_obs_rep = ext_obs.repeat((1, 1, self.N_links))

        # Joints angles
        jl = T.cat((T.zeros(M, 2), x[:, 5:5 + self.N_links * 6 - 2]), 1)
        jlrs = jl.view((M, 6, -1))

        # Joint angle velocities
        jdl = T.cat(
            (T.zeros(M, 2), x[:, 5 + self.N_links * 6 - 2 + 6:5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2]), 1)
        jdlrs = jdl.view((M, 6, -1))

        # Contacts
        jcl = x[:, 5 + self.N_links * 6 - 2 + 6 + self.N_links * 6 - 2:]
        jclrs = jcl.view((M, 2, -1))

        ocat = T.cat((jlrs, jdlrs, ext_obs_rep, jclrs), 1)  # Concatenate j and jd so that they are 2 parallel channels

        phase_fm = self.afun(self.conv_obs(ocat)) * 0.3
        phase_deltas = self.afun(self.conv_phase(phase_fm))

        self.modify_phase(phase_deltas)
        self.step_phase()

        # Phases directly translate into torques
        acts = T.sin(self.phases.view(M, self.act_dim + 2))

        return acts[:, 2:]


class CM_MLP(nn.Module):
    def __init__(self, obs_dim, act_dim, n_hid):
        super(CM_MLP, self).__init__()

        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.n_hid = n_hid

        self.fc1 = nn.Linear(self.obs_dim, self.n_hid)
        self.fc2 = nn.Linear(self.n_hid, self.n_hid)
        self.fc3 = nn.Linear(self.n_hid, self.act_dim)


    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.tanh(self.fc3(x))
        return x


class CM_RNN(nn.Module):
    def __init__(self, obs_dim, output_dim, n_hid):
        super(CM_RNN, self).__init__()

        self.n_hid = n_hid
        self.obs_dim = obs_dim
        self.output_dim = output_dim

        self.in1 = nn.Linear(self.obs_dim, self.n_hid)
        self.rnn = nn.GRUCell(self.n_hid, self.n_hid)
        self.out1 = nn.Linear(self.n_hid, self.n_hid)
        self.out2 = nn.Linear(self.n_hid, self.output_dim)


    def forward(self, x, h):
        x = T.tanh(self.in1(x))
        h_ = self.rnn(x, h)
        x = T.tanh(self.out1(h_))
        return self.out2(x), h_


    def average_grads(self, N):
        self.in1.weight.grad /= N
        self.in1.bias.grad /= N
        self.rnn.weight_hh.grad /= N
        self.rnn.weight_ih.grad /= N
        self.rnn.bias_hh.grad /= N
        self.rnn.bias_ih.grad /= N
        self.out1.weight.grad /= N
        self.out1.bias.grad /= N
        self.out2.weight.grad /= N
        self.out2.bias.grad /= N


    def reset(self, batchsize=1):
        return T.zeros(1, self.n_hid)


class CM_Policy(nn.Module):
    def __init__(self, obs_dim, act_dim, n_hid):
        super(CM_Policy, self).__init__()

        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.n_hid = n_hid

        # Set states
        self.reset()

        self.rnn = nn.GRUCell(obs_dim, n_hid)
        self.out = nn.Linear(n_hid, act_dim)


    def forward(self, x, h):
        h_ = self.rnn(x, h)
        return self.out(h_), h_

    def average_grads(self, N):
        self.rnn.weight_hh.grad /= N
        self.rnn.weight_ih.grad /= N
        self.rnn.bias_hh.grad /= N
        self.rnn.bias_ih.grad /= N
        self.out.weight.grad /= N
        self.out.bias.grad /= N


    def reset(self, batchsize=1):
        return T.zeros(batchsize, self.n_hid).float()


class GYM_Linear(nn.Module):
    def __init__(self, env):
        super(GYM_Linear, self).__init__()
        self.obs_dim = env.observation_space.shape[0]
        self.act_dim = env.action_space.shape[0]

        self.fc1 = nn.Linear(self.obs_dim, self.act_dim)


    def forward(self, x):
        return self.fc1(x)


class FB_RNN(nn.Module):
    def __init__(self, env):
        super(FB_RNN, self).__init__()
        self.obs_dim = env.obs_dim
        self.act_dim = env.act_dim
        self.hid_dim = 24


        self.rnn = nn.RNNCell(self.obs_dim, self.hid_dim)
        self.xp = nn.Linear(self.obs_dim, self.obs_dim)
        self.pa = nn.Linear(self.hid_dim, self.act_dim)
        self.ph = nn.Linear(self.hid_dim, self.hid_dim)
        self.ah = nn.Linear(self.act_dim, self.hid_dim)


    def init_hidden(self):
        return T.zeros((1, self.hid_dim))


    def forward(self, input):
        x, h = input

        # Input to rnn
        x = T.tanh(self.xp(x))

        # Pre-hidden state
        p = self.rnn(x, h)

        # Action output
        a = T.tanh(self.pa(p))

        # Next hidden state
        h_ = T.tanh(self.ph(p) + self.ah(a))

        return a, h_

    def wstats(self):
        return self.rnn.weight_ih.data.min(), self.rnn.weight_ih.data.max()
