# Slack GPU Bot
This bot will respond to the command `/gpus_<hostname>` with the current status of the GPUs on the given host:

## :computer: hostname

---------

**GPU Status**: :yawning_face:

Util: `█               ` 7%, Mem: `█████████████▌  ` 90%

:zero: NVIDIA GeForce GTX TITAN X, Temp: 43C :snowflake: , Power: 73W :electric_plug:

---------

**GPU Status**: :hot_face:

Util: `█████████████▌  ` 90%, Mem: `█████████████▌  ` 90%

:one: NVIDIA GeForce GTX TITAN X, Temp: 43C :snowflake: , Power: 234W :electric_plug:

---------

## Python Requirements
You can install the python requirments for this bot:
```
pip3 install --user -r requirements.txt
```

In addition it will need a working CUDA install, with nvidia-smi/nvml libraries installed.

## Slack Workspace Permissions/Configuration
In order to run this bot, you first need to add the app to your Slack workspace, getting both a Slack App Token and Bot Token. These must be loaded as environmental variables:

```
export SLACK_APP_TOKEN=xapp-***
export SLACK_BOT_TOKEN=xoxb-***
python3 gpuslackbot.py
```
### Multiple Servers/Hosts
This app uses the Slack Socket interface, which does not broadcast consistently across multiple apps listening on one channel. Therefore, when using with multiple servers, you will need to register a seperate app (APP token and Bot token) for each server. Also ensure the app is setup to listen to the correct command.
