FROM nvcr.io/nvidia/pytorch:23.02-py3

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --user -r /tmp/requirements.txt