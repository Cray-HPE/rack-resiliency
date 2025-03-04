FROM --platform=linux/amd64 python:3.9-slim as build
# Use the SLES base image
FROM registry.suse.com/suse/sle15:latest

# Set environment variables
ENV KUBECTL_VERSION=v1.28.0

# Update package manager and install necessary dependencies
RUN zypper refresh && \
    zypper install -y curl ca-certificates python3 python3-pip openssh && \
    zypper clean && \
    update-ca-certificates

# Install kubectl securely
RUN curl --insecure -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/kubectl

RUN zypper --non-interactive install vim
RUN pip install kubernetes
# RUN zypper --non-interactive install python3-rados
RUN pip install flask
# RUN pip install flask-cors
RUN zypper --non-interactive install iputils

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
CMD bash -c "/usr/sbin/sshd && flask run --host=0.0.0.0 --port=80"