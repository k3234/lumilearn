# -*- coding: utf-8 -*-
"""
framework/services/interactive_scene.py
交互模拟场景生成器
生成基于 HTML Canvas 的交互式数学学习场景
"""
import logging

logger = logging.getLogger(__name__)


class InteractiveSceneGenerator:
    """交互模拟场景生成器：生成勾股定理、三角函数、直线方程等交互 HTML"""

    def generate_pythagorean_theorem(self) -> str:
        """
        生成勾股定理交互 HTML
        学生可拖动直角三角形顶点改变形状，实时显示三边长度并验证 a² + b² = c²
        """
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>勾股定理交互探索</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f0f4f8; color: #2d3748; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; }
  h1 { font-size: 1.6rem; margin-bottom: 16px; color: #1a365d; }
  .container { background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 24px; max-width: 700px; width: 100%; }
  canvas { display: block; margin: 0 auto 20px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; cursor: crosshair; max-width: 100%; }
  .info-panel { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-bottom: 16px; }
  .info-card { background: #edf2f7; border-radius: 8px; padding: 12px 18px; text-align: center; min-width: 120px; }
  .info-card .label { font-size: 0.85rem; color: #718096; margin-bottom: 4px; }
  .info-card .value { font-size: 1.3rem; font-weight: 700; color: #2b6cb0; }
  .formula-box { background: #ebf8ff; border: 2px solid #90cdf4; border-radius: 8px; padding: 16px; text-align: center; }
  .formula-box .formula { font-size: 1.4rem; font-weight: 700; color: #1a365d; margin-bottom: 8px; }
  .formula-box .verify { font-size: 1rem; color: #276749; }
  .formula-box .verify.error { color: #c53030; }
  .hint { font-size: 0.85rem; color: #a0aec0; text-align: center; margin-top: 8px; }
</style>
</head>
<body>
<div class="container">
  <h1>&#x52FE8326;&#x80B1;&#x5B9A;&#x7406;&#x4EA4;&#x4E92;&#x63A2;&#x7D22;</h1>
  <canvas id="canvas" width="600" height="420"></canvas>
  <div class="info-panel">
    <div class="info-card"><div class="label">&#x8FB9 a (&#x6C34;&#x5E73;)</div><div class="value" id="va">-</div></div>
    <div class="info-card"><div class="label">&#x8FB9 b (&#x7AD6;&#x76F4;)</div><div class="value" id="vb">-</div></div>
    <div class="info-card"><div class="label">&#x659C;&#x8FB9 c</div><div class="value" id="vc">-</div></div>
  </div>
  <div class="formula-box">
    <div class="formula" id="formula">&#x52FE8326;&#xFF1A; a&#178; + b&#178; = c&#178;</div>
    <div class="verify" id="verify">&#x8BF7;&#x62D6;&#x52A8;&#x4E09;&#x89D2;&#x5F62;&#x7684;&#x9876;&#x70B9;</div>
  </div>
  <div class="hint">&#x63D0;&#x793A;&#xFF1A;&#x62D6;&#x52A8;&#x7EFF;&#x8272;&#x9876;&#x70B9;&#x53EF;&#x6539;&#x53D8;&#x4E09;&#x89D2;&#x5F62;&#x5F62;&#x72B6;</div>
</div>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const BASE_X = 80, BASE_Y = 360, RIGHT_X = 420, RIGHT_Y = 360;
let topX = 420, topY = 100;
let dragging = null;
const TOP_COLOR = '#38A169';
const BASE_COLOR = '#3182CE';
const VERT_COLOR = '#D97706';
const HYP_COLOR = '#E53E3E';

function dist(x1,y1,x2,y2){ return Math.sqrt((x2-x1)**2+(y2-y1)**2); }

function toMathLen(px){
  return (px / 200).toFixed(2);
}

function render(){
  ctx.clearRect(0,0,600,420);
  // grid
  ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
  for(let x=0;x<600;x+=20){ ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,420); ctx.stroke(); }
  for(let y=0;y<420;y+=20){ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(600,y); ctx.stroke(); }

  const ax=BASE_X, ay=BASE_Y, bx=RIGHT_X, by=RIGHT_Y, cx2=topX, cy=topY;
  const aLen = dist(ax,ay,bx,by);
  const bLen = dist(bx,by,cx2,cy);
  const cLen = dist(cx2,cy,ax,ay);

  // draw triangle
  ctx.beginPath();
  ctx.moveTo(ax,ay); ctx.lineTo(bx,by); ctx.lineTo(cx2,cy); ctx.closePath();
  ctx.fillStyle = 'rgba(66,153,225,0.1)'; ctx.fill();
  ctx.strokeStyle = '#2B6CB0'; ctx.lineWidth = 2; ctx.stroke();

  // right angle marker
  const mark = 15;
  ctx.strokeStyle = '#4A5568'; ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(bx-mark, by); ctx.lineTo(bx-mark, by-mark); ctx.lineTo(bx, by-mark);
  ctx.stroke();

  // label sides
  ctx.font = 'bold 14px Microsoft YaHei';
  ctx.fillStyle = BASE_COLOR;
  ctx.fillText('a', (ax+bx)/2+6, ay+18);
  ctx.fillStyle = VERT_COLOR;
  ctx.fillText('b', bx+6, (by+cy)/2);
  ctx.fillStyle = HYP_COLOR;
  ctx.fillText('c', (ax+cx2)/2-20, (ay+cy)/2+6);

  // vertices
  drawDot(ax,ay,'#4A5568','A');
  drawDot(bx,by,'#4A5568','B');
  drawDot(cx2,cy,TOP_COLOR,'C');

  // lengths
  document.getElementById('va').textContent = toMathLen(aLen);
  document.getElementById('vb').textContent = toMathLen(bLen);
  document.getElementById('vc').textContent = toMathLen(cLen);

  // verify
  const a2 = (aLen/200)**2, b2 = (bLen/200)**2, c2 = (cLen/200)**2;
  const sum = a2 + b2;
  const diff = Math.abs(sum - c2);
  const verifyEl = document.getElementById('verify');
  const formulaEl = document.getElementById('formula');
  formulaEl.textContent = 'a\u00B2 + b\u00B2 = c\u00B2  =>  '
    + sum.toFixed(4) + ' ' + (diff < 0.01 ? '\u2248 ' + c2.toFixed(4) : '\u2260 ' + c2.toFixed(4));
  verifyEl.textContent = diff < 0.01 ? '\u2705 a\u00B2 + b\u00B2 \u2248 c\u00B2 \u6210\u7ACB' : '\u274C \u503C\u504F\u5DEE\u8F83\u5927';
  verifyEl.className = 'verify' + (diff < 0.01 ? '' : ' error');
}

function drawDot(x,y,color,label){
  ctx.beginPath(); ctx.arc(x,y,6,0,Math.PI*2);
  ctx.fillStyle = color; ctx.fill();
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
  ctx.font = 'bold 13px Microsoft YaHei'; ctx.fillStyle = '#1A365D';
  ctx.fillText(label, x+8, y-6);
}

canvas.addEventListener('mousedown', e => {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width, scaleY = canvas.height / rect.height;
  const mx = (e.clientX-rect.left)*scaleX, my = (e.clientY-rect.top)*scaleY;
  if(dist(mx,my,topX,topY)<20) dragging = 'top';
});
canvas.addEventListener('mousemove', e => {
  if(!dragging) return;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width, scaleY = canvas.height / rect.height;
  topX = Math.max(100, Math.min(580, (e.clientX-rect.left)*scaleX));
  topY = Math.max(20, Math.min(350, (e.clientY-rect.top)*scaleY));
  render();
});
canvas.addEventListener('mouseup', () => { dragging = null; });
canvas.addEventListener('mouseleave', () => { dragging = null; });

render();
</script>
</body>
</html>'''

    def generate_trig_function(self) -> str:
        """
        生成三角函数图像交互 HTML
        学生可通过滑块调整振幅(A)、角频率(ω)、相位(φ)，实时观察 y = A·sin(ωx + φ) 图像变化
        """
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>三角函数交互探索</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f0f4f8; color: #2d3748; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; }
  h1 { font-size: 1.6rem; margin-bottom: 16px; color: #1a365d; }
  .container { background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 24px; max-width: 800px; width: 100%; }
  canvas { display: block; margin: 0 auto 20px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; max-width: 100%; }
  .controls { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin-bottom: 16px; }
  .control-group { background: #edf2f7; border-radius: 8px; padding: 14px 18px; min-width: 200px; flex: 1; }
  .control-group label { display: block; font-weight: 600; margin-bottom: 8px; color: #2d3748; }
  .control-group input[type=range] { width: 100%; cursor: pointer; }
  .control-group .val { float: right; font-weight: 700; color: #2b6cb0; }
  .formula-box { background: #ebf8ff; border: 2px solid #90cdf4; border-radius: 8px; padding: 16px; text-align: center; }
  .formula-box .formula { font-size: 1.3rem; font-weight: 700; color: #1a365d; }
  .hint { font-size: 0.85rem; color: #a0aec0; text-align: center; margin-top: 8px; }
</style>
</head>
<body>
<div class="container">
  <h1>&#x4E09;&#x89D2;&#x51FD;&#x6570;&#x4EA4;&#x4E92;&#x63A2;&#x7D22;</h1>
  <canvas id="canvas" width="700" height="350"></canvas>
  <div class="controls">
    <div class="control-group">
      <label>&#x632F;&#x5E45 A <span class="val" id="valA">1.00</span></label>
      <input type="range" id="sliderA" min="0.1" max="5" step="0.1" value="1">
    </div>
    <div class="control-group">
      <label>&#x89D2;&#x9891;&#x7387 &#x03C9 <span class="val" id="valW">1.00</span></label>
      <input type="range" id="sliderW" min="0.1" max="5" step="0.1" value="1">
    </div>
    <div class="control-group">
      <label>&#x76F8;&#x4F4D; &#x03C6 <span class="val" id="valP">0.00</span></label>
      <input type="range" id="sliderP" min="-3.14" max="3.14" step="0.01" value="0">
    </div>
  </div>
  <div class="formula-box">
    <div class="formula" id="formula">y = 1.00 &middot; sin(1.00x + 0.00)</div>
  </div>
  <div class="hint">&#x63D0;&#x793A;&#xFF1A;&#x62D6;&#x52A8;&#x6EDA;&#x52A8;&#x6761;&#x89C2;&#x5BDF;&#x56FE;&#x50CF;&#x53D8;&#x5316;</div>
</div>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;
const originX = 60, originY = H / 2;
const scaleX = 80, scaleY = 60;

function drawGrid(){
  ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
  for(let x=originX; x<W; x+=scaleX){ ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }
  for(let y=originY; y<H; y+=scaleY){ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }
  // axes
  ctx.strokeStyle = '#4A5568'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(originX, originY); ctx.lineTo(W-10, originY); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(originX, 10); ctx.lineTo(originX, H-10); ctx.stroke();
  ctx.font = '12px Microsoft YaHei'; ctx.fillStyle = '#4A5568';
  ctx.fillText('x', W-20, originY-6);
  ctx.fillText('y', originX+6, 14);
  ctx.fillText('0', originX-10, originY+16);
}

function render(){
  const A = parseFloat(document.getElementById('sliderA').value);
  const W2 = parseFloat(document.getElementById('sliderW').value);
  const P = parseFloat(document.getElementById('sliderP').value);
  document.getElementById('valA').textContent = A.toFixed(2);
  document.getElementById('valW').textContent = W2.toFixed(2);
  document.getElementById('valP').textContent = P.toFixed(2);
  document.getElementById('formula').textContent =
    'y = ' + A.toFixed(2) + ' &middot; sin(' + W2.toFixed(2) + 'x + ' + P.toFixed(2) + ')';

  ctx.clearRect(0,0,W,H);
  drawGrid();

  ctx.strokeStyle = '#E53E3E'; ctx.lineWidth = 2.5;
  ctx.beginPath();
  let first = true;
  for(let px=0; px<W; px++){
    const x = (px - originX) / scaleX;
    const y = A * Math.sin(W2 * x + P);
    const py = originY - y * scaleY;
    if(first){ ctx.moveTo(px, py); first = false; }
    else ctx.lineTo(px, py);
  }
  ctx.stroke();

  // amplitude indicator
  ctx.strokeStyle = 'rgba(49,130,206,0.4)'; ctx.lineWidth = 1; ctx.setLineDash([4,4]);
  ctx.beginPath(); ctx.moveTo(originX, originY - A*scaleY); ctx.lineTo(W, originY - A*scaleY); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(originX, originY + A*scaleY); ctx.lineTo(W, originY + A*scaleY); ctx.stroke();
  ctx.setLineDash([]);
}

document.getElementById('sliderA').addEventListener('input', render);
document.getElementById('sliderW').addEventListener('input', render);
document.getElementById('sliderP').addEventListener('input', render);
render();
</script>
</body>
</html>'''

    def generate_line_equation(self) -> str:
        """
        生成直线方程交互 HTML
        学生可通过滑块调整斜率(k)和截距(b)，实时观察 y = kx + b 直线变化
        """
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>直线方程交互探索</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f0f4f8; color: #2d3748; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 20px; }
  h1 { font-size: 1.6rem; margin-bottom: 16px; color: #1a365d; }
  .container { background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 24px; max-width: 700px; width: 100%; }
  canvas { display: block; margin: 0 auto 20px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fafbfc; max-width: 100%; }
  .controls { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin-bottom: 16px; }
  .control-group { background: #edf2f7; border-radius: 8px; padding: 14px 18px; min-width: 200px; flex: 1; }
  .control-group label { display: block; font-weight: 600; margin-bottom: 8px; color: #2d3748; }
  .control-group input[type=range] { width: 100%; cursor: pointer; }
  .control-group .val { float: right; font-weight: 700; color: #2b6cb0; }
  .formula-box { background: #ebf8ff; border: 2px solid #90cdf4; border-radius: 8px; padding: 16px; text-align: center; }
  .formula-box .formula { font-size: 1.4rem; font-weight: 700; color: #1a365d; }
  .hint { font-size: 0.85rem; color: #a0aec0; text-align: center; margin-top: 8px; }
</style>
</head>
<body>
<div class="container">
  <h1>&#x76F4;&#x7EBF;&#x65B9;&#x7A0B;&#x4EA4;&#x4E92;&#x63A2;&#x7D22;</h1>
  <canvas id="canvas" width="600" height="420"></canvas>
  <div class="controls">
    <div class="control-group">
      <label>&#x659C;&#x7387 k <span class="val" id="valK">1.00</span></label>
      <input type="range" id="sliderK" min="-5" max="5" step="0.1" value="1">
    </div>
    <div class="control-group">
      <label>&#x622A;&#x8DDD b <span class="val" id="valB">0.00</span></label>
      <input type="range" id="sliderB" min="-5" max="5" step="0.1" value="0">
    </div>
  </div>
  <div class="formula-box">
    <div class="formula" id="formula">y = 1.00x + 0.00</div>
  </div>
  <div class="hint">&#x63D0;&#x793A;&#xFF1A;&#x62D6;&#x52A8;&#x6EDA;&#x52A8;&#x6761;&#x89C2;&#x5BDF;&#x76F4;&#x7EBF;&#x53D8;&#x5316;</div>
</div>
<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;
const originX = 60, originY = H - 60;
const scale = 50;

function drawGrid(){
  ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
  for(let x=originX; x<W; x+=scale){ ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,H); ctx.stroke(); }
  for(let y=originY; y>=0; y-=scale){ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }
  ctx.strokeStyle = '#4A5568'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(originX, originY); ctx.lineTo(W-10, originY); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(originX, 10); ctx.lineTo(originX, H-10); ctx.stroke();
  ctx.font = '12px Microsoft YaHei'; ctx.fillStyle = '#4A5568';
  ctx.fillText('x', W-20, originY+16);
  ctx.fillText('y', originX+6, 14);
  ctx.fillText('0', originX-10, originY+16);
  for(let i=-5;i<=5;i++){
    if(i===0) continue;
    ctx.fillText(i, originX+i*scale-4, originY+14);
    ctx.fillText(i, originX-14, originY-i*scale+4);
  }
}

function render(){
  const K = parseFloat(document.getElementById('sliderK').value);
  const B = parseFloat(document.getElementById('sliderB').value);
  document.getElementById('valK').textContent = K.toFixed(2);
  document.getElementById('valB').textContent = B.toFixed(2);
  const bSign = B >= 0 ? '+ ' + B.toFixed(2) : '- ' + Math.abs(B).toFixed(2);
  document.getElementById('formula').textContent = 'y = ' + K.toFixed(2) + 'x ' + bSign;

  ctx.clearRect(0,0,W,H);
  drawGrid();

  ctx.strokeStyle = '#E53E3E'; ctx.lineWidth = 2.5;
  ctx.beginPath();
  let started = false;
  for(let px=0; px<W; px++){
    const x = (px - originX) / scale;
    const y = K * x + B;
    const py = originY - y * scale;
    if(py < -50 || py > H+50) { started = false; continue; }
    if(!started){ ctx.moveTo(px, py); started = true; }
    else ctx.lineTo(px, py);
  }
  ctx.stroke();

  // highlight y-intercept
  const intPx = originX, intPy = originY - B * scale;
  if(intPy >= 0 && intPy <= H){
    ctx.beginPath(); ctx.arc(intPx, intPy, 6, 0, Math.PI*2);
    ctx.fillStyle = '#38A169'; ctx.fill();
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
    ctx.font = 'bold 11px Microsoft YaHei'; ctx.fillStyle = '#276749';
    ctx.fillText('(0,' + B.toFixed(1) + ')', intPx+8, intPy-6);
  }
}

document.getElementById('sliderK').addEventListener('input', render);
document.getElementById('sliderB').addEventListener('input', render);
render();
</script>
</body>
</html>'''
