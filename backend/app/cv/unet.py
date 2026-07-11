"""Compact 2D U-Net for multi-class segmentation.

Four downsampling stages, so the input side must be divisible by 16 (e.g. 256).
Channel width is set by base_channels to keep the model small enough for a CPU
smoke test while scaling up for a real run.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class DoubleConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class UNet(nn.Module):
    def __init__(
        self, in_channels: int = 1, num_classes: int = 5, base_channels: int = 32
    ) -> None:
        super().__init__()
        c = base_channels
        self.inc = DoubleConv(in_channels, c)
        self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c, c * 2))
        self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c * 2, c * 4))
        self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c * 4, c * 8))
        self.bottleneck = nn.Sequential(nn.MaxPool2d(2), DoubleConv(c * 8, c * 16))

        self.up3 = nn.ConvTranspose2d(c * 16, c * 8, kernel_size=2, stride=2)
        self.conv3 = DoubleConv(c * 16, c * 8)
        self.up2 = nn.ConvTranspose2d(c * 8, c * 4, kernel_size=2, stride=2)
        self.conv2 = DoubleConv(c * 8, c * 4)
        self.up1 = nn.ConvTranspose2d(c * 4, c * 2, kernel_size=2, stride=2)
        self.conv1 = DoubleConv(c * 4, c * 2)
        self.up0 = nn.ConvTranspose2d(c * 2, c, kernel_size=2, stride=2)
        self.conv0 = DoubleConv(c * 2, c)
        self.outc = nn.Conv2d(c, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x0 = self.inc(x)
        x1 = self.down1(x0)
        x2 = self.down2(x1)
        x3 = self.down3(x2)
        xb = self.bottleneck(x3)

        y = self.conv3(torch.cat([self.up3(xb), x3], dim=1))
        y = self.conv2(torch.cat([self.up2(y), x2], dim=1))
        y = self.conv1(torch.cat([self.up1(y), x1], dim=1))
        y = self.conv0(torch.cat([self.up0(y), x0], dim=1))
        return self.outc(y)
