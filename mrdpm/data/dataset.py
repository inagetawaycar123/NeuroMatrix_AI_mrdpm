import torch.utils.data as data
from torchvision import transforms
from PIL import Image
import os
import torch
import numpy as np

from .util.mask import (bbox2mask, brush_stroke_mask, get_irregular_mask, random_bbox, random_cropping_bbox)

IMG_EXTENSIONS = [
    '.npy'
]


def is_image_file(filename):
    return any(filename.endswith(extension) for extension in IMG_EXTENSIONS)


def make_dataset(dir):
    if os.path.isfile(dir):
        images = [i for i in np.genfromtxt(dir, dtype=str, encoding='utf-8')]
    else:
        images = []
        assert os.path.isdir(dir), '%s is not a valid directory' % dir
        for root, _, fnames in sorted(os.walk(dir)):
            for fname in sorted(fnames):
                if is_image_file(fname):
                    path = os.path.join(root, fname)
                    images.append(path)

    return images


def pil_loader(path):
    return Image.open(path).convert('RGB')


def npy_loader(path):
    return np.load(path)


# class NumpyDataset_mask(data.Dataset):
#     def __init__(self, data_root, data_flist, data_len=-1, image_size=[256, 256], loader=npy_loader):
#         self.data_root = data_root
#         flist = make_dataset(data_flist)
#         if data_len > 0:
#             self.flist = flist[:int(data_len)]
#         else:
#             self.flist = flist
#         self.tfs_img = transforms.Compose([
#                 transforms.ToTensor(),
#         ])
#         self.tfs_mask = transforms.Compose([
#                 transforms.ToTensor(),
#         ])
#         self.loader = npy_loader
#         self.image_size = image_size
#
#     def __getitem__(self, index):
#         ret = {}
#         file_name = str(self.flist[index]) + '.npy'
#
#         img = self.tfs_img(self.loader('{}/{}/{}'.format(self.data_root, 'Tmax', file_name)))
#         cond_image = self.tfs_img(self.loader('{}/{}/{}'.format(self.data_root, 'mCTA', file_name)))
#         mask = self.tfs_mask(self.loader('{}/{}/{}'.format(self.data_root, 'mask', file_name)))
#         mask = mask + 0
#
#         img[img >1]=1
#         img[img <0]=0
#         cond_image[cond_image >1]=1
#         cond_image[cond_image <0]=0
#
#         cond_image = cond_image *np.concatenate([mask,mask,mask,mask], axis=0)
#         mask_img = img*(1. - mask) + mask
#         img = img * mask
#
#         ret['gt_image'] = img
#         ret['cond_image'] = cond_image
#         ret['mask_image'] = mask_img
#         ret['mask'] = mask
#         ret['path'] = file_name
#         return ret
#
#     def __len__(self):
#         return len(self.flist)

class NumpyDataset_mask(data.Dataset):
    def __init__(self, data_root, data_flist, data_len=-1, image_size=[256, 256], loader=pil_loader,
                 mcta_phase=1):  # 新增mcta_phase参数选择要使用的mCTA时相:动脉期为第2个通道（索引1）！！！！
        self.data_root = data_root
        flist = make_dataset(data_flist)
        self.mcta_phase = mcta_phase  # 存储选择的mCTA时相索引

        if data_len > 0:
            self.flist = flist[:int(data_len)]
        else:
            self.flist = flist

        self.tfs_img = transforms.Compose([
            transforms.ToTensor(),
        ])

        self.tfs_mask = transforms.Compose([
            transforms.ToTensor(),
        ])

        self.loader = npy_loader
        self.image_size = image_size

    def __getitem__(self, index):
        ret = {}
        file_name = str(self.flist[index]) + '.npy'

        # 加载原始数据
        img = self.tfs_img(self.loader('{}/{}/{}'.format(self.data_root, 'CBF', file_name)))
        cond_image = self.tfs_img(self.loader('{}/{}/{}'.format(self.data_root, 'NCCT_mCTA_only', file_name)))
        mask = self.tfs_mask(self.loader('{}/{}/{}'.format(self.data_root, 'mask', file_name)))
        mask = mask + 0  # 确保掩码是数值类型

        # 截断数值到[0,1]范围
        img[img > 1] = 1
        img[img < 0] = 0
        cond_image[cond_image > 1] = 1
        cond_image[cond_image < 0] = 0

        # 修改处：从4通道条件图像中选择动脉期+NCCT通道
        # 原形状：[4, H, W]，我们选择第mcta_phase通道（动脉期，为第2通道，索引为1）和NCCT（第1通道，索引为0）
        selected_cond = torch.stack([
            cond_image[self.mcta_phase],  # 选择指定时相的mCTA
            cond_image[0]  # NCCT是第1通道（索引0）；cond_image[0]
        ])

        # ====== 关键修改：添加全零的第三通道 ======
        # 创建与第一个通道相同形状的全零张量
        zero_channel = torch.zeros_like(selected_cond[0].unsqueeze(0))

        # 合并为3通道
        selected_cond = torch.cat([
            selected_cond,
            zero_channel
        ], dim=0)
        # ========================================

        # 应用掩码（现在只需要复制3次）
        cond_image = selected_cond * torch.cat([mask, mask, mask], dim=0)

        # 创建掩码图像（不变）
        mask_img = img * (1. - mask) + mask
        img = img * mask  # 保留目标图像的脑区

        ret['gt_image'] = img
        ret['cond_image'] = cond_image  # 现在是2通道
        ret['mask_image'] = mask_img
        ret['mask'] = mask
        ret['path'] = file_name
        return ret

    def __len__(self):
        return len(self.flist)


class NumpyDataset_mask_res(data.Dataset):  # 残差有负值
    def __init__(self, data_root, data_flist, data_len=-1, image_size=[256, 256], loader=pil_loader,
                 mcta_phase=1):  # 新增mcta_phase参数选择要使用的mCTA时相
        self.data_root = data_root
        flist = make_dataset(data_flist)
        self.mcta_phase = mcta_phase  # 存储选择的mCTA时相索引

        if data_len > 0:
            self.flist = flist[:int(data_len)]
        else:
            self.flist = flist

        self.tfs_img = transforms.Compose([
            transforms.ToTensor(),
        ])

        self.tfs_mask = transforms.Compose([
            transforms.ToTensor(),
        ])

        self.loader = npy_loader
        self.image_size = image_size

    def __getitem__(self, index):
        ret = {}
        file_name = str(self.flist[index]) + '.npy'
        # 加载原始数据
        img = self.tfs_img(self.loader('{}/{}/{}'.format(self.data_root, 'CBF', file_name)))
        cond_image = self.tfs_img(self.loader('{}/{}/{}'.format(self.data_root, 'NCCT_mCTA_only', file_name)))
        mask = self.tfs_mask(self.loader('{}/{}/{}'.format(self.data_root, 'mask', file_name)))
        mask = mask + 0  # 确保掩码是数值类型

        # 从4通道条件图像中选择指定通道
        # 原形状：[4, H, W]，选择第mcta_phase通道和NCCT通道（索引3）
        selected_cond = torch.stack([
            cond_image[self.mcta_phase],  # 选择指定时相的mCTA
            cond_image[0]  # NCCT是第1通道（索引0）
        ])

        # 添加全零的第三通道
        zero_channel = torch.zeros_like(selected_cond[0].unsqueeze(0))
        selected_cond = torch.cat([selected_cond, zero_channel], dim=0)

        # 应用掩码（现在只需要复制3次）
        cond_image = selected_cond * torch.cat([mask, mask, mask], dim=0)

        # 创建掩码图像
        mask_img = img * mask
        img = img * mask  # 保留目标图像的脑区

        ret['gt_image'] = img
        ret['cond_image'] = cond_image  # 现在是3通道
        ret['mask_image'] = mask_img
        ret['mask'] = mask
        ret['path'] = file_name
        return ret

    def __len__(self):
        return len(self.flist)