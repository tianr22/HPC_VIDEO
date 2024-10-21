## 常用指令
查看分区：
```
sinfo
```
查看运行中的任务：
```
squeue
```
终止任务：
```
scancel
```
运行：
```
srun --account=a100 --partition=a100 --gres=gpu:1 bash run.sh
```

## 各个模型的运行用时
| 模型 | GPU=1 | GPU=2 | GPU=4 | GPU=8 | 
| --- | --- | --- | --- | --- |
| cogvideoX-5b |
| latte | 00:31 | 00:20 |
| open_sora |
| vchitect | 02:29 | 01:43 |

## 加速比
注意换算分钟和秒的关系

| 模型 | GPU=1 | GPU=2 | GPU=4 | GPU=8 | 
| --- | --- | --- | --- | --- |
| cogvideoX-5b | 1.00 | 
| latte | 1.00 | 1.55 |
| open_sora | 1.00 |
| vchitect | 1.00 | 1.45 | 

## profile
### cogvideoX-5b
