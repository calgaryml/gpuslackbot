#!/usr/bin/env python3
import os
import socket
import logging

import pynvml

from tqdm import tqdm

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

logging.basicConfig(level=logging.INFO)

# Install the Slack app and get xoxb-token in advance
slack_app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# Get basic information about the system/GPUs
hostname = socket.gethostname()

try:
    pynvml.nvmlInit()
    logging.debug("Initialized NVML")
except:
    logging.error("Failed to initialize NVML")

device_count = pynvml.nvmlDeviceGetCount()

idemojis = {0: ':zero:', 1: ':one:', 2: ':two:', 3: ':three:', 4: ':four', 5: ':five:', 6: ':six:', 7: ':seven:', 8: ':eight:'}
def id2emoji(gpu_id):
    if gpu_id in idemojis.keys():
        return idemojis[gpu_id]
    return f"{gpu_id}"

def util2emoji(util):
    return ':yawning_face:' if util < 20 else ':flushed:' if util < 80 else ':hot_face:'

def temp2emoji(temp):
    return ':snowflake:' if temp < 60 else ':fire:'

def percentage_bar(percent):
    # Have to redirect tqdm to output to /dev/null, otherwise outputs to stderr by default (aside from string)
    return tqdm(total=100, initial=percent, bar_format='|{bar:15}|', file=open(os.devnull, 'w'))

# Function to query individual GPUs and return dict.
def query_gpu(index):
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)
    
    name = pynvml.nvmlDeviceGetName(handle)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    util = utilization.gpu
    mem = utilization.memory
    temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
    power = int(pynvml.nvmlDeviceGetPowerUsage(handle))/1000
    
    return {'gpu_id': index, 'name': name, 'util': util, 'mem': mem, 'temp': temp, 'power': power}

def gpu_section_format(gpu_state):
    gpu_id = gpu_state['gpu_id']
    name = gpu_state['name']
    util = gpu_state['util']
    mem = gpu_state['mem']
    temp = gpu_state['temp']
    power = gpu_state['power']

    return [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*GPU Status*: {}".format(util2emoji(util))
        },
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": 'Util: `{}` {:d}%, Mem: `{}` {:d}%'.format(percentage_bar(util), util, percentage_bar(mem), mem)
        },
    },
    {
        "type": "context",
        "elements": [{
            "type": "plain_text",
            "text": "{} {}, Temp: {:d}C {}, Power: {:.0f}W :electric_plug:".format(id2emoji(gpu_id), name, temp, temp2emoji(temp), power),
        }]
    },
    {
        "type": "divider"
    }]

# Function to query GPUS and return message payload
def query_gpus():
    gpu_state_list = [query_gpu(i) for i in range(device_count)]

    for gpu_state in gpu_state_list:
        logging.debug(gpu_state)

    for gpu_state in gpu_state_list:
        logging.debug(gpu_section_format(gpu_state))


    blocks = []
    blocks.append({
        "type": "header",
        "text": {
          "type": "plain_text",
          "text": f":computer: {hostname}"
        }
      })
    blocks.append(
      {
        "type": "divider"
      })
    
    for gpu_state in gpu_state_list:
        blocks = blocks + gpu_section_format(gpu_state)

    blocks.append(
      {
        "type": "divider"
      })

    return {"blocks": blocks}

@slack_app.command(f"/gpus_{hostname}")
async def command(ack, body, respond):
    await ack()
    logging.debug(body)
    response = query_gpus()
    logging.debug(response)
    await respond(response)

async def main():
    socket_handler = AsyncSocketModeHandler(slack_app, os.environ["SLACK_APP_TOKEN"])
    await socket_handler.start_async()

if __name__ == "__main__":
    import asyncio

    logging.info(f"Started Slack GPU Bot on Host: {hostname}, responding to command: /gpus_{hostname}")
    asyncio.run(main())
