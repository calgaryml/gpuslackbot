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

## Build Python Wheel

```
python -m build --wheel
```

## Slack Workspace Permissions/Configuration
In order to run this bot, you first need to add the app to your Slack workspace, getting both a Slack App Token and Bot Token. These must be loaded as environmental variables:

```
export SLACK_APP_TOKEN=xapp-***
export SLACK_BOT_TOKEN=xoxb-***
python3 gpuslackbot.py
```

## Installing as a Systemd Service

Copy the relevant files into your systemd configuration directly, e.g.

```
$ sudo cp systemd/system/gpuslackbot.service /etc/systemd/system/
$ sudo chmod 644 /etc/systemd/system/gpuslackbot.service
$ sudo mkdir /etc/systemd/system/gpuslackbot.service.d
$ sudo cp systemd/system/gpuslackbot.service.d/gpuslackbot.conf /etc/systemd/system/gpuslackbot.service.d/
```

And then edit the file `systemd/system/gpuslackbot.service.d/gpuslackbot.conf` to add the required slack token environmental variable (see above). Next test the service, and ensure that it is running:

```
$ sudo service start myservice
$ sudo service gpuslackbot status
● gpuslackbot.service - GPU Slack Bot
     Loaded: loaded (/etc/systemd/system/gpuslackbot.service; disabled; vendor preset: enabled)
    Drop-In: /etc/systemd/system/gpuslackbot.service.d
             └─gpuslackbot.conf
     Active: active (running) since Mon 2023-03-13 00:00:00 MDT; 9s ago
   Main PID: 86941 (python3)
      Tasks: 2 (limit: 38352)
     Memory: 36.2M
        CPU: 187ms
     CGroup: /system.slice/gpuslackbot.service
             └─86941 python3 -m gpuslackbot.gpuslackbot

Mar 13 00:00:00 hostname systemd[1]: Started GPU Slack Bot.
Mar 13 00:00:00 hostname python3[86941]: INFO:root:Started Slack GPU Bot on Host: hostname, responding to command: /gpus_hostname
Mar 13 00:00:00 hostname python3[86941]: INFO:slack_bolt.AsyncApp:A new session (s_xxxxxxxxxxx) has been established
Mar 13 00:00:00 hostname python3[86941]: INFO:slack_bolt.AsyncApp:⚡️ Bolt app is running!
```

If the bot is working well, you can enable to service at boot:
```
$ sudo systemctl enable gpuslackbot.service 
Created symlink /etc/systemd/system/multi-user.target.wants/gpuslackbot.service → /etc/systemd/system/gpuslackbot.service.
```

### Multiple Servers/Hosts
This app uses the Slack Socket interface, which does not broadcast consistently across multiple apps listening on one channel. Therefore, when using with multiple servers, you will need to register a seperate app (APP token and Bot token) for each server. Also ensure the app is setup to listen to the correct command.
