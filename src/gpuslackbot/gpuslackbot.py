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

import psutil
import pynvml

from tqdm import tqdm

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

logging.basicConfig(level=logging.INFO)

# Install the Slack app and get xoxb-token in advance
slack_app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# Get basic information about the system/GPUs
hostname = socket.gethostname()

# Initialize PSUtil's non-blocking cpu usage call
psutil.cpu_percent(interval=None)

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
    return tqdm(total=100, initial=percent, bar_format='|{bar:12}|',
                file=open(os.devnull, 'w', encoding="utf-8"))

# Function to query individual GPUs and return dict.


def _query_gpu(index):
    handle = pynvml.nvmlDeviceGetHandleByIndex(index)

    name = pynvml.nvmlDeviceGetName(handle)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    util = utilization.gpu

    meminfo = pynvml.nvmlDeviceGetMemoryInfo(handle)

    gpu_mem_usage = (meminfo.total - meminfo.free)/meminfo.total

    temp = pynvml.nvmlDeviceGetTemperature(handle, 0)
    try:
        power = int(pynvml.nvmlDeviceGetPowerUsage(handle))/1000
    except pynvml.nvml.NVMLError_NotSupported:  # pylint: disable=maybe-no-member
        logging.debug("NVML doesn't support reading the power usage of GPU %i", index)
        power = None
    # Kbps, but want in Mbps
    pciethroughput = pynvml.nvmlDeviceGetPcieThroughput(handle, 0)/1024
    # in Mbps
    pciemaxspeed = pynvml.nvmlDeviceGetPcieSpeed(handle)
    pciemaxlink = pynvml.nvmlDeviceGetMaxPcieLinkWidth(handle)
    pciemaxgen = pynvml.nvmlDeviceGetMaxPcieLinkGeneration(handle)

    return {'gpu_id': index, 'name': name, 'util': util, 'mem': round(gpu_mem_usage*100), 
            'temp': temp, 'power': power, 'pciethroughput': pciethroughput,
            'pciemaxspeed': pciemaxspeed, 'pciemaxlink': pciemaxlink,
            'pciemaxgen': pciemaxgen, 'memtotal': meminfo.total}


def _gpu_section_format(gpu_state):
    gpu_id = gpu_state['gpu_id']
    name = gpu_state['name']
    util = gpu_state['util']
    mem = gpu_state['mem']
    temp = gpu_state['temp']
    power = gpu_state['power']
    # Memory total in GB
    memtotal = ((gpu_state['memtotal']/1024)/1024)/1024

    pciethroughput = gpu_state['pciethroughput']
    pciemaxspeed = gpu_state['pciemaxspeed']
    pciemaxlink = gpu_state['pciemaxlink']
    pciemaxgen = gpu_state['pciemaxgen']
    pciepercent = int(round((100*pciethroughput)/pciemaxspeed))

    # Some GPUs don't support power reading
    powerstring = f", Power: {power:.0f}W :electric_plug:" if power else ""

    return [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"{_id2emoji(gpu_id)} Util: `{_percentage_bar(util)}` {util:.0f}%"
                    f", Mem: `{_percentage_bar(mem)}` {mem:.0f}%"
                    f", PCIe: `{_percentage_bar(pciepercent)}`"
                    f" {pciethroughput:.0f} Mbps"
        },
    },
        {
        "type": "context",
        "elements": [{
            "type": "plain_text",
            "text": f"{name} {memtotal:.0f}GB, Temp: {temp:d}C {_temp2emoji(temp)}" +
                    powerstring +
                    f", PCIe {pciemaxgen} x{pciemaxlink}"
        }]
    }]

def _all_gpu_short_status_format(gpu_state_list):
    emoji_list = [f"{_id2emoji(gpu_state['gpu_id'])} {_util2emoji(gpu_state['util'])}"
                    for gpu_state in gpu_state_list]

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*GPU Status Summary*: {''.join(emoji_list)}"
        },
    }


def query_cpus():
    """Function to query CPU(s) and return slack blocks message.

    Returns
    -------
    list[dict
        list of JSON-serializable response blocks to send back to Slack.

    """
    cpu_usage = psutil.cpu_percent(interval=None)
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    mem = psutil.virtual_memory()
    mem_usage = (mem.total - mem.available)/mem.total
    total_mem_gb = ((mem.total/1024)/1024)/1024

    return [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"CPU Usage: `{_percentage_bar(cpu_usage)}` {cpu_usage:.0f}%"
                    f", Mem: `{_percentage_bar(mem_usage)}` {mem_usage:.0f}%"
        },
    },
    {
        "type": "context",
        "elements": [{
            "type": "plain_text",
            "text": f"{physical_cores} cores ({logical_cores} logical), {total_mem_gb:.0f}GB RAM"
        }]
    }]


def query_users():
    """Function to query active users and return slack blocks message.

    Returns
    -------
    dict
        JSON-serializable response to send back to Slack.

    """
    users = set((user.name for user in psutil.users()))

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Active Users*: {', '.join(users) if users else '*None*'}"
        },
    }


def query_gpus():
    """Function to query GPUS and return slack blocks message.

    Returns
    -------
    dict
        JSON-serializable response to send back to Slack.

    """
    gpu_state_list = [_query_gpu(i) for i in range(device_count)]

    blocks = []
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f":computer: {hostname}"
        }
      })
    blocks = blocks + query_cpus()
    blocks.append(_all_gpu_short_status_format(gpu_state_list))
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
    blocks.append(query_users())
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
