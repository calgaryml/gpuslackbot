#!/usr/bin/env python

## export SLACK_APP_TOKEN=xapp-***
## export SLACK_BOT_TOKEN=xoxb-***
## python app.py

import os
import sys
import socket
import logging

import pynvml
from pynvml.smi import nvidia_smi
from fastapi import FastAPI
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

logging.basicConfig(level=logging.DEBUG)

# Install the Slack app and get xoxb-token in advance
slack_app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])
socket_handler = AsyncSocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])

fastapi_app = FastAPI()

# Get basic information about the system/GPUs
hostname = socket.gethostname()
nvsmi = nvidia_smi.getInstance()
device_count = pynvml.nvmlDeviceGetCount()

# Function to query individual GPUs and return dict.
def query_gpu(index):
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)
    
    name = pynvml.nvmlDeviceGetName(handle)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    util = utilization.gpu
    mem = utilization.memory
    temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
    power = int(pynvml.nvmlDeviceGetPowerUsage(handle))/1000
    
    return {'id': index, 'name': name, 'util': util, 'mem': mem, 'temp': temp, 'power': power}

# Function to query GPUS and return formatted string.
def query_gpus():
    return ['GPU {id} ({name}): Util: {util} Mem: {mem} {temp}C {power}W'.format(**query_gpu(i)) for i in range(device_count)]

def query_accounted_apps():
    accounted_apps=nvsmi.DeviceQuery('accounted-apps')
    return accounted_apps

@slack_app.event({"type": "message"})
async def receive_message(event, say):
    await say("Hi")

@slack_app.command("/gpus")
async def command(ack, body, respond):
    await ack()
    await respond('\n'.join(query_gpus()))

@fastapi_app.get("/healthcheck")
async def healthcheck():
    if socket_handler.client is not None and await socket_handler.client.is_connected():
        return "OK"
    return "BAD"

@fastapi_app.on_event('startup')
async def start_slack_socket_conn():
    await socket_handler.connect_async()

@fastapi_app.on_event('shutdown')
async def start_slack_socket_conn():
    await socket_handler.close_async()

print(query_gpus())