import { Go2RtcWebRtcClient, normalizeHttpBase } from "./go2rtc-webrtc.js";

const MODEL = {
  name: "fisheye_kannala_brandt_4",
  imageSize: [1920, 1080],
  K: [994.9971032102981, 994.4029012066164, 964.9142904632592, 537.2073189018432],
  D: [
    -0.054103821798074554,
    -0.04128019290365484,
    0.030639291846282588,
    -0.01163989139853635,
  ],
  newKBalance0: [873.6835814068628, 873.1618265866922, 975.2957609735381, 535.9327155367041],
  newKBalance1: [537.6759174037791, 537.3548228936323, 969.4132046073167, 537.4969417399109],
};

const PRESETS = {
  wide: { balance: 1.0, zoom: 1.02 },
  crop: { balance: 1.0, zoom: 1.62 },
};

const FRAGMENT_SHADER_URL = "./shaders/fisheye_kb4.frag.glsl";

const vertexSource = `#version 300 es
in vec2 aPosition;
in vec2 aTexCoord;
out vec2 vTexCoord;

void main() {
  vTexCoord = aTexCoord;
  gl_Position = vec4(aPosition, 0.0, 1.0);
}
`;

const ui = {
  canvas: document.querySelector("#preview"),
  video: document.querySelector("#sourceVideo"),
  startButton: document.querySelector("#startButton"),
  hideToolbarButton: document.querySelector("#hideToolbarButton"),
  showToolbarButton: document.querySelector("#showToolbarButton"),
  remoteBase: document.querySelector("#remoteBase"),
  remoteSource: document.querySelector("#remoteSource"),
  remoteStreamSelect: document.querySelector("#remoteStreamSelect"),
  remoteRefreshButton: document.querySelector("#remoteRefreshButton"),
  remoteConnectButton: document.querySelector("#remoteConnectButton"),
  cameraSelect: document.querySelector("#cameraSelect"),
  status: document.querySelector("#status"),
  balance: document.querySelector("#balance"),
  balanceValue: document.querySelector("#balanceValue"),
  zoom: document.querySelector("#zoom"),
  zoomValue: document.querySelector("#zoomValue"),
  fpsCap: document.querySelector("#fpsCap"),
  fpsCapValue: document.querySelector("#fpsCapValue"),
  fps: document.querySelector("#fps"),
  resolution: document.querySelector("#resolution"),
  presetButtons: [...document.querySelectorAll("[data-preset]")],
};

let gl;
let program;
let videoTexture;
let currentStream = null;
let sourceElement = null;
let sampleMode = false;
let lastDrawMs = 0;
let frames = 0;
let fpsWindowStart = performance.now();
let selectedDeviceId = "";
let remoteClient = null;
let videoRenderTimer = 0;

function setStatus(message) {
  ui.status.textContent = message;
}

function compileShader(type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader) || "shader compile failed");
  }
  return shader;
}

function createProgram(fragmentSource) {
  const vertex = compileShader(gl.VERTEX_SHADER, vertexSource);
  const fragment = compileShader(gl.FRAGMENT_SHADER, fragmentSource);
  const linked = gl.createProgram();
  gl.attachShader(linked, vertex);
  gl.attachShader(linked, fragment);
  gl.linkProgram(linked);
  if (!gl.getProgramParameter(linked, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(linked) || "program link failed");
  }
  return linked;
}

async function loadShaderSource(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`加载 GLSL 失败: ${response.status} ${url}`);
  }
  return response.text();
}

function initGl(fragmentSource) {
  gl = ui.canvas.getContext("webgl2", {
    alpha: false,
    antialias: false,
    depth: false,
    stencil: false,
    preserveDrawingBuffer: false,
  });
  if (!gl) {
    throw new Error("WebGL2 不可用");
  }

  program = createProgram(fragmentSource);
  gl.useProgram(program);

  const vertices = new Float32Array([
    -1, -1, 0, 1,
     1, -1, 1, 1,
    -1,  1, 0, 0,
     1,  1, 1, 0,
  ]);
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);

  const stride = 4 * Float32Array.BYTES_PER_ELEMENT;
  const positionLoc = gl.getAttribLocation(program, "aPosition");
  const texCoordLoc = gl.getAttribLocation(program, "aTexCoord");
  gl.enableVertexAttribArray(positionLoc);
  gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, stride, 0);
  gl.enableVertexAttribArray(texCoordLoc);
  gl.vertexAttribPointer(texCoordLoc, 2, gl.FLOAT, false, stride, 2 * Float32Array.BYTES_PER_ELEMENT);

  videoTexture = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, videoTexture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.uniform1i(gl.getUniformLocation(program, "uVideo"), 0);

  gl.viewport(0, 0, ui.canvas.width, ui.canvas.height);
  gl.uniform2f(gl.getUniformLocation(program, "uOutputSize"), ui.canvas.width, ui.canvas.height);
  gl.uniform2f(gl.getUniformLocation(program, "uInputSize"), MODEL.imageSize[0], MODEL.imageSize[1]);
  gl.uniform4fv(gl.getUniformLocation(program, "uD"), MODEL.D);
  updateKForInput(MODEL.imageSize[0], MODEL.imageSize[1]);
  updateNewK();
}

function interpolateParams(a, b, t) {
  return a.map((value, index) => value + (b[index] - value) * t);
}

function updateKForInput(width, height) {
  if (!gl || !program) {
    return;
  }
  const scaleX = width / MODEL.imageSize[0];
  const scaleY = height / MODEL.imageSize[1];
  const scaled = [
    MODEL.K[0] * scaleX,
    MODEL.K[1] * scaleY,
    MODEL.K[2] * scaleX,
    MODEL.K[3] * scaleY,
  ];
  gl.useProgram(program);
  gl.uniform2f(gl.getUniformLocation(program, "uInputSize"), width, height);
  gl.uniform4fv(gl.getUniformLocation(program, "uK"), scaled);
}

function updateNewK() {
  if (!gl || !program) {
    return;
  }
  const balance = Number(ui.balance.value);
  const zoom = Number(ui.zoom.value);
  const matrix = interpolateParams(MODEL.newKBalance0, MODEL.newKBalance1, balance);
  matrix[0] *= zoom;
  matrix[1] *= zoom;
  gl.useProgram(program);
  gl.uniform4fv(gl.getUniformLocation(program, "uNewK"), matrix);
  ui.balanceValue.textContent = balance.toFixed(2);
  ui.zoomValue.textContent = zoom.toFixed(2);
  updatePresetState(balance, zoom);
}

function renderFrame(now) {
  if (!sourceElement) {
    return;
  }
  if (!sampleMode && ui.video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    return;
  }

  const fpsCap = Number(ui.fpsCap.value);
  const minInterval = 1000 / Math.max(1, fpsCap);
  if (now - lastDrawMs < minInterval) {
    return;
  }
  lastDrawMs = now;

  gl.activeTexture(gl.TEXTURE0);
  gl.bindTexture(gl.TEXTURE_2D, videoTexture);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, sourceElement);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

  frames += 1;
  if (now - fpsWindowStart >= 1000) {
    ui.fps.textContent = `draw fps: ${frames}`;
    frames = 0;
    fpsWindowStart = now;
  }
}

function ensureVideoFrameLoop() {
  if (videoRenderTimer) {
    return;
  }

  videoRenderTimer = window.setInterval(() => {
    if (sourceElement !== ui.video) {
      stopVideoFrameLoop();
      return;
    }
    renderFrame(performance.now());
  }, 1000 / 60);
}

function stopVideoFrameLoop() {
  if (!videoRenderTimer) {
    return;
  }
  window.clearInterval(videoRenderTimer);
  videoRenderTimer = 0;
}

function isCloseEnough(a, b) {
  return Math.abs(a - b) < 0.005;
}

function updatePresetState(balance = Number(ui.balance.value), zoom = Number(ui.zoom.value)) {
  for (const button of ui.presetButtons) {
    const preset = PRESETS[button.dataset.preset];
    const active = preset && isCloseEnough(balance, preset.balance) && isCloseEnough(zoom, preset.zoom);
    button.classList.toggle("active", Boolean(active));
  }
}

function applyPreset(name) {
  const preset = PRESETS[name];
  if (!preset) {
    return;
  }
  ui.balance.value = String(preset.balance);
  ui.zoom.value = String(preset.zoom);
  updateNewK();
}

function disconnectRemote() {
  if (!remoteClient) {
    return;
  }
  remoteClient.close();
  remoteClient = null;
}

function setToolbarHidden(hidden) {
  document.body.classList.toggle("toolbar-hidden", hidden);
  ui.hideToolbarButton.setAttribute("aria-expanded", String(!hidden));
  ui.showToolbarButton.setAttribute("aria-expanded", String(!hidden));
}

function toggleToolbar() {
  setToolbarHidden(!document.body.classList.contains("toolbar-hidden"));
}

function shouldHandleToolbarShortcut(event) {
  const target = event.target;
  return !(target instanceof HTMLInputElement || target instanceof HTMLSelectElement);
}

function hasLocalCameraApi() {
  return Boolean(navigator.mediaDevices?.getUserMedia);
}

async function listCameras() {
  ui.cameraSelect.replaceChildren();

  if (!navigator.mediaDevices?.enumerateDevices) {
    ui.cameraSelect.appendChild(new Option("本机摄像头不可用", ""));
    ui.cameraSelect.disabled = true;
    ui.startButton.disabled = true;
    return [];
  }

  const devices = await navigator.mediaDevices.enumerateDevices();
  const videoDevices = devices.filter((device) => device.kind === "videoinput");
  for (const [index, device] of videoDevices.entries()) {
    const option = document.createElement("option");
    option.value = device.deviceId;
    option.textContent = device.label || `camera ${index + 1}`;
    ui.cameraSelect.appendChild(option);
  }
  ui.cameraSelect.disabled = false;
  ui.startButton.disabled = !hasLocalCameraApi();
  if (selectedDeviceId) {
    ui.cameraSelect.value = selectedDeviceId;
  }
  return videoDevices;
}

function stopStream() {
  disconnectRemote();
  stopVideoFrameLoop();
  if (!currentStream) {
    ui.video.srcObject = null;
    sourceElement = null;
    sampleMode = false;
    return;
  }
  for (const track of currentStream.getTracks()) {
    track.stop();
  }
  currentStream = null;
  ui.video.srcObject = null;
  sourceElement = null;
  sampleMode = false;
}

async function openCamera(deviceId = "") {
  stopStream();
  const videoConstraints = {
    width: { ideal: MODEL.imageSize[0] },
    height: { ideal: MODEL.imageSize[1] },
    frameRate: { ideal: 30, max: 60 },
  };
  if (deviceId) {
    videoConstraints.deviceId = { exact: deviceId };
  }

  currentStream = await navigator.mediaDevices.getUserMedia({
    video: videoConstraints,
    audio: false,
  });
  ui.video.srcObject = currentStream;
  await ui.video.play();
  sourceElement = ui.video;
  sampleMode = false;
  ensureVideoFrameLoop();

  const [track] = currentStream.getVideoTracks();
  selectedDeviceId = track.getSettings().deviceId || deviceId;
  const settings = track.getSettings();
  ui.resolution.textContent = `source: ${settings.width || "--"}x${settings.height || "--"} @ ${settings.frameRate || "--"}fps`;
  updateKForInput(ui.video.videoWidth || settings.width || MODEL.imageSize[0], ui.video.videoHeight || settings.height || MODEL.imageSize[1]);
  setStatus(track.label || "摄像头已启动");
  await listCameras();

  const usbOption = [...ui.cameraSelect.options].find((option) => /usb camera/i.test(option.textContent));
  if (!deviceId && usbOption && selectedDeviceId !== usbOption.value) {
    selectedDeviceId = usbOption.value;
    ui.cameraSelect.value = selectedDeviceId;
    await openCamera(selectedDeviceId);
  }
}

function handleRemoteVideoReady(width, height) {
  const sourceWidth = width || MODEL.imageSize[0];
  const sourceHeight = height || MODEL.imageSize[1];
  sourceElement = ui.video;
  sampleMode = false;
  ensureVideoFrameLoop();
  updateKForInput(sourceWidth, sourceHeight);
  ui.resolution.textContent = `source: ${sourceWidth}x${sourceHeight} remote`;
}

async function refreshRemoteStreams() {
  const baseUrl = normalizeHttpBase(ui.remoteBase.value);
  ui.remoteBase.value = baseUrl.href.replace(/\/$/, "");
  const url = new URL("/api/streams", baseUrl);
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`刷新远端流失败: HTTP ${response.status}`);
  }

  const streams = await response.json();
  const current = ui.remoteSource.value;
  const streamNames = Object.keys(streams)
    .filter((name) => !name.endsWith("_mjpeg_source"))
    .sort();
  ui.remoteStreamSelect.replaceChildren(new Option("远端流", ""));
  for (const name of streamNames) {
    ui.remoteStreamSelect.appendChild(new Option(name, name));
  }
  ui.remoteStreamSelect.value = streamNames.includes(current) ? current : "";
  setStatus(`远端流: ${streamNames.length}`);
}

async function connectRemoteStream() {
  try {
    stopStream();
    const baseUrl = normalizeHttpBase(ui.remoteBase.value);
    ui.remoteBase.value = baseUrl.href.replace(/\/$/, "");
    const source = ui.remoteSource.value.trim();
    remoteClient = new Go2RtcWebRtcClient({
      baseUrl,
      source,
      video: ui.video,
      onStatus: setStatus,
      onVideoReady: handleRemoteVideoReady,
    });
    remoteClient.connect();
  } catch (error) {
    console.error(error);
    setStatus(error instanceof Error ? error.message : String(error));
  }
}

function draw(now) {
  requestAnimationFrame(draw);
  if (sourceElement === ui.video && videoRenderTimer) {
    return;
  }
  renderFrame(now);
}

async function start() {
  try {
    if (!hasLocalCameraApi()) {
      setStatus("本机摄像头需要 HTTPS 或 localhost；当前地址可使用远端流");
      return;
    }
    setStatus("请求摄像头权限");
    await openCamera(ui.cameraSelect.value || "");
  } catch (error) {
    console.error(error);
    setStatus(error instanceof Error ? error.message : String(error));
  }
}

function wireUi() {
  ui.startButton.addEventListener("click", start);
  ui.hideToolbarButton.addEventListener("click", () => setToolbarHidden(true));
  ui.showToolbarButton.addEventListener("click", () => setToolbarHidden(false));
  ui.remoteRefreshButton.addEventListener("click", () => {
    refreshRemoteStreams().catch((error) => {
      console.error(error);
      const message = error instanceof Error ? error.message : String(error);
      setStatus(message === "Failed to fetch" ? "刷新失败: go2rtc 未开放 CORS，可直接输入 src 连接" : message);
    });
  });
  ui.remoteStreamSelect.addEventListener("change", () => {
    if (ui.remoteStreamSelect.value) {
      ui.remoteSource.value = ui.remoteStreamSelect.value;
    }
  });
  ui.remoteConnectButton.addEventListener("click", connectRemoteStream);
  document.addEventListener("keydown", (event) => {
    if (event.key.toLowerCase() === "h" && shouldHandleToolbarShortcut(event)) {
      toggleToolbar();
    }
  });
  ui.cameraSelect.addEventListener("change", () => {
    selectedDeviceId = ui.cameraSelect.value;
    start();
  });
  ui.balance.addEventListener("input", updateNewK);
  ui.zoom.addEventListener("input", updateNewK);
  for (const button of ui.presetButtons) {
    button.addEventListener("click", () => applyPreset(button.dataset.preset));
  }
  ui.fpsCap.addEventListener("input", () => {
    ui.fpsCapValue.textContent = ui.fpsCap.value;
  });
}

async function main() {
  setStatus("加载 GLSL");
  const fragmentSource = await loadShaderSource(FRAGMENT_SHADER_URL);
  initGl(fragmentSource);
  wireUi();
  await listCameras();
  requestAnimationFrame(draw);
  if (hasLocalCameraApi()) {
    setStatus("点击启动摄像头，或连接远端流");
  } else {
    setStatus("当前地址不是安全上下文，本机摄像头不可用；可连接远端流");
  }
}

main().catch((error) => {
  console.error(error);
  setStatus(error instanceof Error ? error.message : String(error));
});
