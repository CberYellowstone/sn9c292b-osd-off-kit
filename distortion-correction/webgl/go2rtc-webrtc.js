export class Go2RtcWebRtcClient {
  constructor({ baseUrl, source, video, onStatus, onVideoReady }) {
    this.baseUrl = normalizeHttpBase(baseUrl);
    this.source = source.trim();
    this.video = video;
    this.onStatus = onStatus;
    this.onVideoReady = onVideoReady;
    this.ws = null;
    this.pc = null;
    this.stream = new MediaStream();
    this.closed = false;
  }

  connect() {
    if (!this.source) {
      throw new Error("远端流名称不能为空");
    }

    const wsUrl = this.buildWebSocketUrl();
    this.onStatus(`连接远端流: ${this.source}`);

    this.ws = new WebSocket(wsUrl);
    this.ws.addEventListener("open", () => {
      this.openPeerConnection().catch((error) => {
        this.onStatus(error instanceof Error ? error.message : String(error));
        this.close();
      });
    });
    this.ws.addEventListener("message", (event) => this.handleMessage(event));
    this.ws.addEventListener("close", () => {
      if (!this.closed) {
        this.onStatus("远端流连接已断开");
      }
    });
    this.ws.addEventListener("error", () => {
      this.onStatus("远端 WebSocket 连接失败");
    });
  }

  close() {
    this.closed = true;

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    if (this.pc) {
      for (const sender of this.pc.getSenders()) {
        sender.track?.stop();
      }
      for (const receiver of this.pc.getReceivers()) {
        receiver.track?.stop();
      }
      this.pc.close();
      this.pc = null;
    }

    for (const track of this.stream.getTracks()) {
      track.stop();
    }
    this.stream = new MediaStream();
  }

  buildWebSocketUrl() {
    const url = new URL("/api/ws", this.baseUrl);
    url.searchParams.set("src", this.source);
    url.searchParams.set("media", "video");
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url;
  }

  send(message) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  async openPeerConnection() {
    this.pc = new RTCPeerConnection({
      bundlePolicy: "max-bundle",
      iceServers: [
        { urls: ["stun:stun.cloudflare.com:3478", "stun:stun.l.google.com:19302"] },
      ],
      sdpSemantics: "unified-plan",
    });

    this.pc.addEventListener("icecandidate", (event) => {
      const candidate = event.candidate ? event.candidate.toJSON().candidate : "";
      this.send({ type: "webrtc/candidate", value: candidate });
    });

    this.pc.addEventListener("track", (event) => {
      if (event.track.kind !== "video") {
        return;
      }
      this.stream.addTrack(event.track);
      this.video.srcObject = this.stream;
      this.video.muted = true;
      this.video.play().catch(() => {
        this.video.muted = true;
        this.video.play().catch(() => {});
      });
    });

    this.video.addEventListener(
      "loadedmetadata",
      () => {
        this.onVideoReady(this.video.videoWidth, this.video.videoHeight);
      },
      { once: true },
    );

    this.pc.addEventListener("connectionstatechange", () => {
      switch (this.pc.connectionState) {
        case "connected":
          this.onStatus(`远端流已连接: ${this.source}`);
          break;
        case "failed":
        case "disconnected":
          this.onStatus(`远端流${this.pc.connectionState}`);
          break;
      }
    });

    this.pc.addTransceiver("video", { direction: "recvonly" });
    const offer = await this.pc.createOffer();
    await this.pc.setLocalDescription(offer);
    this.send({ type: "webrtc/offer", value: offer.sdp });
  }

  handleMessage(event) {
    if (typeof event.data !== "string") {
      return;
    }

    const message = JSON.parse(event.data);
    switch (message.type) {
      case "webrtc/answer":
        this.pc?.setRemoteDescription({ type: "answer", sdp: message.value }).catch((error) => {
          console.warn(error);
        });
        break;
      case "webrtc/candidate":
        if (message.value) {
          this.pc?.addIceCandidate({ candidate: message.value, sdpMid: "0" }).catch((error) => {
            console.warn(error);
          });
        }
        break;
      case "error":
        this.onStatus(formatGo2RtcError(message.value));
        break;
    }
  }
}

function formatGo2RtcError(value) {
  const message = value || "远端流错误";
  if (/codecs not matched/i.test(message) && /H265/i.test(message)) {
    return "当前浏览器 WebRTC offer 不包含 H.265，请改用 H.264 流或升级/开启 H.265 WebRTC";
  }
  return message;
}

export function normalizeHttpBase(value) {
  const raw = String(value instanceof URL ? value.href : value).trim();
  if (!raw) {
    throw new Error("go2rtc 地址不能为空");
  }
  const withProtocol = /^[a-z]+:\/\//i.test(raw) ? raw : `http://${raw}`;
  const url = new URL(withProtocol);
  url.pathname = "/";
  url.search = "";
  url.hash = "";
  return url;
}
