# StarAI LeRobot Hotfix

这个仓库用于记录和迁移 StarAI/FashionStar 机械臂在 LeRobot 标定时需要的本地修复。

我在使用 `lerobot-calibrate` 标定 StarAI Violin 机械臂时遇到两个主要现象：

- 标定读取到的 `POS` 很快卡死在 `4096`，移动关节也不再变化。
- 启动标定命令后，机械臂会在进入标定流程前自动移动到一组预设姿态。

排查后确认问题不在机械臂操作流程，而是在 StarAI/FashionStar 的 LeRobot 适配包和 SDK 代码里。这个仓库提供一个可重复执行的补丁脚本，方便在新电脑、新 conda 环境或重新安装依赖后恢复这些修复。

## 修复内容

当前修复覆盖三个问题：

1. `lerobot_motor_starai` 的 `StaraiMotorsBus.sync_read()` 会把角度缓存 `current_position` 覆写成 0-4096 encoder 值，导致后续读取卡到 `4096`。
2. `fashionstar_uart_sdk` 的 `Monitor_data.flash()` 只有在新旧位置差小于 10 度时才更新，关节移动超过 10 度时位置会冻结。
3. `lerobot_teleoperator_violin` 在连接时会自动执行 slow start，并强制移动到预设初始姿态；标定场景下禁用这个自动动作。

## 根因说明

### 1. `sync_read()` 破坏性覆写位置缓存

`lerobot_motor_starai` 的 `StaraiMotorsBus.sync_read()` 从 SDK 读取的是舵机角度，范围大致是 `-180` 到 `180` 度。但原实现把这个角度值转换成 LeRobot 使用的 0-4096 raw position 后，又写回了 SDK 的 `monitor_data[name].current_position`。

这会污染缓存。第一次读取可能正常，例如 `5` 度被转换成约 `2105`。第二次读取时，SDK 的 `flash()` 会拿旧的 raw 值 `2105` 和新的角度值 `6` 比较，差值远大于 10，于是拒绝更新。随后 `sync_read()` 又把 `2105` 当角度 clamp 到 `180`，最终转换成 `4096`。之后位置读数就会锁死。

修复方式：转换时只使用局部变量 `pos`，不再修改 `monitor_data[name].current_position`。

### 2. `Monitor_data.flash()` 的 10 度过滤会冻结位置

`fashionstar_uart_sdk` 的 `Monitor_data.flash()` 原逻辑是：

```python
if abs(self.current_position - current_position) < 10:
    self.current_position = current_position
```

这个过滤器在正常手动标定时也不合理。用户移动关节超过 10 度后，SDK 反而不更新当前位置，导致后续读数冻结。

修复方式：每次收到新位置都更新 `self.current_position`。

### 3. 标定连接阶段自动移动机械臂

`lerobot_teleoperator_violin` 的 `connect()` 在检测到已有 calibration 时会执行：

```python
self.move_to_initial_position()
```

这个函数会发送 `Goal_Position`，让机械臂自动移动到预设姿态。标定场景下这不是期望行为，也有安全风险。

修复方式：保留连接流程，但跳过自动 slow start 初始位置移动。

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

本仓库已经包含当前 StarAI Violin teleoperator 的标定文件：

```bash
calibration/teleoperators/starai_violin/my_awesome_staraiviolin_arm.json
```

默认标定文件位于：

```bash
~/.cache/huggingface/lerobot/calibration/teleoperators/starai_violin/
```

把旧电脑上的对应 JSON 文件复制到新电脑同一路径即可，例如：

```bash
mkdir -p ~/.cache/huggingface/lerobot/calibration/teleoperators/starai_violin
cp calibration/teleoperators/starai_violin/my_awesome_staraiviolin_arm.json \
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
