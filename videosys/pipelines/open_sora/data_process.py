# Adapted from OpenSora

# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
# --------------------------------------------------------
# References:
# OpenSora: https://github.com/hpcaitech/Open-Sora
# --------------------------------------------------------


import numbers
import os
import re

import numpy as np
import requests
import torch
import torchvision
import torchvision.transforms as transforms
from PIL import Image
from torchvision.datasets.folder import IMG_EXTENSIONS, pil_loader
from torchvision.io import write_video
from torchvision.utils import save_image

IMG_FPS = 120
VID_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv")

regex = re.compile(
    r"^(?:http|ftp)s?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

# H:W
ASPECT_RATIO_MAP = {
    "3:8": "0.38",
    "9:21": "0.43",
    "12:25": "0.48",
    "1:2": "0.50",
    "9:17": "0.53",
    "27:50": "0.54",
    "9:16": "0.56",
    "5:8": "0.62",
    "2:3": "0.67",
    "3:4": "0.75",
    "1:1": "1.00",
    "4:3": "1.33",
    "3:2": "1.50",
    "16:9": "1.78",
    "17:9": "1.89",
    "2:1": "2.00",
    "50:27": "2.08",
}


# computed from above code
# S = 8294400
ASPECT_RATIO_4K = {
    "0.38": (1764, 4704),
    "0.43": (1886, 4400),
    "0.48": (1996, 4158),
    "0.50": (2036, 4072),
    "0.53": (2096, 3960),
    "0.54": (2118, 3918),
    "0.62": (2276, 3642),
    "0.56": (2160, 3840),  # base
    "0.67": (2352, 3528),
    "0.75": (2494, 3326),
    "1.00": (2880, 2880),
    "1.33": (3326, 2494),
    "1.50": (3528, 2352),
    "1.78": (3840, 2160),
    "1.89": (3958, 2096),
    "2.00": (4072, 2036),
    "2.08": (4156, 1994),
}

# S = 3686400
ASPECT_RATIO_2K = {
    "0.38": (1176, 3136),
    "0.43": (1256, 2930),
    "0.48": (1330, 2770),
    "0.50": (1358, 2716),
    "0.53": (1398, 2640),
    "0.54": (1412, 2612),
    "0.56": (1440, 2560),  # base
    "0.62": (1518, 2428),
    "0.67": (1568, 2352),
    "0.75": (1662, 2216),
    "1.00": (1920, 1920),
    "1.33": (2218, 1664),
    "1.50": (2352, 1568),
    "1.78": (2560, 1440),
    "1.89": (2638, 1396),
    "2.00": (2716, 1358),
    "2.08": (2772, 1330),
}

# S = 2073600
ASPECT_RATIO_1080P = {
    "0.38": (882, 2352),
    "0.43": (942, 2198),
    "0.48": (998, 2080),
    "0.50": (1018, 2036),
    "0.53": (1048, 1980),
    "0.54": (1058, 1958),
    "0.56": (1080, 1920),  # base
    "0.62": (1138, 1820),
    "0.67": (1176, 1764),
    "0.75": (1248, 1664),
    "1.00": (1440, 1440),
    "1.33": (1662, 1246),
    "1.50": (1764, 1176),
    "1.78": (1920, 1080),
    "1.89": (1980, 1048),
    "2.00": (2036, 1018),
    "2.08": (2078, 998),
}

# S = 921600
ASPECT_RATIO_720P = {
    "0.38": (588, 1568),
    "0.43": (628, 1466),
    "0.48": (666, 1388),
    "0.50": (678, 1356),
    "0.53": (698, 1318),
    "0.54": (706, 1306),
    "0.56": (720, 1280),  # base
    "0.62": (758, 1212),
    "0.67": (784, 1176),
    "0.75": (832, 1110),
    "1.00": (960, 960),
    "1.33": (1108, 832),
    "1.50": (1176, 784),
    "1.78": (1280, 720),
    "1.89": (1320, 698),
    "2.00": (1358, 680),
    "2.08": (1386, 666),
}

# S = 409920
ASPECT_RATIO_480P = {
    "0.38": (392, 1046),
    "0.43": (420, 980),
    "0.48": (444, 925),
    "0.50": (452, 904),
    "0.53": (466, 880),
    "0.54": (470, 870),
    "0.56": (480, 854),  # base
    "0.62": (506, 810),
    "0.67": (522, 784),
    "0.75": (554, 738),
    "1.00": (640, 640),
    "1.33": (740, 555),
    "1.50": (784, 522),
    "1.78": (854, 480),
    "1.89": (880, 466),
    "2.00": (906, 454),
    "2.08": (924, 444),
}

# S = 230400
ASPECT_RATIO_360P = {
    "0.38": (294, 784),
    "0.43": (314, 732),
    "0.48": (332, 692),
    "0.50": (340, 680),
    "0.53": (350, 662),
    "0.54": (352, 652),
    "0.56": (360, 640),  # base
    "0.62": (380, 608),
    "0.67": (392, 588),
    "0.75": (416, 554),
    "1.00": (480, 480),
    "1.33": (554, 416),
    "1.50": (588, 392),
    "1.78": (640, 360),
    "1.89": (660, 350),
    "2.00": (678, 340),
    "2.08": (692, 332),
}

# S = 102240
ASPECT_RATIO_240P = {
    "0.38": (196, 522),
    "0.43": (210, 490),
    "0.48": (222, 462),
    "0.50": (226, 452),
    "0.53": (232, 438),
    "0.54": (236, 436),
    "0.56": (240, 426),  # base
    "0.62": (252, 404),
    "0.67": (262, 393),
    "0.75": (276, 368),
    "1.00": (320, 320),
    "1.33": (370, 278),
    "1.50": (392, 262),
    "1.78": (426, 240),
    "1.89": (440, 232),
    "2.00": (452, 226),
    "2.08": (462, 222),
}

# S = 36864
ASPECT_RATIO_144P = {
    "0.38": (117, 312),
    "0.43": (125, 291),
    "0.48": (133, 277),
    "0.50": (135, 270),
    "0.53": (139, 262),
    "0.54": (141, 260),
    "0.56": (144, 256),  # base
    "0.62": (151, 241),
    "0.67": (156, 234),
    "0.75": (166, 221),
    "1.00": (192, 192),
    "1.33": (221, 165),
    "1.50": (235, 156),
    "1.78": (256, 144),
    "1.89": (263, 139),
    "2.00": (271, 135),
    "2.08": (277, 132),
}

# from PixArt
# S = 8294400
ASPECT_RATIO_2880 = {
    "0.25": (1408, 5760),
    "0.26": (1408, 5568),
    "0.27": (1408, 5376),
    "0.28": (1408, 5184),
    "0.32": (1600, 4992),
    "0.33": (1600, 4800),
    "0.34": (1600, 4672),
    "0.4": (1792, 4480),
    "0.42": (1792, 4288),
    "0.47": (1920, 4096),
    "0.49": (1920, 3904),
    "0.51": (1920, 3776),
    "0.55": (2112, 3840),
    "0.59": (2112, 3584),
    "0.68": (2304, 3392),
    "0.72": (2304, 3200),
    "0.78": (2496, 3200),
    "0.83": (2496, 3008),
    "0.89": (2688, 3008),
    "0.93": (2688, 2880),
    "1.0": (2880, 2880),
    "1.07": (2880, 2688),
    "1.12": (3008, 2688),
    "1.21": (3008, 2496),
    "1.28": (3200, 2496),
    "1.39": (3200, 2304),
    "1.47": (3392, 2304),
    "1.7": (3584, 2112),
    "1.82": (3840, 2112),
    "2.03": (3904, 1920),
    "2.13": (4096, 1920),
    "2.39": (4288, 1792),
    "2.5": (4480, 1792),
    "2.92": (4672, 1600),
    "3.0": (4800, 1600),
    "3.12": (4992, 1600),
    "3.68": (5184, 1408),
    "3.82": (5376, 1408),
    "3.95": (5568, 1408),
    "4.0": (5760, 1408),
}

# S = 4194304
ASPECT_RATIO_2048 = {
    "0.25": (1024, 4096),
    "0.26": (1024, 3968),
    "0.27": (1024, 3840),
    "0.28": (1024, 3712),
    "0.32": (1152, 3584),
    "0.33": (1152, 3456),
    "0.35": (1152, 3328),
    "0.4": (1280, 3200),
    "0.42": (1280, 3072),
    "0.48": (1408, 2944),
    "0.5": (1408, 2816),
    "0.52": (1408, 2688),
    "0.57": (1536, 2688),
    "0.6": (1536, 2560),
    "0.68": (1664, 2432),
    "0.72": (1664, 2304),
    "0.78": (1792, 2304),
    "0.82": (1792, 2176),
    "0.88": (1920, 2176),
    "0.94": (1920, 2048),
    "1.0": (2048, 2048),
    "1.07": (2048, 1920),
    "1.13": (2176, 1920),
    "1.21": (2176, 1792),
    "1.29": (2304, 1792),
    "1.38": (2304, 1664),
    "1.46": (2432, 1664),
    "1.67": (2560, 1536),
    "1.75": (2688, 1536),
    "2.0": (2816, 1408),
    "2.09": (2944, 1408),
    "2.4": (3072, 1280),
    "2.5": (3200, 1280),
    "2.89": (3328, 1152),
    "3.0": (3456, 1152),
    "3.11": (3584, 1152),
    "3.62": (3712, 1024),
    "3.75": (3840, 1024),
    "3.88": (3968, 1024),
    "4.0": (4096, 1024),
}

# S = 1048576
ASPECT_RATIO_1024 = {
    "0.25": (512, 2048),
    "0.26": (512, 1984),
    "0.27": (512, 1920),
    "0.28": (512, 1856),
    "0.32": (576, 1792),
    "0.33": (576, 1728),
    "0.35": (576, 1664),
    "0.4": (640, 1600),
    "0.42": (640, 1536),
    "0.48": (704, 1472),
    "0.5": (704, 1408),
    "0.52": (704, 1344),
    "0.57": (768, 1344),
    "0.6": (768, 1280),
    "0.68": (832, 1216),
    "0.72": (832, 1152),
    "0.78": (896, 1152),
    "0.82": (896, 1088),
    "0.88": (960, 1088),
    "0.94": (960, 1024),
    "1.0": (1024, 1024),
    "1.07": (1024, 960),
    "1.13": (1088, 960),
    "1.21": (1088, 896),
    "1.29": (1152, 896),
    "1.38": (1152, 832),
    "1.46": (1216, 832),
    "1.67": (1280, 768),
    "1.75": (1344, 768),
    "2.0": (1408, 704),
    "2.09": (1472, 704),
    "2.4": (1536, 640),
    "2.5": (1600, 640),
    "2.89": (1664, 576),
    "3.0": (1728, 576),
    "3.11": (1792, 576),
    "3.62": (1856, 512),
    "3.75": (1920, 512),
    "3.88": (1984, 512),
    "4.0": (2048, 512),
}

# S = 262144
ASPECT_RATIO_512 = {
    "0.25": (256, 1024),
    "0.26": (256, 992),
    "0.27": (256, 960),
    "0.28": (256, 928),
    "0.32": (288, 896),
    "0.33": (288, 864),
    "0.35": (288, 832),
    "0.4": (320, 800),
    "0.42": (320, 768),
    "0.48": (352, 736),
    "0.5": (352, 704),
    "0.52": (352, 672),
    "0.57": (384, 672),
    "0.6": (384, 640),
    "0.68": (416, 608),
    "0.72": (416, 576),
    "0.78": (448, 576),
    "0.82": (448, 544),
    "0.88": (480, 544),
    "0.94": (480, 512),
    "1.0": (512, 512),
    "1.07": (512, 480),
    "1.13": (544, 480),
    "1.21": (544, 448),
    "1.29": (576, 448),
    "1.38": (576, 416),
    "1.46": (608, 416),
    "1.67": (640, 384),
    "1.75": (672, 384),
    "2.0": (704, 352),
    "2.09": (736, 352),
    "2.4": (768, 320),
    "2.5": (800, 320),
    "2.89": (832, 288),
    "3.0": (864, 288),
    "3.11": (896, 288),
    "3.62": (928, 256),
    "3.75": (960, 256),
    "3.88": (992, 256),
    "4.0": (1024, 256),
}

# S = 65536
ASPECT_RATIO_256 = {
    "0.25": (128, 512),
    "0.26": (128, 496),
    "0.27": (128, 480),
    "0.28": (128, 464),
    "0.32": (144, 448),
    "0.33": (144, 432),
    "0.35": (144, 416),
    "0.4": (160, 400),
    "0.42": (160, 384),
    "0.48": (176, 368),
    "0.5": (176, 352),
    "0.52": (176, 336),
    "0.57": (192, 336),
    "0.6": (192, 320),
    "0.68": (208, 304),
    "0.72": (208, 288),
    "0.78": (224, 288),
    "0.82": (224, 272),
    "0.88": (240, 272),
    "0.94": (240, 256),
    "1.0": (256, 256),
    "1.07": (256, 240),
    "1.13": (272, 240),
    "1.21": (272, 224),
    "1.29": (288, 224),
    "1.38": (288, 208),
    "1.46": (304, 208),
    "1.67": (320, 192),
    "1.75": (336, 192),
    "2.0": (352, 176),
    "2.09": (368, 176),
    "2.4": (384, 160),
    "2.5": (400, 160),
    "2.89": (416, 144),
    "3.0": (432, 144),
    "3.11": (448, 144),
    "3.62": (464, 128),
    "3.75": (480, 128),
    "3.88": (496, 128),
    "4.0": (512, 128),
}


def get_closest_ratio(height: float, width: float, ratios: dict):
    aspect_ratio = height / width
    closest_ratio = min(ratios.keys(), key=lambda ratio: abs(float(ratio) - aspect_ratio))
    return closest_ratio


ASPECT_RATIOS = {
    "144p": (36864, ASPECT_RATIO_144P),
    "256": (65536, ASPECT_RATIO_256),
    "240p": (102240, ASPECT_RATIO_240P),
    "360p": (230400, ASPECT_RATIO_360P),
    "512": (262144, ASPECT_RATIO_512),
    "480p": (409920, ASPECT_RATIO_480P),
    "720p": (921600, ASPECT_RATIO_720P),
    "1024": (1048576, ASPECT_RATIO_1024),
    "1080p": (2073600, ASPECT_RATIO_1080P),
    "2k": (3686400, ASPECT_RATIO_2K),
    "2048": (4194304, ASPECT_RATIO_2048),
    "2880": (8294400, ASPECT_RATIO_2880),
    "4k": (8294400, ASPECT_RATIO_4K),
}


def get_image_size(resolution, ar_ratio):
    ar_key = ASPECT_RATIO_MAP[ar_ratio]
    rs_dict = ASPECT_RATIOS[resolution][1]
    assert ar_key in rs_dict, f"Aspect ratio {ar_ratio} not found for resolution {resolution}"
    return rs_dict[ar_key]


NUM_FRAMES_MAP = {
    "1x": 51,
    "2x": 102,
    "4x": 204,
    "8x": 408,
    "16x": 816,
    "2s": 51,
    "4s": 102,
    "8s": 204,
    "16s": 408,
    "32s": 816,
}


def get_num_frames(num_frames):
    if num_frames in NUM_FRAMES_MAP:
        return NUM_FRAMES_MAP[num_frames]
    else:
        return int(num_frames)


def save_sample(x, save_path=None, fps=8, normalize=True, value_range=(-1, 1), force_video=False, verbose=True):
    """
    Args:
        x (Tensor): shape [C, T, H, W]
    """
    assert x.ndim == 4

    if not force_video and x.shape[1] == 1:  # T = 1: save as image
        save_path += ".png"
        x = x.squeeze(1)
        save_image([x], save_path, normalize=normalize, value_range=value_range)
    else:
        save_path += ".mp4"
        if normalize:
            low, high = value_range
            x.clamp_(min=low, max=high)
            x.sub_(low).div_(max(high - low, 1e-5))

        x = x.mul(255).add_(0.5).clamp_(0, 255).permute(1, 2, 3, 0).to("cpu", torch.uint8)
        write_video(save_path, x, fps=fps, video_codec="h264")
    if verbose:
        print(f"Saved to {save_path}")
    return save_path


def is_url(url):
    return re.match(regex, url) is not None


def download_url(input_path):
    output_dir = "cache"
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(input_path)
    output_path = os.path.join(output_dir, base_name)
    img_data = requests.get(input_path).content
    with open(output_path, "wb") as handler:
        handler.write(img_data)
    print(f"URL {input_path} downloaded to {output_path}")
    return output_path


def get_transforms_video(name="center", image_size=(256, 256)):
    if name is None:
        return None
    elif name == "center":
        assert image_size[0] == image_size[1], "image_size must be square for center crop"
        transform_video = transforms.Compose(
            [
                ToTensorVideo(),  # TCHW
                # video_transforms.RandomHorizontalFlipVideo(),
                UCFCenterCropVideo(image_size[0]),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5], inplace=True),
            ]
        )
    elif name == "resize_crop":
        transform_video = transforms.Compose(
            [
                ToTensorVideo(),  # TCHW
                ResizeCrop(image_size),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5], inplace=True),
            ]
        )
    else:
        raise NotImplementedError(f"Transform {name} not implemented")
    return transform_video


def crop(clip, i, j, h, w):
    """
    Args:
        clip (torch.tensor): Video clip to be cropped. Size is (T, C, H, W)
    """
    if len(clip.size()) != 4:
        raise ValueError("clip should be a 4D tensor")
    return clip[..., i : i + h, j : j + w]


def center_crop(clip, crop_size):
    if not _is_tensor_video_clip(clip):
        raise ValueError("clip should be a 4D torch.tensor")
    h, w = clip.size(-2), clip.size(-1)
    th, tw = crop_size
    if h < th or w < tw:
        raise ValueError("height and width must be no smaller than crop_size")

    i = int(round((h - th) / 2.0))
    j = int(round((w - tw) / 2.0))
    return crop(clip, i, j, th, tw)


def resize_scale(clip, target_size, interpolation_mode):
    if len(target_size) != 2:
        raise ValueError(f"target size should be tuple (height, width), instead got {target_size}")
    H, W = clip.size(-2), clip.size(-1)
    scale_ = target_size[0] / min(H, W)
    return torch.nn.functional.interpolate(clip, scale_factor=scale_, mode=interpolation_mode, align_corners=False)


class UCFCenterCropVideo:
    """
    First scale to the specified size in equal proportion to the short edge,
    then center cropping
    """

    def __init__(
        self,
        size,
        interpolation_mode="bilinear",
    ):
        if isinstance(size, tuple):
            if len(size) != 2:
                raise ValueError(f"size should be tuple (height, width), instead got {size}")
            self.size = size
        else:
            self.size = (size, size)

        self.interpolation_mode = interpolation_mode

    def __call__(self, clip):
        """
        Args:
            clip (torch.tensor): Video clip to be cropped. Size is (T, C, H, W)
        Returns:
            torch.tensor: scale resized / center cropped video clip.
                size is (T, C, crop_size, crop_size)
        """
        clip_resize = resize_scale(clip=clip, target_size=self.size, interpolation_mode=self.interpolation_mode)
        clip_center_crop = center_crop(clip_resize, self.size)
        return clip_center_crop

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size}, interpolation_mode={self.interpolation_mode}"


def _is_tensor_video_clip(clip):
    if not torch.is_tensor(clip):
        raise TypeError("clip should be Tensor. Got %s" % type(clip))

    if not clip.ndimension() == 4:
        raise ValueError("clip should be 4D. Got %dD" % clip.dim())

    return True


def to_tensor(clip):
    """
    Convert tensor data type from uint8 to float, divide value by 255.0 and
    permute the dimensions of clip tensor
    Args:
        clip (torch.tensor, dtype=torch.uint8): Size is (T, C, H, W)
    Return:
        clip (torch.tensor, dtype=torch.float): Size is (T, C, H, W)
    """
    _is_tensor_video_clip(clip)
    if not clip.dtype == torch.uint8:
        raise TypeError("clip tensor should have data type uint8. Got %s" % str(clip.dtype))
    # return clip.float().permute(3, 0, 1, 2) / 255.0
    return clip.float() / 255.0


class ToTensorVideo:
    """
    Convert tensor data type from uint8 to float, divide value by 255.0 and
    permute the dimensions of clip tensor
    """

    def __init__(self):
        pass

    def __call__(self, clip):
        """
        Args:
            clip (torch.tensor, dtype=torch.uint8): Size is (T, C, H, W)
        Return:
            clip (torch.tensor, dtype=torch.float): Size is (T, C, H, W)
        """
        return to_tensor(clip)

    def __repr__(self) -> str:
        return self.__class__.__name__


class ResizeCrop:
    def __init__(self, size):
        if isinstance(size, numbers.Number):
            self.size = (int(size), int(size))
        else:
            self.size = size

    def __call__(self, clip):
        clip = resize_crop_to_fill(clip, self.size)
        return clip

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(size={self.size})"


def get_transforms_image(name="center", image_size=(256, 256)):
    if name is None:
        return None
    elif name == "center":
        assert image_size[0] == image_size[1], "Image size must be square for center crop"
        transform = transforms.Compose(
            [
                transforms.Lambda(lambda pil_image: center_crop_arr(pil_image, image_size[0])),
                # transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5], inplace=True),
            ]
        )
    elif name == "resize_crop":
        transform = transforms.Compose(
            [
                transforms.Lambda(lambda pil_image: resize_crop_to_fill(pil_image, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5], inplace=True),
            ]
        )
    else:
        raise NotImplementedError(f"Transform {name} not implemented")
    return transform


def center_crop_arr(pil_image, image_size):
    """
    Center cropping implementation from ADM.
    https://github.com/openai/guided-diffusion/blob/8fb3ad9197f16bbc40620447b2742e13458d2831/guided_diffusion/image_datasets.py#L126
    """
    while min(*pil_image.size) >= 2 * image_size:
        pil_image = pil_image.resize(tuple(x // 2 for x in pil_image.size), resample=Image.BOX)

    scale = image_size / min(*pil_image.size)
    pil_image = pil_image.resize(tuple(round(x * scale) for x in pil_image.size), resample=Image.BICUBIC)

    arr = np.array(pil_image)
    crop_y = (arr.shape[0] - image_size) // 2
    crop_x = (arr.shape[1] - image_size) // 2
    return Image.fromarray(arr[crop_y : crop_y + image_size, crop_x : crop_x + image_size])


def resize_crop_to_fill(pil_image, image_size):
    w, h = pil_image.size  # PIL is (W, H)
    th, tw = image_size
    rh, rw = th / h, tw / w
    if rh > rw:
        sh, sw = th, round(w * rh)
        image = pil_image.resize((sw, sh), Image.BICUBIC)
        i = 0
        j = int(round((sw - tw) / 2.0))
    else:
        sh, sw = round(h * rw), tw
        image = pil_image.resize((sw, sh), Image.BICUBIC)
        i = int(round((sh - th) / 2.0))
        j = 0
    arr = np.array(image)
    assert i + th <= arr.shape[0] and j + tw <= arr.shape[1]
    return Image.fromarray(arr[i : i + th, j : j + tw])


def read_video_from_path(path, transform=None, transform_name="center", image_size=(256, 256)):
    vframes, aframes, info = torchvision.io.read_video(filename=path, pts_unit="sec", output_format="TCHW")
    if transform is None:
        transform = get_transforms_video(image_size=image_size, name=transform_name)
    video = transform(vframes)  # T C H W
    video = video.permute(1, 0, 2, 3)
    return video


def read_from_path(path, image_size, transform_name="center"):
    if is_url(path):
        path = download_url(path)
    ext = os.path.splitext(path)[-1].lower()
    if ext.lower() in VID_EXTENSIONS:
        return read_video_from_path(path, image_size=image_size, transform_name=transform_name)
    else:
        assert ext.lower() in IMG_EXTENSIONS, f"Unsupported file format: {ext}"
        return read_image_from_path(path, image_size=image_size, transform_name=transform_name)


def read_image_from_path(path, transform=None, transform_name="center", num_frames=1, image_size=(256, 256)):
    image = pil_loader(path)
    if transform is None:
        transform = get_transforms_image(image_size=image_size, name=transform_name)
    image = transform(image)
    video = image.unsqueeze(0).repeat(num_frames, 1, 1, 1)
    video = video.permute(1, 0, 2, 3)
    return video


def prepare_multi_resolution_info(info_type, batch_size, image_size, num_frames, fps, device, dtype):
    if info_type is None:
        return dict()
    elif info_type == "PixArtMS":
        hw = torch.tensor([image_size], device=device, dtype=dtype).repeat(batch_size, 1)
        ar = torch.tensor([[image_size[0] / image_size[1]]], device=device, dtype=dtype).repeat(batch_size, 1)
        return dict(ar=ar, hw=hw)
    elif info_type in ["STDiT2", "OpenSora"]:
        fps = fps if num_frames > 1 else IMG_FPS
        fps = torch.tensor([fps], device=device, dtype=dtype).repeat(batch_size)
        height = torch.tensor([image_size[0]], device=device, dtype=dtype).repeat(batch_size)
        width = torch.tensor([image_size[1]], device=device, dtype=dtype).repeat(batch_size)
        num_frames = torch.tensor([num_frames], device=device, dtype=dtype).repeat(batch_size)
        ar = torch.tensor([image_size[0] / image_size[1]], device=device, dtype=dtype).repeat(batch_size)
        return dict(height=height, width=width, num_frames=num_frames, ar=ar, fps=fps)
    else:
        raise NotImplementedError
