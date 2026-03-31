import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, dropout_rate=0.0):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.dropout = nn.Dropout2d(dropout_rate) if dropout_rate > 0 else nn.Identity()
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.dropout(out)
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        return F.relu(out)

class SimpleAttention(nn.Module):
    def __init__(self, channel):
        super(SimpleAttention, self).__init__()
        self.query = nn.Conv2d(channel, channel // 8, 1)
        self.key = nn.Conv2d(channel, channel // 8, 1)
        self.value = nn.Conv2d(channel, channel, 1)
        self.gamma = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        batch_size, C, width, height = x.size()
        proj_query = self.query(x).view(batch_size, -1, width * height).permute(0, 2, 1)
        proj_key = self.key(x).view(batch_size, -1, width * height)
        energy = torch.bmm(proj_query, proj_key)
        attention = F.softmax(energy, dim=-1)
        proj_value = self.value(x).view(batch_size, -1, width * height)
        out = torch.bmm(proj_value, attention.permute(0, 2, 1))
        out = out.view(batch_size, C, width, height)
        out = self.gamma * out + x
        return out

class SquareCRNN(nn.Module):
    def __init__(self, num_classes, hidden_size=256, dropout_rate=0.3):
        super(SquareCRNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        self.layer1 = ResidualBlock(64, 128, stride=1, dropout_rate=0.1)
        self.maxpool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        self.layer2 = ResidualBlock(128, 256, stride=1, dropout_rate=dropout_rate)
        self.maxpool3 = nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 1), padding=(0, 1))
        
        self.layer3 = ResidualBlock(256, 512, stride=1, dropout_rate=dropout_rate)
        self.maxpool4 = nn.MaxPool2d(kernel_size=(2, 2), stride=(2, 1), padding=(0, 1))
        
        self.layer4 = ResidualBlock(512, 512, stride=1, dropout_rate=dropout_rate)
        self.attention = SimpleAttention(512)
        
        self.adaptive_pool = nn.AdaptiveAvgPool2d((1, None))
        self.rnn = nn.LSTM(512, hidden_size, bidirectional=True, num_layers=2, dropout=0.4)
        self.fc = nn.Linear(hidden_size * 2, num_classes + 1)

    def forward(self, x):
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.maxpool1(x)
        x = self.layer1(x)
        x = self.maxpool2(x)
        x = self.layer2(x)
        x = self.maxpool3(x)
        x = self.layer3(x)
        x = self.maxpool4(x)
        x = self.layer4(x)
        x = self.attention(x)
        x = self.adaptive_pool(x)
        
        b, c, h, w = x.size()
        x = x.view(b, c * h, w)
        x = x.permute(2, 0, 1)
        
        x, _ = self.rnn(x)
        x = self.fc(x)
        return x