# Batch-import-default-config-to-meshtastic-node
apply default values to node, 
user specific settings in top of file
other defaults are in code

it applies settings, reboot, checks if it applies succesfully, and if any differences fire another loop till all is identical


### example usage from CLI, params are optional
> [!CAUTION]
> passing parameters in CLI - not tested

```python set-my-defaults-pythonapi -tgt=COM4 -ln=JB_MOB_4 -sn=JBM4```

```python set-my-defaults-pythonapi -tgt=ip:192.168.1.171 -ln=JB_MOB_Tak4 -sn=JBM4```

if no params passed, defaults from code are used
