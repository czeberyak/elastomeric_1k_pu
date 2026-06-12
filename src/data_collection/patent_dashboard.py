# src/data_collection/patent_dashboard.py
import urllib.parse
from pathlib import Path

def generate_patent_dashboard():
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Спецификация запросов
    queries = {
        "FTO_Sealants": {
            "title": "Патентная чистота герметиков (C09K 3/10)",
            "espacenet": 'cl=C09K3/10 AND aldimine AND "moisture-curing"',
            "google": 'aldimine polyurethane "moisture-curing" cpc:C09K3/10'
        },
        "Prepolymer_Synthesis": {
            "title": "Синтез форполимеров ПУ (C08G 18/12)",
            "espacenet": 'cl=C08G18/12 AND aldimine AND "PPG"',
            "google": 'aldimine prepolymer "PPG" cpc:C08G18/12'
        },
        "Latent_Hardeners": {
            "title": "Латентные отвердители (C08G 18/32)",
            "espacenet": 'cl=C08G18/32 AND aldimine AND "diisocyanate"',
            "google": 'aldimine "diisocyanate" cpc:C08G18/32'
        }
    }
    
    html_content = """<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>R&D Патентный Дашборд: 1K ПУ Герметики</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f6f9; color: #333; }
            h1 { color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
            .card { background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .card h3 { margin-top: 0; color: #2980b9; }
            .btn { display: inline-block; padding: 10px 20px; margin-right: 10px; border-radius: 4px; text-decoration: none; color: white; font-weight: bold; }
            .btn-google { background-color: #ea4335; }
            .btn-espacenet { background-color: #34495e; }
            .btn:hover { opacity: 0.9; }
            code { background: #f1f2f6; padding: 4px 8px; border-radius: 4px; font-family: monospace; display: block; margin: 10px 0; }
        </style>
    </head>
    <body>
        <h1>Интерактивный R&D Патентный Дашборд</h1>
        <p>Используйте преднастроенные URL-кодированные запросы для мгновенного перехода к поиску в Espacenet и Google Patents.</p>
    """
    
    for _, q in queries.items():
        esc_encoded = urllib.parse.quote(q["espacenet"])
        go_encoded = urllib.parse.quote(q["google"])
        
        espacenet_url = f"https://worldwide.espacenet.com/searchResults?query={esc_encoded}"
        google_url = f"https://patents.google.com/?q={go_encoded}"
        
        html_content += f"""
        <div class="card">
            <h3>{q['title']}</h3>
            <p>Запрос Espacenet:</p>
            <code>{q['espacenet']}</code>
            <p>Запрос Google Patents:</p>
            <code>{q['google']}</code>
            <br>
            <a href="{espacenet_url}" target="_blank" class="btn btn-espacenet">Искать в Espacenet</a>
            <a href="{google_url}" target="_blank" class="btn btn-google">Искать в Google Patents</a>
        </div>
        """
        
    html_content += """
    </body>
    </html>
    """
    
    output_path = reports_dir / "patent_search_dashboard.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Интерактивный дашборд успешно создан: {output_path.resolve()}")

if __name__ == "__main__":
    generate_patent_dashboard()