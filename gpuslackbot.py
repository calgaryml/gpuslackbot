#!/usr/bin/env python

## export SLACK_APP_TOKEN=xapp-***
## export SLACK_BOT_TOKEN=xoxb-***
## python app.py

import os
import sys
import socket

import pynvml
from pynvml.smi import nvidia_smi
from fastapi import FastAPI
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

fastapi_app = FastAPI()

# Install the Slack app and get xoxb-token in advance
slack_app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])
socket_handler = AsyncSocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])

# Get basic information about the system/GPUs
hostname = socket.gethostname()
nvsmi = nvidia_smi.getInstance()
device_count = pynvml.nvmlDeviceGetCount()

def query_gpu(index):
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)
    
    name = pynvml.nvmlDeviceGetName(handle)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    util = utilization.gpu
    mem = utilization.memory
    temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
    power = int(pynvml.nvmlDeviceGetPowerUsage(handle))/1000
    
    return {'id': id, 'name': name, 'util': util, 'mem': mem, 'temp': temp, 'power': power}

# Function to query GPUS and return formatted string.
def query_gpus():
    gpu_status_lines = ('GPU {id} ({name}): Util: {util} Mem: {mem} {temp}C {power}W'.format(*query_gpu(i)) for i in range(device_count))

def query_accounted_apps():
    accounted_apps=nvsmi.DeviceQuery('accounted-apps')
    return accounted_apps

@slack_app.command("/gpus")
async def command(ack, body, respond):
    await ack()
    await respond('\n'.join(query_gpus()))

@fastapi_app.on_event("startup")
async def startup():
    # client.chat_postMessage(channel='#gpu-monitoring', text='GPU Monitor on {hostname} started!')
    # this is not ideal for # of workers > 1.
    await socket_handler.connect_async()


if __name__ == "__main__":
    # Create an app-level token with connections:write scope
    socket_handler.start()