FROM ubuntu:noble

RUN rm -f /etc/apt/sources.list.d/ubuntu.sources && \
    echo "deb http://mirror-linux.runflare.com/ubuntu noble main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb http://mirror-linux.runflare.com/ubuntu noble-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://mirror-linux.runflare.com/ubuntu noble-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://mirror-linux.runflare.com/ubuntu noble-security main restricted universe multiverse" >> /etc/apt/sources.list

COPY apt-packages.txt /tmp/apt-packages.txt

RUN apt update && \
    xargs -a /tmp/apt-packages.txt apt install -y && \
    apt clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
