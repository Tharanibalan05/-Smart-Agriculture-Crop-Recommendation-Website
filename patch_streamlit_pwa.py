"""
Automated Streamlit PWA Patch Script.
Copies PWA assets to Streamlit's static directory and injects manifest & service worker tags into index.html.
"""
import os
import shutil
import streamlit

PWA_TAGS_MARKER = "<!-- SMART_AGRICULTURE_PWA_HEAD_TAGS -->"

PWA_HEAD_HTML = f"""{PWA_TAGS_MARKER}
    <title>Smart Agriculture | AI Crop Recommendation System</title>
    <meta name="description" content="Smart Agriculture is an AI-powered crop recommendation and agricultural decision support system that analyzes soil nutrients, weather conditions, market prices, crop suitability, and agricultural risks to recommend suitable crops." />
    <meta name="keywords" content="Smart Agriculture, AI Crop Recommendation, Crop Recommendation System, Agriculture Decision Support System, Smart Farming, Soil Health Analysis, Crop Suitability, Agricultural Risk Analysis, Machine Learning Agriculture" />
    <link rel="canonical" href="https://smart-agriculture-dss.onrender.com/" />
    <meta property="og:title" content="Smart Agriculture | AI Crop Recommendation System" />
    <meta property="og:description" content="AI-powered crop recommendation and agricultural decision support using soil, weather, market, suitability and risk analysis." />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="https://smart-agriculture-dss.onrender.com" />
    <meta property="og:image" content="https://smart-agriculture-dss.onrender.com/icon-512.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Smart Agriculture | AI Crop Recommendation System" />
    <meta name="twitter:description" content="AI-powered crop recommendation and agricultural decision support using soil, weather, market, suitability and risk analysis." />
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "WebApplication",
      "name": "Smart Agriculture",
      "applicationCategory": "AgricultureApplication",
      "operatingSystem": "Web",
      "description": "AI-powered crop recommendation and agricultural decision support system using soil, weather, market, suitability and risk analysis.",
      "url": "https://smart-agriculture-dss.onrender.com"
    }}
    </script>
    <link rel="manifest" href="./manifest.json" />
    <meta name="theme-color" content="#10b981" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="Smart Agriculture" />
    <link rel="apple-touch-icon" href="./icon-192.png" />
    <script>
      if ('serviceWorker' in navigator) {{
        window.addEventListener('load', function() {{
          navigator.serviceWorker.register('./service-worker.js')
            .then(function(reg) {{
              console.log('[PWA] ServiceWorker registration successful with scope: ', reg.scope);
            }})
            .catch(function(err) {{
              console.warn('[PWA] ServiceWorker registration failed: ', err);
            }});
        }});
      }}
    </script>
    <!-- END_SMART_AGRICULTURE_PWA_HEAD_TAGS -->
"""

def patch_streamlit():
    streamlit_dir = os.path.dirname(streamlit.__file__)
    static_dir = os.path.join(streamlit_dir, "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if not os.path.exists(static_dir):
        print(f"Error: Streamlit static directory not found at {static_dir}")
        return False
        
    print(f"Streamlit static directory: {static_dir}")
    
    # 1. Copy PWA assets to static directory
    assets = ["manifest.json", "service-worker.js", "icon-192.png", "icon-512.png"]
    for asset in assets:
        if os.path.exists(asset):
            dest = os.path.join(static_dir, asset)
            shutil.copy2(asset, dest)
            print(f"Copied asset -> {dest}")
        else:
            print(f"Warning: Asset {asset} not found in current directory.")

    # Generate crawler support files in static directory
    robots_content = "User-agent: *\nAllow: /\n\nSitemap: https://smart-agriculture-dss.onrender.com/sitemap.xml\n"
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://smart-agriculture-dss.onrender.com/</loc>
    <lastmod>2026-08-14</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    try:
        with open(os.path.join(static_dir, "robots.txt"), "w", encoding="utf-8") as f:
            f.write(robots_content)
        print("Generated robots.txt in static dir")
        with open(os.path.join(static_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write(sitemap_content)
        print("Generated sitemap.xml in static dir")
    except Exception as err:
        print(f"Warning generating crawler files: {err}")
            
    # 2. Patch index.html head
    if not os.path.exists(index_path):
        print(f"Error: index.html not found at {index_path}")
        return False
        
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if PWA_TAGS_MARKER in content:
        print("index.html is already patched with PWA & SEO tags.")
        return True
        
    # Inject tags before </head>
    if "</head>" in content:
        new_content = content.replace("</head>", f"{PWA_HEAD_HTML}\n  </head>")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully injected PWA & SEO tags into Streamlit's index.html")
        return True
    else:
        print("Error: </head> tag not found in index.html")
        return False

if __name__ == "__main__":
    patch_streamlit()
