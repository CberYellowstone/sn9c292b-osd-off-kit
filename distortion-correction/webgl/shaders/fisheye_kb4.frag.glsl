#version 300 es
precision highp float;

uniform sampler2D uVideo;
uniform vec2 uOutputSize;
uniform vec2 uInputSize;
uniform vec4 uK;
uniform vec4 uNewK;
uniform vec4 uD;

in vec2 vTexCoord;
out vec4 outColor;

void main() {
  vec2 pixel = vec2(vTexCoord.x * uOutputSize.x, vTexCoord.y * uOutputSize.y);
  float x = (pixel.x - uNewK.z) / uNewK.x;
  float y = (pixel.y - uNewK.w) / uNewK.y;
  float r = length(vec2(x, y));

  float scale = 1.0;
  if (r > 0.000001) {
    float theta = atan(r);
    float theta2 = theta * theta;
    float theta4 = theta2 * theta2;
    float theta6 = theta4 * theta2;
    float theta8 = theta4 * theta4;
    float thetaD = theta * (
      1.0
      + uD.x * theta2
      + uD.y * theta4
      + uD.z * theta6
      + uD.w * theta8
    );
    scale = thetaD / r;
  }

  vec2 distorted = vec2(x * scale, y * scale);
  vec2 sourcePixel = vec2(
    uK.x * distorted.x + uK.z,
    uK.y * distorted.y + uK.w
  );
  vec2 uv = sourcePixel / uInputSize;

  if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
    outColor = vec4(0.0, 0.0, 0.0, 1.0);
    return;
  }

  outColor = texture(uVideo, uv);
}
