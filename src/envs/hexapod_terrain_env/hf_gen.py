import numpy as np
import cv2
import os
import torch
import torch as T
import torch.nn as nn
import torch.nn.functional as F

class ConvGen(nn.Module):
    def __init__(self, noise_dim):
        super(ConvGen, self).__init__()
        self.noise_dim = noise_dim

        self.c1 = nn.ConvTranspose2d(self.noise_dim, 4, kernel_size=(3,5), stride=(1,2))
        self.c2 = nn.ConvTranspose2d(4, 3, kernel_size=(3,5), stride=(1,2))
        self.c3 = nn.ConvTranspose2d(3, 1, kernel_size=(3,5), stride=(1,2))


    def forward(self, z):
        z = z.view(-1,self.noise_dim,1,1)

        out = F.leaky_relu(self.c1(z))
        out = F.upsample(out, scale_factor=2)

        out = F.leaky_relu(self.c2(out))
        out = F.upsample(out, scale_factor=2)

        out = F.sigmoid(self.c3(out))
        out = F.upsample(out, size=(30, 120))

        return out.view(-1, 30, 120)

class Gen:
    def __init__(self):
        self.N = 120
        self.M = 30
        self.div = 5

        self.filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                "assets/hf_gen.png")

        self.noise_dim = 8
        self.convgen = ConvGen(self.noise_dim)

    def generate(self):
        mat = np.random.randint(0, 70, size=(self.M // self.div, self.N // self.div), dtype=np.uint8).repeat(self.div, axis=0).repeat(self.div,
                                                                                                             axis=1)
        mat[0, :] = 255
        mat[:, 0] = 255
        mat[-1, :] = 255
        mat[:, -1] = 255
        cv2.imwrite(self.filename, mat)


    def gen_conv(self):

        mat = self.convgen(T.randn(1, self.noise_dim)).detach().squeeze(0).numpy()

        mat *= 255

        mat[0, :] = 255
        mat[:, 0] = 255
        mat[-1, :] = 255
        mat[:, -1] = 255
        cv2.imwrite(self.filename, mat)

if __name__ == "__main__":
    gen = Gen()
    gen.gen_conv()