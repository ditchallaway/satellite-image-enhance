# 卫星图像增强 Skill

发布后的 GitHub 地址：

`https://github.com/ditchallaway/satellite-image-enhance`

这个仓库打包的是一个可以安装到 Codex 或兼容 agent 里的 skill：

`satellite-image-enhance/`

它不是独立 App，也不是网页图像处理工具。它的作用是让 agent 学会如何处理卫星图像，同时尽量保持地理精度和光谱保真度。

## 它能做什么

- 判断卫星图像应该走哪种增强方式。
- 优先保证地理精度和光谱保真度，而不是追求戏剧性的视觉效果。
- 约束去云、对比度增强、光谱波段合并、AI 图像编辑等操作。
- 提供可选的本地批量处理脚本。
- 批量处理前先审查图像，虚构地理特征或隐藏关键地形数据的结果要拒绝。

## 它不能做什么

- 它不是独立软件，没有图形界面。
- 仓库里不包含真实卫星图像。
- 仓库里不包含 API key、云服务凭证、本地模型文件。
- 它不能保证另一台电脑有同样的图像处理能力。
- 它不能用于虚构地形、捏造地理特征、隐藏关键地形或环境数据。

## 安装到 Codex

1. 下载或 clone 这个仓库。
2. 复制里面这个子文件夹：

   `satellite-image-enhance/`

3. 放到 Codex skills 目录：

   `~/.codex/skills/satellite-image-enhance/`

4. 重启 Codex，或按你的环境刷新 skill index。
5. 让 Codex 读取这个网址：

   `https://github.com/ditchallaway/satellite-image-enhance`

给另一台 Codex 的最短交接话术：

```text
请安装并使用这个卫星图像增强 skill：
https://github.com/ditchallaway/satellite-image-enhance

真正要安装的 skill 子文件夹是：
satellite-image-enhance/
```

## 必需配置

必需：

- 一个能读取本地图像、能遵守 `SKILL.md` 的 agent host。
- 用户自己提供本地卫星图像。
- 对外发布前必须人工复核。

如果要用仓库里的本地批量脚本，还需要：

- Python 3.10+
- `Pillow`
- `numpy`
- `opencv-python`

安装示例：

```bash
python -m pip install pillow numpy opencv-python
```

## 可选增强

可选：

- agent 自带的图像编辑能力。
- 本地确定性批量处理流程。
- 用户自己配置的本地或云端图像模型。
- GDAL、QGIS 或其它你自己已有的地理空间工具。

这些都是可选增强。这个 skill 不默认假设另一台电脑有作者本机的路径、凭证或模型环境。

## 安全边界

- 批量处理前先看完整图像文件夹。
- 不要覆盖原图，除非用户明确要求。
- 增强后的图像对外使用前必须人工复核。
- 如果用户说只处理某个波段或区域，就只能改那个部分。
- 不能虚构地理特征、篡改地形高程数据、扭曲地图投影或隐藏关键地形信息。
- 不能用图像处理隐藏会影响分析人员、研究人员或决策者判断的真实地理或环境数据。

## 准确度和输入质量

增强效果取决于原始图像质量：

- 高分辨率、低噪声、无云覆盖的场景效果更好。
- 采集参数一致、场景覆盖完整，批量判断会更准。
- 云量大、分辨率低、严重压缩或辐射质量差的图像会降低可信度。
- agent 可以结合图像内容、文件名、文件夹名和用户说明来判断场景类型和处理重点。
- 外部权限，例如云模型权限或本地文件访问权限，只能在用户授权后使用。

## 自检

分享前建议运行：

```bash
python satellite-image-enhance/scripts/privacy_scan.py --root .
python satellite-image-enhance/scripts/capability_check.py
python -m py_compile satellite-image-enhance/scripts/*.py
```

## License

MIT。详见 `LICENSE`。
