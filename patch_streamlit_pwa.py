"""
Automated Streamlit PWA Patch Script.
Copies PWA assets to Streamlit's static directory and injects manifest & service worker tags into index.html.
"""
import os
import shutil
import streamlit

PWA_TAGS_MARKER = "<!-- SMART_AGRICULTURE_PWA_HEAD_TAGS -->"

PWA_HEAD_HTML = f"""{PWA_TAGS_MARKER}
    <link rel="manifest" href="./manifest.json" />
    <meta name="theme-color" content="#10b981" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="SmartAgri" />
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
            
    # 2. Patch index.html head
    if not os.path.exists(index_path):
        print(f"Error: index.html not found at {index_path}")
        return False
        
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if PWA_TAGS_MARKER in content:
        print("index.html is already patched with PWA tags.")
        return True
        
    # Inject tags before </head>
    if "</head>" in content:
        new_content = content.replace("</head>", f"{PWA_HEAD_HTML}\n  </head>")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully injected PWA tags into Streamlit's index.html")
        return True
    else:
        print("Error: </head> tag not found in index.html")
        return False

if __name__ == "__main__":
    patch_streamlit()
