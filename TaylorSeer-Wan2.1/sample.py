# Copyright 2024-2025 The Alibaba Wan Team Authors. All rights reserved.
import argparse
from datetime import datetime
import json
import logging
import os
import random
import re
import sys
import warnings

warnings.filterwarnings('ignore')

import torch, random
import torch.distributed as dist
from PIL import Image

import wan
from wan.configs import WAN_CONFIGS, SIZE_CONFIGS, MAX_AREA_CONFIGS, SUPPORTED_SIZES
from wan.utils.prompt_extend import DashScopePromptExpander, QwenPromptExpander
from wan.utils.utils import cache_video, cache_image, str2bool
from wan.taylorseer.generates import wan_t2v_generate, wan_i2v_generate
from wan.taylorseer.forwards import wan_forward, xfusers_wan_forward, wan_attention_forward
import types

# 只保留文生图和文生视频示例（删除图生视频 i2v 示例）
EXAMPLE_PROMPT = {
    "t2v-1.3B": {
        "prompt": "Two anthropomorphic cats in comfy boxing gear and bright gloves fight intensely on a spotlighted stage.",
    },
    "t2v-14B": {
        "prompt": "Two anthropomorphic cats in comfy boxing gear and bright gloves fight intensely on a spotlighted stage.",
    },
    "t2i-14B": {
        "prompt": "一个朴素端庄的美人",
    },
}

def sanitize_filename(prompt):
    """
    将 prompt 中的特殊字符去除，并将空格替换为下划线，生成安全的文件名。
    """
    sanitized = re.sub(r'[^\w\- ]', '', prompt)
    sanitized = sanitized.replace(" ", "_")
    return sanitized

def load_prompts_from_file(file_path):
    """
    根据文件后缀（txt/json）加载 prompt。
    txt 文件中每一行作为一个 prompt；json 文件要求为列表格式，或者为 {"prompts": [...]}
    """
    ext = os.path.splitext(file_path)[1].lower()
    prompts = []
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    prompts.append(line)
    elif ext == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                prompts = data
            elif isinstance(data, dict):
                prompts = data.get("prompts", [])
            else:
                raise ValueError("Unsupported json format for prompts.")
    else:
        raise ValueError("Unsupported file extension for prompt_file. Only .txt and .json are supported.")
    return prompts

def _validate_args(args):
    # 基本检查
    assert args.ckpt_dir is not None, "Please specify the checkpoint directory."
    # 仅支持文生图和文生视频任务
    assert args.task in EXAMPLE_PROMPT, f"Unsupport task: {args.task}"

    # 默认采样步数：图像生成为40，视频生成为50
    if args.sample_steps is None:
        args.sample_steps = 40 if "t2i" in args.task else 50

    if args.sample_shift is None:
        args.sample_shift = 5.0
        if "t2i" not in args.task and args.size in ["832*480", "480*832"]:
            args.sample_shift = 3.0

    # 默认帧数：文生图任务 frame_num=1，其他任务默认81帧
    if args.frame_num is None:
        args.frame_num = 1 if "t2i" in args.task else 81

    # 文生图任务 frame_num 必须为1
    if "t2i" in args.task:
        assert args.frame_num == 1, f"Unsupport frame_num {args.frame_num} for task {args.task}"

    args.base_seed = args.base_seed if args.base_seed >= 0 else random.randint(0, sys.maxsize)
    # 尺寸检查
    assert args.size in SUPPORTED_SIZES[args.task], f"Unsupport size {args.size} for task {args.task}, supported sizes are: {', '.join(SUPPORTED_SIZES[args.task])}"

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Generate an image or video from a text prompt using Wan (only text-to-image and text-to-video are supported)."
    )
    parser.add_argument(
        "--task",
        type=str,
        default="t2v-14B",
        choices=list(EXAMPLE_PROMPT.keys()),
        help="The task to run (e.g., t2v-14B for text-to-video, t2i-14B for text-to-image).")
    parser.add_argument(
        "--size",
        type=str,
        default="1280*720",
        choices=list(SIZE_CONFIGS.keys()),
        help="The area (width*height) of the generated output.")
    parser.add_argument(
        "--frame_num",
        type=int,
        default=None,
        help="How many frames to sample. Should be 1 for text-to-image and 4n+1 for text-to-video.")
    parser.add_argument(
        "--ckpt_dir",
        type=str,
        default=None,
        help="The path to the checkpoint directory.")
    parser.add_argument(
        "--offload_model",
        type=str2bool,
        default=None,
        help="Whether to offload the model to CPU after each forward pass (reduces GPU memory usage).")
    parser.add_argument(
        "--ulysses_size",
        type=int,
        default=1,
        help="The size of the ulysses parallelism in DiT.")
    parser.add_argument(
        "--ring_size",
        type=int,
        default=1,
        help="The size of the ring attention parallelism in DiT.")
    parser.add_argument(
        "--t5_fsdp",
        action="store_true",
        default=False,
        help="Whether to use FSDP for T5.")
    parser.add_argument(
        "--t5_cpu",
        action="store_true",
        default=False,
        help="Whether to place T5 model on CPU.")
    parser.add_argument(
        "--dit_fsdp",
        action="store_true",
        default=False,
        help="Whether to use FSDP for DiT.")
    parser.add_argument(
        "--save_file",
        type=str,
        default=None,
        help="The file to save the generated image (for t2i) if prompt_file is not used.")
    # 针对单个 prompt 的情况
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="The prompt to generate the image or video from (only used if --prompt_file is not provided).")
    parser.add_argument(
        "--use_prompt_extend",
        action="store_true",
        default=False,
        help="Whether to use prompt extend.")
    parser.add_argument(
        "--prompt_extend_method",
        type=str,
        default="local_qwen",
        choices=["dashscope", "local_qwen"],
        help="The prompt extend method to use.")
    parser.add_argument(
        "--prompt_extend_model",
        type=str,
        default=None,
        help="The prompt extend model to use.")
    parser.add_argument(
        "--prompt_extend_target_lang",
        type=str,
        default="zh",
        choices=["zh", "en"],
        help="The target language for prompt extension.")
    parser.add_argument(
        "--base_seed",
        type=int,
        default=-1,
        help="The seed to use for generation.")
    # 针对文生视频任务，支持从文件中批量加载 prompt
    parser.add_argument(
        "--prompt_file",
        type=str,
        default=None,
        help="Path to a txt/json file containing prompts (one per line for txt, or a list for json) for text-to-video generation.")
    parser.add_argument(
        "--save_folder",
        type=str,
        default=None,
        help="Folder to save generated videos (only used when --prompt_file is provided).")
    parser.add_argument(
        "--sample_solver",
        type=str,
        default='unipc',
        choices=['unipc', 'dpm++'],
        help="The solver used to sample.")
    parser.add_argument(
        "--sample_steps", type=int, default=None, help="The sampling steps.")
    parser.add_argument(
        "--sample_shift",
        type=float,
        default=None,
        help="Sampling shift factor for flow matching schedulers.")
    parser.add_argument(
        "--sample_guide_scale",
        type=float,
        default=5.0,
        help="Classifier free guidance scale.")

    args = parser.parse_args()
    _validate_args(args)
    return args

def _init_logging(rank):
    # 日志设置
    if rank == 0:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s: %(message)s",
            handlers=[logging.StreamHandler(stream=sys.stdout)])
    else:
        logging.basicConfig(level=logging.ERROR)

def generate(args):
    rank = int(os.getenv("RANK", 0))
    world_size = int(os.getenv("WORLD_SIZE", 1))
    local_rank = int(os.getenv("LOCAL_RANK", 0))
    device = local_rank
    _init_logging(rank)

    if args.offload_model is None:
        args.offload_model = False if world_size > 1 else True
        logging.info(f"offload_model is not specified, set to {args.offload_model}.")
    if world_size > 1:
        torch.cuda.set_device(local_rank)
        dist.init_process_group(
            backend="nccl",
            init_method="env://",
            rank=rank,
            world_size=world_size)
    else:
        assert not (args.t5_fsdp or args.dit_fsdp), "t5_fsdp and dit_fsdp are not supported in non-distributed environments."
        assert not (args.ulysses_size > 1 or args.ring_size > 1), "Context parallelism is not supported in non-distributed environments."

    if args.ulysses_size > 1 or args.ring_size > 1:
        assert args.ulysses_size * args.ring_size == world_size, "The product of ulysses_size and ring_size must equal world size."
        from xfuser.core.distributed import (initialize_model_parallel, init_distributed_environment)
        init_distributed_environment(rank=dist.get_rank(), world_size=dist.get_world_size())
        initialize_model_parallel(sequence_parallel_degree=dist.get_world_size(),
                                  ring_degree=args.ring_size,
                                  ulysses_degree=args.ulysses_size)

    if args.use_prompt_extend:
        if args.prompt_extend_method == "dashscope":
            prompt_expander = DashScopePromptExpander(model_name=args.prompt_extend_model, is_vl=False)
        elif args.prompt_extend_method == "local_qwen":
            prompt_expander = QwenPromptExpander(model_name=args.prompt_extend_model, is_vl=False, device=rank)
        else:
            raise NotImplementedError(f"Unsupport prompt_extend_method: {args.prompt_extend_method}")

    cfg = WAN_CONFIGS[args.task]
    if args.ulysses_size > 1:
        assert cfg.num_heads % args.ulysses_size == 0, "`num_heads` must be divisible by `ulysses_size`."

    logging.info(f"Generation job args: {args}")
    logging.info(f"Generation model config: {cfg}")

    if dist.is_initialized():
        base_seed = [args.base_seed] if rank == 0 else [None]
        dist.broadcast_object_list(base_seed, src=0)
        args.base_seed = base_seed[0]

    # 针对文生视频任务
    if args.task.startswith("t2v"):
        # 如果指定了 prompt_file，则加载多个 prompt；否则使用单个 prompt（或默认示例）
        if args.prompt_file is not None:
            prompt_list = [None]
            if rank == 0:
                prompt_list[0] = load_prompts_from_file(args.prompt_file)
                logging.info(f"Loaded {len(prompt_list[0])} prompts from {args.prompt_file}.")
            if dist.is_initialized():
                dist.broadcast_object_list(prompt_list, src=0)
            prompts = prompt_list[0]
        else:
            if args.prompt is None:
                args.prompt = EXAMPLE_PROMPT[args.task]["prompt"]
            prompts = [args.prompt]

        logging.info("Creating WanT2V pipeline.")
        wan_t2v = wan.WanT2V(
            config=cfg,
            checkpoint_dir=args.ckpt_dir,
            device_id=device,
            rank=rank,
            t5_fsdp=args.t5_fsdp,
            dit_fsdp=args.dit_fsdp,
            use_usp=(args.ulysses_size > 1 or args.ring_size > 1),
            t5_cpu=args.t5_cpu,
        )
        # TaylorSeer
        wan_t2v.generate = types.MethodType(wan_t2v_generate, wan_t2v)

        # 对于每个 prompt，生成对应视频并保存
        for prompt in prompts:
            args.prompt = prompt
            logging.info(f"Input prompt: {args.prompt}")
            if args.use_prompt_extend:
                logging.info("Extending prompt ...")
                if rank == 0:
                    prompt_output = prompt_expander(args.prompt, tar_lang=args.prompt_extend_target_lang, seed=args.base_seed)
                    if not prompt_output.status:
                        logging.info(f"Extending prompt failed: {prompt_output.message}")
                        logging.info("Falling back to original prompt.")
                        input_prompt = args.prompt
                    else:
                        input_prompt = prompt_output.prompt
                    input_prompt = [input_prompt]
                else:
                    input_prompt = [None]
                if dist.is_initialized():
                    dist.broadcast_object_list(input_prompt, src=0)
                args.prompt = input_prompt[0]
                logging.info(f"Extended prompt: {args.prompt}")

            logging.info("Generating video ...")
            video = wan_t2v.generate(
                args.prompt,
                size=SIZE_CONFIGS[args.size],
                frame_num=args.frame_num,
                shift=args.sample_shift,
                sample_solver=args.sample_solver,
                sampling_steps=args.sample_steps,
                guide_scale=args.sample_guide_scale,
                seed=args.base_seed,
                offload_model=args.offload_model)

            if rank == 0:
                # 文件保存：若指定了 save_folder，则保存到该文件夹，文件名仅包含经过清洗的 prompt 信息
                if args.save_folder is not None:
                    os.makedirs(args.save_folder, exist_ok=True)
                    file_prompt = sanitize_filename(args.prompt)
                    save_file = os.path.join(args.save_folder, f"{file_prompt}.mp4")
                else:
                    # 若未指定 save_folder，则使用 save_file 参数（若未指定，则构造默认文件名）
                    if args.save_file is None:
                        file_prompt = sanitize_filename(args.prompt)
                        save_file = f"{args.task}_{args.size.replace('*','x')}_{args.ulysses_size}_{args.ring_size}_{file_prompt}.mp4"
                    else:
                        save_file = args.save_file
                logging.info(f"Saving generated video to {save_file}")
                cache_video(
                    tensor=video[None],
                    save_file=save_file,
                    fps=cfg.sample_fps,
                    nrow=1,
                    normalize=True,
                    value_range=(-1, 1))
        logging.info("Finished.")

    # 针对文生图任务（只生成单个例子）
    elif args.task.startswith("t2i"):
        if args.prompt is None:
            args.prompt = EXAMPLE_PROMPT[args.task]["prompt"]
        logging.info(f"Input prompt: {args.prompt}")
        if args.use_prompt_extend:
            logging.info("Extending prompt ...")
            if rank == 0:
                prompt_output = prompt_expander(args.prompt, tar_lang=args.prompt_extend_target_lang, seed=args.base_seed)
                if not prompt_output.status:
                    logging.info(f"Extending prompt failed: {prompt_output.message}")
                    logging.info("Falling back to original prompt.")
                    input_prompt = args.prompt
                else:
                    input_prompt = prompt_output.prompt
                input_prompt = [input_prompt]
            else:
                input_prompt = [None]
            if dist.is_initialized():
                dist.broadcast_object_list(input_prompt, src=0)
            args.prompt = input_prompt[0]
            logging.info(f"Extended prompt: {args.prompt}")

        logging.info("Creating WanT2V pipeline.")
        wan_t2v = wan.WanT2V(
            config=cfg,
            checkpoint_dir=args.ckpt_dir,
            device_id=device,
            rank=rank,
            t5_fsdp=args.t5_fsdp,
            dit_fsdp=args.dit_fsdp,
            use_usp=(args.ulysses_size > 1 or args.ring_size > 1),
            t5_cpu=args.t5_cpu,
        )
        logging.info("Generating image ...")
        wan_t2v.generate = types.MethodType(wan_t2v_generate, wan_t2v)
        video = wan_t2v.generate(
            args.prompt,
            size=SIZE_CONFIGS[args.size],
            frame_num=args.frame_num,
            shift=args.sample_shift,
            sample_solver=args.sample_solver,
            sampling_steps=args.sample_steps,
            guide_scale=args.sample_guide_scale,
            seed=args.base_seed,
            offload_model=args.offload_model)
        if rank == 0:
            if args.save_file is None:
                formatted_prompt = args.prompt.replace(" ", "_").replace("/", "_")[:50]
                args.save_file = f"{args.task}_{args.size.replace('*','x')}_{args.ulysses_size}_{args.ring_size}_{formatted_prompt}.png"
            logging.info(f"Saving generated image to {args.save_file}")
            cache_image(
                tensor=video.squeeze(1)[None],
                save_file=args.save_file,
                nrow=1,
                normalize=True,
                value_range=(-1, 1))
        logging.info("Finished.")

if __name__ == "__main__":
    args = _parse_args()
    generate(args)
