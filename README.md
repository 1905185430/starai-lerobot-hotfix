# StarAI LeRobot Hotfix

这个仓库用于记录和迁移 StarAI/FashionStar 机械臂在 LeRobot 标定时需要的本地修复。

## 修复内容

当前修复覆盖三个问题：

1. `lerobot_motor_starai` 的 `StaraiMotorsBus.sync_read()` 会把角度缓存 `current_position` 覆写成 0-4096 encoder 值，导致后续读取卡到 `4096`。
2. `fashionstar_uart_sdk` 的 `Monitor_data.flash()` 只有在新旧位置差小于 10 度时才更新，关节移动超过 10 度时位置会冻结。
3. `lerobot_teleoperator_violin` 在连接时会自动执行 slow start，并强制移动到预设初始姿态；标定场景下禁用这个自动动作。

## 适用环境

已在以下版本上验证：

- `lerobot_motor_starai==0.0.4`
- `fashionstar_uart_sdk==1.3.9`
- `lerobot_teleoperator_violin`

如果上游包升级后源码结构变化，脚本会拒绝修改并报错，而不是盲目写入。

## 使用方式

在目标电脑上先安装好 LeRobot 和 StarAI 相关包，然后运行：

```bash
conda activate lerobot
python patch_starai_hotfixes.py
```

成功时会看到：

```text
patched: lerobot_motor_starai sync_read position cache
patched: fashionstar_uart_sdk Monitor_data.flash position update
patched: lerobot_teleoperator_violin automatic initial-position move
```

重复运行是安全的，已经修复过会显示：

```text
already patched
```

## 标定命令

```bash
lerobot-calibrate \
  --teleop.type=lerobot_teleoperator_violin \
  --teleop.port=/dev/ttyUSB0 \
  --teleop.id=my_awesome_staraiviolin_arm
```

如果希望标定文件也跟项目一起迁移，可以显式指定目录：

```bash
lerobot-calibrate \
  --teleop.type=lerobot_teleoperator_violin \
  --teleop.port=/dev/ttyUSB0 \
  --teleop.id=my_awesome_staraiviolin_arm \
  --teleop.calibration_dir=./calibration/starai_violin
```

## 迁移标定文件

默认标定文件位于：

```bash
~/.cache/huggingface/lerobot/calibration/teleoperators/starai_violin/
```

把旧电脑上的对应 JSON 文件复制到新电脑同一路径即可，例如：

```bash
mkdir -p ~/.cache/huggingface/lerobot/calibration/teleoperators/starai_violin
cp my_awesome_staraiviolin_arm.json \
  ~/.cache/huggingface/lerobot/calibration/teleoperators/starai_violin/
```

注意：`--teleop.id` 必须和 JSON 文件名一致。

## 建议的部署顺序

1. 在新电脑安装系统依赖、conda 环境和 LeRobot。
2. 安装 StarAI/FashionStar 相关包。
3. 运行 `python patch_starai_hotfixes.py`。
4. 复制 calibration JSON，或重新运行标定。
5. 运行标定/遥操作命令验证。

## 建议建仓方式

```bash
git init
git add README.md patch_starai_hotfixes.py .gitignore
git commit -m "Add StarAI LeRobot hotfix"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```
