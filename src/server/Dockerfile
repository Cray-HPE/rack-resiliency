#
# MIT License
#
# (C) Copyright [2024-2025] Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#

FROM alpine:latest

# Update package manager and install necessary dependencies
RUN apk update && \
    apk add --no-cache curl ca-certificates python3 py3-pip openssh && \
    update-ca-certificates

# Create and activate a virtual environment
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install Python packages within the virtual environment
RUN pip3 install kubernetes flask

# Enable and start SSH service
RUN mkdir -p /var/run/sshd && echo "PermitRootLogin yes" >> /etc/ssh/sshd_config

# Set the working directory in the container
WORKDIR /src/server

# Copy the current directory contents into the container
COPY . .

EXPOSE 80 22

# Set Flask environment variable
ENV FLASK_APP=app.py

# Start SSH and Flask app
CMD /usr/sbin/sshd && flask run --host=0.0.0.0 --port=80