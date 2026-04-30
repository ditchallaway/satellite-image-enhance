# 房源修图 Skill

发布后的 GitHub 地址：

`https://github.com/yyxone/real-estate-photo-editing`

这个仓库打包的是一个可以安装到 Codex 或兼容 agent 里的 skill：

`real-estate-photo-editing/`

它不是独立 App，也不是网页修图工具。它的作用是让 agent 学会如何处理房源照片，同时尽量保持照片真实、不误导客户。

## 它能做什么

- 判断房源照片应该走哪种修图方式。
- 优先保证真实可信，而不是把房子修成假的豪华效果。
- 约束去杂物、调亮、白平衡、窗户、线条、AI 修图等操作。
- 提供可选的本地批量修图脚本。
- 批量处理前先审查照片，修坏或虚构房源细节的结果要拒绝。

## 它不能做什么

- 它不是独立软件，没有图形界面。
- 仓库里不包含真实房源照片。
- 仓库里不包含 API key、云服务凭证、本地模型文件。
- 它不能保证另一台电脑有同样的图片编辑能力。
- 它不能用于虚构装修、虚构家具、隐藏真实房况问题。

## 安装到 Codex

1. 下载或 clone 这个仓库。
2. 复制里面这个子文件夹：

   `real-estate-photo-editing/`

3. 放到 Codex skills 目录：

   `~/.codex/skills/real-estate-photo-editing/`

4. 重启 Codex，或按你的环境刷新 skill index。
5. 让 Codex 读取这个网址：

   `https://github.com/yyxone/real-estate-photo-editing`

给另一台 Codex 的最短交接话术：

```text
请安装并使用这个房源修图 skill：
https://github.com/yyxone/real-estate-photo-editing

真正要安装的 skill 子文件夹是：
real-estate-photo-editing/
```

## 必需配置

必需：

- 一个能读取本地图片、能遵守 `SKILL.md` 的 agent host。
- 用户自己提供本地房源照片。
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

- agent 自带的图片编辑能力。
- 本地确定性批量修图流程。
- 用户自己配置的本地或云端图片模型。
- Darktable 或其它你自己已有的照片工具。

这些都是可选增强。这个 skill 不默认假设另一台电脑有作者本机的路径、凭证或模型环境。

## 安全边界

- 批量修图前先看完整照片文件夹。
- 不要覆盖原图，除非用户明确要求。
- 修好的照片对外使用前必须人工复核。
- 如果用户说“只去掉某个东西”，就只能改那个东西。
- 不能改变房间结构、固定装修、家电、窗外真实视野、光照方向或重要房况事实。
- 不能用修图隐藏会影响买家、租客或经纪人判断的真实缺陷。

## 准确度和输入质量

修图效果取决于原始照片质量：

- 清晰、明亮、不糊、不压缩过度的照片效果更好。
- 拍摄角度规律、每个房间覆盖完整，批量判断会更准。
- 太暗、太歪、太乱、低分辨率、严重压缩的照片会降低可信度。
- agent 可以结合图片内容、文件名、文件夹名和用户说明来判断房间和处理重点。
- 外部权限，例如云模型权限或本地文件访问权限，只能在用户授权后使用。

## 自检

分享前建议运行：

```bash
python real-estate-photo-editing/scripts/privacy_scan.py --root .
python real-estate-photo-editing/scripts/capability_check.py
python -m py_compile real-estate-photo-editing/scripts/*.py
```

## License

MIT。详见 `LICENSE`。
