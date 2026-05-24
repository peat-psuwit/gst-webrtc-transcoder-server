FROM docker.io/library/rust:trixie AS rust-builder

# https://docs.docker.com/reference/dockerfile/#example-cache-apt-packages
RUN \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y libgstreamer-plugins-bad1.0-dev

ADD https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs.git#0.15.2 /usr/src/gst-plugins-rs
WORKDIR /usr/src/gst-plugins-rs

RUN \
    cd net/webrtc && cargo build --release && \
    cd ../../net/rtp && cargo build --release

# Download and unpack deno for the benefit of real container below.
# FIXME: once Podman/Buildah supports ADD --unpack, use that instead.
RUN \
    cd /tmp && \
    wget https://github.com/denoland/deno/releases/download/v2.8.0/deno-x86_64-unknown-linux-gnu.zip && \
    unzip deno-x86_64-unknown-linux-gnu.zip && \
    rm deno-x86_64-unknown-linux-gnu.zip

# Use latest Ubuntu to benefit from newer GStreamer.
FROM docker.io/library/ubuntu:26.04

RUN \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        gstreamer1.0-libav \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-rtp \
        gstreamer1.0-nice \
        gir1.2-gstreamer-1.0 \
        gir1.2-gst-plugins-bad-1.0 \
        python3 \
        # yt-dlp optional dependency
        python3-brotli \
        # server dependency
        python3-gst-1.0 \
        python3-typing-extensions \
        python3-websockets

# Install yt-dlp from official release instead of Ubuntu package, as yt-dlp is
# updated frequently to catch up with YouTube and other services' changes.
ADD --chmod=755 \
    https://github.com/yt-dlp/yt-dlp/releases/download/2026.03.17/yt-dlp \
    /usr/local/bin/

# Install Deno from official binary as there's not Ubuntu package.
# FIXME: once Podman/Buildah supports ADD --unpack, use that instead.
COPY --from=rust-builder --chmod=755 \
    /tmp/deno \
    /usr/local/bin/

COPY --from=rust-builder \
    /usr/src/gst-plugins-rs/target/release/*.so \
    /usr/local/lib/gstreamer-1.0/
ENV GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0

RUN mkdir -p /srv/app/node_gst_transcoder_server
COPY __main__.py /srv/app/
COPY node_gst_transcoder_server/ srv/app/node_gst_transcoder_server/

WORKDIR /srv/app
CMD ["/usr/bin/python3", "__main__.py"]
