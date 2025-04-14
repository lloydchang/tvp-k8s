FROM python:3.10

WORKDIR /app

# Install essential packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    git \
    bash \
    vim \
    less \
    procps \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/stable.txt" && \
    KUBECTL_VERSION=$(cat stable.txt) && \
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl stable.txt

# Install Argo CD CLI
RUN curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64 && \
    install -m 555 argocd-linux-amd64 /usr/local/bin/argocd && \
    rm argocd-linux-amd64

# Create required directories
RUN mkdir -p /home/app/.kube

# Copy requirements and install dependencies
COPY requirements.txt* /app/
RUN if [ -f "requirements.txt" ]; then pip install --no-cache-dir -r requirements.txt; fi

EXPOSE 8000

# This command is crucial - it keeps the container running
CMD ["sleep", "infinity"]