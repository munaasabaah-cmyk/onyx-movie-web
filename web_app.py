from flask import Flask, jsonify, request
import os
import urllib.request
import urllib.parse
import json

app = Flask(__name__)
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🎬 ONYX MOVIE</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#fff;font-family:'Cairo',sans-serif;min-height:100vh}
.header{padding:15px 30px;background:linear-gradient(180deg,#ff6b35,#e85d2a);display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.logo{font-size:1.4rem;font-weight:900}
.hero{padding:60px 30px;text-align:center}
.hero h1{font-size:3rem;background:linear-gradient(90deg,#ff6b35,#ffd700);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:15px}
.hero p{color:#aaa;font-size:1.1rem}
.section{max-width:1400px;margin:0 auto 50px;padding:0 30px}
.section h2{font-size:1.5rem;margin-bottom:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:20px}
.card{background:#15151f;border-radius:12px;overflow:hidden;transition:all .3s;text-decoration:none;color:#fff}
.card:hover{transform:translateY(-8px);box-shadow:0 15px 40px rgba(255,107,53,.3)}
.card img{width:100%;aspect-ratio:2/3;object-fit:cover;background:#1a1a2e}
.card-info{padding:12px}
.card-info h4{font-size:.95rem;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card-info p{font-size:.8rem;color:#888}
.rating{color:#ffd700;font-weight:700}
.loading{text-align:center;padding:50px;color:#666}
.footer{text-align:center;padding:40px;color:#444;font-size:.85rem;border-top:1px solid #1a1a2e}
@media(max-width:768px){.hero h1{font-size:2rem}.grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}}
</style>
</head>
<body>
<header class="header">
<div class="logo">🎬 ONYX MOVIE</div>
<div>Powered by TMDB</div>
</header>
<section class="hero">
<h1>🎬 ONYX MOVIE</h1>
<p>شاشة واحدة تجمعكم — مكان واحد يجمعكم على فيلم تحبونه</p>
</section>
<section class="section">
<h2>🔥 الأكثر رواجاً</h2>
<div class="grid" id="trending"><div class="loading">جاري التحميل...</div></div>
</section>
<section class="section">
<h2>🎬 أفلام شائعة</h2>
<div class="grid" id="popular"><div class="loading">جاري التحميل...</div></div>
</section>
<footer class="footer">🚀 ONYX STUDIO — جميع الحقوق محفوظة</footer>
<script>
async function load(url,id){
  try{
    const r=await fetch(url);
    const d=await r.json();
    const el=document.getElementById(id);
    if(!d.results||!d.results.length){el.innerHTML='<div class="loading">لا توجد نتائج</div>';return}
    el.innerHTML=d.results.slice(0,12).map(m=>{
      const t=m.title||m.name||'?';
      const y=(m.release_date||m.first_air_date||'').substring(0,4);
      const p=m.poster_path?'https://image.tmdb.org/t/p/w500'+m.poster_path:'https://via.placeholder.com/300x450/15151f/ff6b35';
      const r=m.vote_average?m.vote_average.toFixed(1):'?';
      return `<div class="card"><img src="${p}" loading="lazy"><div class="card-info"><h4>${t}</h4><p>${y} • <span class="rating">⭐ ${r}</span></p></div></div>`;
    }).join('');
  }catch(e){console.error(e);document.getElementById(id).innerHTML='<div class="loading">خطأ</div>'}
}
load('/api/trending','trending');
load('/api/popular/movie','popular');
</script>
</body>
</html>
"""

@app.route("/api/trending")
def trending():
    try:
        url = f"https://api.themoviedb.org/3/trending/all/week?api_key={TMDB_API_KEY}&language=ar"
        with urllib.request.urlopen(url, timeout=10) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/popular/<media_type>")
def popular(media_type):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/popular?api_key={TMDB_API_KEY}&language=ar"
        with urllib.request.urlopen(url, timeout=10) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"results": []})
    try:
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&language=ar&query={urllib.parse.quote(q)}"
        with urllib.request.urlopen(url, timeout=10) as r:
            return jsonify(json.loads(r.read()))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "ONYX MOVIE"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)