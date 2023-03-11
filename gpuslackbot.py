#!/usr/bin/env python

## export SLACK_APP_TOKEN=xapp-***
## export SLACK_BOT_TOKEN=xoxb-***
## python app.py

import os
import sys
import socket
import logging
import time

import pynvml
from pynvml.smi import nvidia_smi

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

logging.basicConfig(level=logging.DEBUG)

# Install the Slack app and get xoxb-token in advance
slack_app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# Get basic information about the system/GPUs
hostname = socket.gethostname()
hostname = 'kolossus'
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

# Function to query GPUS and return message payload
def query_gpus():
    gpu_responses = '\n'.join(['GPU {id} ({name}): Util: {util} Mem: {mem} {temp}C {power}W'.format(**query_gpu(i)) for i in range(device_count)])

    return {"blocks": [
      {
        "type": "header",
        "text": {
          "type": "plain_text",
          "text": f"{hostname}"
        }
      },
      {
        "type": "divider"
      },
      {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": gpu_responses,
            "emoji": True
        },
      }
    ]}

def query_accounted_apps():
    accounted_apps=nvsmi.DeviceQuery('accounted-apps')
    return accounted_apps

@slack_app.command(f"/gpus_{hostname}")
async def command(ack, body, respond):
    logging.debug(body)
    await ack()
    response = query_gpus()
    logging.debug(response)
    await respond(response)

@slack_app.view("socket_modal_submission")
async def submission(ack):
    await ack()

async def main():
    socket_handler = AsyncSocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])
    await socket_handler.start_async()

if __name__ == "__main__":
    import asyncio

    logging.info(f"Started Slack GPU Bot on Host: {hostname}, responding to command: /gpus_{hostname}")
    asyncio.run(main())