#!/usr/bin/env python3
"""GPU Slack Bot

This script will respond to slack commands of the form "/gpus_<hostname>"
with the current status of GPUs on the host, using the NVML library.

The script requires the following environment variables to be set:
export SLACK_APP_TOKEN=xapp-....
export SLACK_BOT_TOKEN=xoxb-....
"""

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
except pynvml.NVMLError as error:
    logging.error(error)

device_count = pynvml.nvmlDeviceGetCount()

_id_emojis = {0: ':zero:', 1: ':one:', 2: ':two:', 3: ':three:',
              4: ':four', 5: ':five:', 6: ':six:', 7: ':seven:', 8: ':eight:'}


def _id2emoji(gpu_id):
    if gpu_id in _id_emojis:
        return _id_emojis[gpu_id]
    return f"{gpu_id}"


def _util2emoji(util):
    return ':yawning_face:' if util < 20 else ':flushed:' if util < 80 else ':hot_face:'


def _temp2emoji(temp):
    return ':snowflake:' if temp < 60 else ':fire:'


def _percentage_bar(percent):
    # Have to redirect tqdm to output to /dev/null, stderr by default
    return tqdm(total=100, initial=percent, bar_format='|{bar:15}|',
                file=open(os.devnull, 'w', encoding="utf-8"))

# Function to query individual GPUs and return dict.


def _query_gpu(index):
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)

    name = pynvml.nvmlDeviceGetName(handle)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    util = utilization.gpu
    mem = utilization.memory
    temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
    power = int(pynvml.nvmlDeviceGetPowerUsage(handle))/1000

    return {'gpu_id': index, 'name': name, 'util': util, 'mem': mem, 'temp': temp, 'power': power}


def _gpu_section_format(gpu_state):
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
            "text": f"*GPU Status*: {_util2emoji(util)}"
        },
    },
        {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f'Util: `{_percentage_bar(util)}` {util}%, Mem: `{_percentage_bar(mem)}` {mem}%'
        },
    },
        {
        "type": "context",
        "elements": [{
            "type": "plain_text",
            "text": f"{_id2emoji(gpu_id)} {name}, Temp: {temp}C {_temp2emoji(temp)}, "
                    f"Power: {power:.0f}W :electric_plug:"
        }]
    },
        {
        "type": "divider"
    }]


def query_gpus():
    """Function to query GPUS and return slack blocks message.

    Returns
    -------
    dict
        JSON-serializable response to send back to Slack.

    """
    gpu_state_list = [_query_gpu(i) for i in range(device_count)]

    for gpu_state in gpu_state_list:
        logging.debug(gpu_state)

    for gpu_state in gpu_state_list:
        logging.debug(_gpu_section_format(gpu_state))

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
        blocks = blocks + _gpu_section_format(gpu_state)

    blocks.append(
        {
            "type": "divider"
        })

    return {"blocks": blocks}


@slack_app.command(f"/gpus_{hostname}")
async def command(ack, body, respond):
    """Function to respond to slack command query of the form "/gpus_<hostname>".

    Parameters
    -------
    ack : slack acknowledgement function.
    body : slack request body.
    respond : slack response function.
    """
    await ack()
    logging.debug(body)
    response = query_gpus()
    logging.debug(response)
    await respond(response)


async def main():
    """Driver function to start the slack bot.
    """
    socket_handler = AsyncSocketModeHandler(
        slack_app, os.environ["SLACK_APP_TOKEN"])
    await socket_handler.start_async()

if __name__ == "__main__":
    import asyncio

    logging.info(
        "Started Slack GPU Bot on Host: %s, responding to command: /gpus_%s", hostname, hostname)
    asyncio.run(main())
