<div align=center>
  
# [ICCV 2025] *TaylorSeer*: From Reusing to Forecasting: Accelerating Diffusion Models with *TaylorSeers*

<p>
<a href='https://arxiv.org/abs/2503.06923'><img src='https://img.shields.io/badge/Paper-arXiv-red'></a>
<a href='https://taylorseer.github.io/TaylorSeer/'><img src='https://img.shields.io/badge/Project-Page-blue'></a>
</p>

</div>

## 🔥 News

* `2025/12/06` TaylorSeer is now natively supported in Diffusers. Check out the [doc](https://huggingface.co/docs/diffusers/main/en/optimization/cache#taylorseer-cache). Thanks to @toilaluan for [contributing](https://github.com/huggingface/diffusers/pull/12648) it.

* `2025/06/26` 💥💥 TaylorSeer is honored to be accepted by ICCV 2025!

* `2025/05/03` 🚀🚀 TaylorSeer for HiDream is released.

* `2025/03/30` 🚀🚀 TaylorSeer for Wan2.1 is released.

* `2025/03/30` 🚀🚀 The Diffusers inference scripts for TaylorSeers and the xDiT scripts applicable for multi-GPU parallel inference have been officially released.

* `2025/03/10` 🚀🚀 Our latest work "From Reusing to Forecasting: Accelerating Diffusion Models with TaylorSeers" is released! Codes are available at [TaylorSeer](https://github.com/Shenyi-Z/TaylorSeer)! TaylorSeer supports lossless compression at a rate of 4.99x on FLUX.1-dev (with a latency speedup of 3.53x) and high-quality acceleration at a compression rate of 5.00x on HunyuanVideo (with a latency speedup of 4.65x)! We hope *TaylorSeer* can move the paradigm of feature caching methods from reusing to forecasting.For more details, please refer to our latest research paper.
* `2025/02/19` 🚀🚀 ToCa solution for **FLUX** has been officially released after adjustments, now achieving up to **3.14× lossless acceleration** (in FLOPs)!
* `2025/01/22` 💥💥 ToCa is honored to be accepted by ICLR 2025!
* `2024/12/29` 🚀🚀 We release our work [DuCa](https://arxiv.org/abs/2412.18911) about accelerating diffusion transformers for FREE, which achieves nearly lossless acceleration of **2.50×** on [OpenSora](https://github.com/hpcaitech/Open-Sora)! 🎉 **DuCa also overcomes the limitation of ToCa by fully supporting FlashAttention, enabling broader compatibility and efficiency improvements.**
* `2024/12/24` 🤗🤗 We release an open-sourse repo "[Awesome-Token-Reduction-for-Model-Compression](https://github.com/xuyang-liu16/Awesome-Token-Reduction-for-Model-Compression)", which collects recent awesome token reduction papers! Feel free to contribute your suggestions!
* `2024/12/10` 💥💥 Our team's recent work, **SiTo** (https://github.com/EvelynZhang-epiclab/SiTo), has been accepted to **AAAI 2025**. It accelerates diffusion models through adaptive **Token Pruning**.
* `2024/07/15` 🤗🤗 We release an open-sourse repo "[Awesome-Generation-Acceleration](https://github.com/xuyang-liu16/Awesome-Generation-Acceleration)", which collects recent awesome generation accleration papers! Feel free to contribute your suggestions!

<details>
  <summary><strong>Abstract</strong></summary>

  Diffusion Transformers (DiT) have revolutionized high-fidelity image and video synthesis, yet their computational demands remain prohibitive for real-time applications. To solve this problem, feature caching has been proposed to accelerate diffusion models by caching the features in the previous timesteps and then reusing them in the following timesteps. However, at timesteps with significant intervals, the feature similarity in diffusion models decreases substantially, leading to a pronounced increase in errors introduced by feature caching, significantly harming the generation quality. To solve this problem, we propose TaylorSeer, which firstly shows that features of diffusion models at future timesteps can be predicted based on their values at previous timesteps. Based on the fact that features change slowly and continuously across timesteps, TaylorSeer employs a differential method to approximate the higher-order derivatives of features and predict features in future timesteps with Taylor series expansion. Extensive experiments demonstrate its significant effectiveness in both image and video synthesis, especially in high acceleration ratios. For instance, it achieves an almost lossless acceleration of 4.99 $\times$ on FLUX and 5.00 $\times$ on HunyuanVideo without additional training. On DiT, it achieves $3.41$ lower FID compared with previous SOTA at $4.53$ $\times$ acceleration.

</details>

## 🧩 Community Contributions

Thanks to all the open-source contributors for their strong support! We’d love to hear from you!

* ComfyUI-TaylorSeer-philipy1219 (FP8 Inference on FLUX, more video models coming): [ComfyUI-TaylorSeer-philipy1219](https://github.com/philipy1219/ComfyUI-TaylorSeer) by [philipy1219](https://github.com/philipy1219).

## 🛠 Installation

``` cmd
git clone https://github.com/Shenyi-Z/TaylorSeer.git
```


## TaylorSeer-FLUX

TaylorSeer achieved a lossless computational compression of 4.99 $\times$ and a Latency Speedup of 3.53 $\times$ on FLUX.1-dev, as measured by [ImageReward](https://github.com/THUDM/ImageReward) for comprehensive quality. To run TaylorSeer-FLUX, see [TaylorSeer-FLUX](TaylorSeer-FLUX.md).

Besides, We have provided examples of inference scripts for the **diffusers version**, as well as multi-GPU parallel **xDiT inference scripts**. You can also conduct tests based on them, located at [TaylorSeers-Diffusers](./TaylorSeers-Diffusers ) and [TaylorSeers-xDiT](./TaylorSeers-xDiT) respectively.

## TaylorSeer-HunyuanVideo

TaylorSeer achieved a computational compression of 5.00 $\times$ and a remarkable Latency Speedup of 4.65 $\times$ on HunyuanVideo, as comprehensively measured by the [VBench](https://github.com/Vchitect/VBench) metric. Compared to previous methods, it demonstrated significant improvements in both acceleration efficiency and quality. To run TaylorSeer-HunyuanVideo, see [TaylorSeer-HunyuanVideo](TaylorSeer-HunyuanVideo.md).

In addition, our scripts also support multi-GPU parallel acceleration implemented by HunyuanVideo using xDiT. In this case, the acceleration effect brought by the cache and the acceleration effect of multi-GPU parallelism are independent of each other and multiply, achieving extremely high acceleration effects.

## TayorSeer-DiT

TaylorSeer achieved a lossless computational compression of 2.77 $\times$ on the base model DiT, as comprehensively evaluated by metrics such as FID. Its performance across various acceleration ratios significantly surpassed previous methods. For instance, in an extreme scenario with a 4.53 $\times$ compression ratio, TaylorSeer's FID only increased by 0.33 from the non-accelerated baseline of 2.32, reaching 2.65, while ToCa and DuCa exhibited FID scores above 6.0 under the same conditions. To run TaylorSeer-DiT,see [TaylorSeer-DiT](TaylorSeer-DiT.md).

## TaylorSeer-Wan2.1

We implemented the TaylorSeer acceleration method on Wan2.1, with support for multi-GPU parallel inference. The installation and inference commands for TaylorSeer-Wan2.1 are fully compatible with those of Wan2.1. To run TaylorSeer-Wan2.1, see [TaylorSeer-Wan2.1](TaylorSeer-Wan2.1.md).

## TaylorSeer-HiDream

The recently open-sourced image generation model **HiDream**, despite its impressive output quality, faces increasing demands for acceleration due to its longer inference time. We applied **TaylorSeer** to accelerate HiDream’s inference, achieving a **72% reduction in runtime**. For more details, see [TaylorSeer-HiDream](TaylorSeer-HiDream.md).

## 👍 Acknowledgements

- Thanks to [DiT](https://github.com/facebookresearch/DiT) for their great work and codebase upon which we build TaylorSeer-DiT.
- Thanks to [FLUX](https://github.com/black-forest-labs/flux) for their great work and codebase upon which we build TaylorSeer-FLUX.
- Thanks to [HiDream](https://github.com/HiDream-ai/HiDream-I1) for their great work and codebase upon which we build TaylorSeer-HiDream.
- Thanks to [HunyuanVideo](https://github.com/Tencent/HunyuanVideo) for their great work and codebase upon which we build TaylorSeer-HunyuanVideo.
- Thanks to [Wan2.1](https://github.com/Wan-Video/Wan2.1) for their great work and codebase upon which we build TaylorSeer-Wan2.1.
- Thanks to [ImageReward](https://github.com/THUDM/ImageReward) for Text-to-Image quality evaluation.
- Thanks to [VBench](https://github.com/Vchitect/VBench) for Text-to-Video quality evaluation.


## 📌 Citation

```bibtex
@article{TaylorSeer2025,
  title={From Reusing to Forecasting: Accelerating Diffusion Models with TaylorSeers},
  author={Liu, Jiacheng and Zou, Chang and Lyu, Yuanhuiyi and Chen, Junjie and Zhang, Linfeng},
  journal={arXiv preprint arXiv:2503.06923},
  year={2025}
}
```

## :e-mail: Contact

If you have any questions, please email [`shenyizou@outlook.com`](mailto:shenyizou@outlook.com).

## :star: Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Shenyi-Z/TaylorSeer&type=Date)](https://www.star-history.com/#Shenyi-Z/TaylorSeer&Date)
