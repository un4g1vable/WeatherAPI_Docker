import time
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from logger import log
from services import start_background_tasks
from api import router
from init_db import init_database
from storage_service import storage_service

app = FastAPI(
    title="Weather Monitoring API (S3 PostgreSQL Edition)",
    version="2.0",
    description="Weather Monitoring API — сервис для сбора, хранения и мониторинга погодных данных с поддержкой S3-принципов."
)


@app.on_event("startup")
async def startup():
    log("system", "=" * 60)
    log("system", "Запуск Weather Monitoring API (S3 PostgreSQL Edition)")
    log("system", "=" * 60)

    # Инициализация базы данных
    if await init_database():
        log("system", "✅ База данных готова к работе")
    else:
        log("error", "❌ Не удалось инициализировать базу данных")

    # Проверяем и создаем структуру бэкапов
    from pathlib import Path
    backup_dir = Path("./backups")
    backup_dir.mkdir(exist_ok=True, parents=True)
    log("system", f"📂 Директория бэкапов: {backup_dir.absolute()}")

    # Запускаем фоновые задачи
    asyncio.create_task(start_background_tasks())
    log("system", "🔄 Фоновые задачи запущены")

    # Инициализируем сервис хранилища
    log("system", "🛡️  Сервис архивации и бэкапов инициализирован")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    log("http", f"{request.method} {request.url.path} {response.status_code} ({time.time() - start_time:.3f}s)")
    return response


app.include_router(router)


# Обновленный интерфейс с вкладкой для управления хранилищем
@app.get("/", response_class=HTMLResponse)
async def get_ui():
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🌤️ Weather Monitor Pro (S3 Edition)</title>

        <!-- Google Fonts -->
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">

        <!-- Font Awesome Icons -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

        <!-- Animate.css -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">

        <style>
            :root {{
                --primary: #4361ee;
                --primary-dark: #3a56d4;
                --secondary: #7209b7;
                --success: #4cc9f0;
                --danger: #f72585;
                --warning: #f8961e;
                --info: #4895ef;
                --light: #f8f9fa;
                --dark: #212529;
                --card-bg: rgba(255, 255, 255, 0.95);
                --shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
                --radius: 16px;
                --transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
                --storage: #20c997;
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                background-attachment: fixed;
                color: #333;
                min-height: 100vh;
                padding: 20px;
            }}

            .app-container {{
                max-width: 1800px;
                margin: 0 auto;
            }}

            /* Header Styles */
            .header {{
                background: linear-gradient(90deg, var(--primary), var(--secondary));
                border-radius: var(--radius);
                padding: 30px 40px;
                margin-bottom: 30px;
                color: white;
                box-shadow: var(--shadow);
                animation: fadeInDown 0.8s ease;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
            }}

            .header-content h1 {{
                font-family: 'Poppins', sans-serif;
                font-weight: 700;
                font-size: 2.5rem;
                margin-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 15px;
            }}

            .header-content p {{
                font-size: 1.1rem;
                opacity: 0.9;
            }}

            .header-badge {{
                background: var(--storage);
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 600;
                margin-left: 10px;
                vertical-align: middle;
            }}

            .header-actions {{
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
            }}

            /* Button Styles */
            .btn {{
                padding: 12px 24px;
                border-radius: 50px;
                border: none;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                transition: var(--transition);
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                text-decoration: none;
            }}

            .btn-primary {{
                background: var(--primary);
                color: white;
            }}

            .btn-primary:hover {{
                background: var(--primary-dark);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(67, 97, 238, 0.3);
            }}

            .btn-success {{
                background: var(--success);
                color: white;
            }}

            .btn-success:hover {{
                background: #3ab3d6;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(76, 201, 240, 0.3);
            }}

            .btn-warning {{
                background: var(--warning);
                color: white;
            }}

            .btn-warning:hover {{
                background: #e68919;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(248, 150, 30, 0.3);
            }}

            .btn-danger {{
                background: var(--danger);
                color: white;
            }}

            .btn-danger:hover {{
                background: #e11570;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(247, 37, 133, 0.3);
            }}

            .btn-storage {{
                background: var(--storage);
                color: white;
            }}

            .btn-storage:hover {{
                background: #1ba87e;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(32, 201, 151, 0.3);
            }}

            /* Card Styles */
            .card {{
                background: var(--card-bg);
                border-radius: var(--radius);
                padding: 25px;
                margin-bottom: 25px;
                box-shadow: var(--shadow);
                transition: var(--transition);
                border: 1px solid rgba(255, 255, 255, 0.2);
                backdrop-filter: blur(10px);
            }}

            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.12);
            }}

            .card-title {{
                font-family: 'Poppins', sans-serif;
                font-weight: 600;
                font-size: 1.4rem;
                margin-bottom: 20px;
                color: var(--primary);
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            /* Stats Cards */
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}

            .stat-card {{
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                border-radius: var(--radius);
                padding: 25px;
                text-align: center;
                border-left: 5px solid var(--primary);
                transition: var(--transition);
            }}

            .stat-card.storage {{
                border-left-color: var(--storage);
            }}

            .stat-card.archive {{
                border-left-color: var(--info);
            }}

            .stat-card.backup {{
                border-left-color: var(--success);
            }}

            .stat-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
            }}

            .stat-icon {{
                font-size: 2.5rem;
                color: var(--primary);
                margin-bottom: 15px;
            }}

            .stat-card.storage .stat-icon {{ color: var(--storage); }}
            .stat-card.archive .stat-icon {{ color: var(--info); }}
            .stat-card.backup .stat-icon {{ color: var(--success); }}

            .stat-number {{
                font-size: 2.5rem;
                font-weight: 700;
                color: var(--dark);
                margin-bottom: 5px;
            }}

            .stat-label {{
                font-size: 1rem;
                color: #6c757d;
                font-weight: 500;
            }}

            /* Tabs */
            .tabs {{
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                border-bottom: 2px solid #e9ecef;
                padding-bottom: 10px;
                flex-wrap: wrap;
            }}

            .tab-btn {{
                padding: 10px 20px;
                background: none;
                border: none;
                font-weight: 600;
                color: #6c757d;
                cursor: pointer;
                border-radius: 8px 8px 0 0;
                transition: var(--transition);
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .tab-btn.active {{
                color: var(--primary);
                background: rgba(67, 97, 238, 0.1);
                border-bottom: 3px solid var(--primary);
            }}

            .tab-btn:hover {{
                background: rgba(67, 97, 238, 0.05);
            }}

            .tab-content {{
                display: none;
            }}

            .tab-content.active {{
                display: block;
            }}

            /* Storage Controls */
            .storage-controls {{
                display: flex;
                gap: 15px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}

            .control-group {{
                background: white;
                padding: 20px;
                border-radius: var(--radius);
                box-shadow: var(--shadow);
                flex: 1;
                min-width: 300px;
            }}

            .control-title {{
                font-weight: 600;
                margin-bottom: 15px;
                color: var(--dark);
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            .control-actions {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}

            /* Backup List */
            .backup-list {{
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #e9ecef;
                border-radius: var(--radius);
                background: white;
            }}

            .backup-item {{
                padding: 15px;
                border-bottom: 1px solid #e9ecef;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .backup-item:last-child {{
                border-bottom: none;
            }}

            .backup-info {{
                flex: 1;
            }}

            .backup-name {{
                font-weight: 600;
                margin-bottom: 5px;
            }}

            .backup-meta {{
                font-size: 0.9rem;
                color: #6c757d;
                display: flex;
                gap: 15px;
            }}

            .backup-badge {{
                padding: 3px 10px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 600;
            }}

            .badge-full {{
                background: #e3f2fd;
                color: #1976d2;
            }}

            .badge-incremental {{
                background: #f3e5f5;
                color: #7b1fa2;
            }}

            .badge-completed {{
                background: #e8f5e9;
                color: #388e3c;
            }}

            .badge-failed {{
                background: #ffebee;
                color: #d32f2f;
            }}

            /* Progress Bar */
            .progress-container {{
                margin: 20px 0;
            }}

            .progress-label {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 5px;
            }}

            .progress-bar {{
                height: 10px;
                background: #e9ecef;
                border-radius: 5px;
                overflow: hidden;
            }}

            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, var(--primary), var(--success));
                border-radius: 5px;
                transition: width 0.3s ease;
            }}

            /* Storage Stats */
            .storage-stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}

            .storage-stat {{
                background: white;
                padding: 15px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid #e9ecef;
            }}

            .storage-stat-value {{
                font-size: 1.5rem;
                font-weight: 700;
                margin: 10px 0;
            }}

            .storage-stat-label {{
                font-size: 0.9rem;
                color: #6c757d;
            }}

            /* Archive Table */
            .archive-table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: var(--radius);
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
            }}

            .archive-table th {{
                background: #f8f9fa;
                padding: 15px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #e9ecef;
            }}

            .archive-table td {{
                padding: 12px 15px;
                border-bottom: 1px solid #f1f3f5;
            }}

            .archive-table tr:hover {{
                background: #f8f9fa;
            }}

            /* Existing styles from original UI */
            .city-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}

            .city-card {{
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                cursor: pointer;
                transition: var(--transition);
                border: 2px solid transparent;
                position: relative;
                overflow: hidden;
            }}

            .city-card.inactive {{
                opacity: 0.6;
                background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
            }}

            .city-card:hover {{
                transform: translateY(-5px);
                border-color: var(--primary);
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            }}

            .city-name {{
                font-weight: 600;
                font-size: 1.1rem;
                margin-bottom: 5px;
                color: var(--dark);
            }}

            .city-slug {{
                font-size: 0.85rem;
                color: #6c757d;
                font-family: monospace;
            }}

            .filter-controls {{
                display: flex;
                gap: 15px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}

            .search-box {{
                flex: 1;
                min-width: 250px;
                position: relative;
            }}

            .search-icon {{
                position: absolute;
                left: 15px;
                top: 50%;
                transform: translateY(-50%);
                color: #6c757d;
            }}

            .search-box input {{
                padding-left: 45px;
            }}

            .select-box {{
                min-width: 200px;
            }}

            .weather-table {{
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                background: white;
                border-radius: var(--radius);
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
            }}

            .weather-table thead {{
                background: linear-gradient(90deg, var(--primary), var(--secondary));
                color: white;
            }}

            .weather-table th {{
                padding: 18px 15px;
                text-align: left;
                font-weight: 600;
                font-size: 0.95rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            .weather-table tbody tr {{
                transition: var(--transition);
                border-bottom: 1px solid #f1f3f5;
            }}

            .weather-table tbody tr:hover {{
                background-color: #f8f9fa;
                transform: scale(1.002);
            }}

            .weather-table td {{
                padding: 16px 15px;
                font-size: 0.95rem;
                vertical-align: middle;
            }}

            /* Badges */
            .badge {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 50px;
                font-size: 0.85rem;
                font-weight: 600;
                text-transform: capitalize;
            }}

            .badge-time-morning {{ background: linear-gradient(90deg, #ffd166, #ffb347); color: #333; }}
            .badge-time-day {{ background: linear-gradient(90deg, #06d6a0, #0cb48a); color: white; }}
            .badge-time-evening {{ background: linear-gradient(90deg, #118ab2, #0d7ca1); color: white; }}
            .badge-time-night {{ background: linear-gradient(90deg, #073b4c, #052a37); color: white; }}
            .badge-time-now {{ background: linear-gradient(90deg, #ef476f, #e83e66); color: white; }}

            .temp-badge {{
                padding: 8px 15px;
                border-radius: 50px;
                font-weight: 700;
                font-size: 1rem;
                min-width: 70px;
                text-align: center;
                display: inline-block;
            }}

            .temp-hot {{ background: linear-gradient(90deg, #ff6b6b, #ee5a52); color: white; }}
            .temp-warm {{ background: linear-gradient(90deg, #ffd166, #ffb347); color: #333; }}
            .temp-mild {{ background: linear-gradient(90deg, #06d6a0, #0cb48a); color: white; }}
            .temp-cool {{ background: linear-gradient(90deg, #118ab2, #0d7ca1); color: white; }}
            .temp-cold {{ background: linear-gradient(90deg, #073b4c, #052a37); color: white; }}

            .condition-badge {{
                padding: 6px 12px;
                border-radius: 8px;
                background: #e9f7fe;
                color: #0d6efd;
                font-size: 0.85rem;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }}

            /* Action Buttons */
            .action-btns {{
                display: flex;
                gap: 8px;
            }}

            .action-btn {{
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: var(--transition);
                border: none;
                font-size: 1rem;
            }}

            .action-btn-edit {{
                background: rgba(13, 110, 253, 0.1);
                color: #0d6efd;
            }}

            .action-btn-edit:hover {{
                background: #0d6efd;
                color: white;
                transform: scale(1.1);
            }}

            .action-btn-delete {{
                background: rgba(220, 53, 69, 0.1);
                color: #dc3545;
            }}

            .action-btn-delete:hover {{
                background: #dc3545;
                color: white;
                transform: scale(1.1);
            }}

            /* Modal */
            .modal-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(5px);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                padding: 20px;
            }}

            .modal-content {{
                background: white;
                border-radius: var(--radius);
                width: 100%;
                max-width: 600px;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
                animation: fadeInUp 0.4s ease;
            }}

            .modal-header {{
                padding: 25px 30px;
                border-bottom: 1px solid #f1f3f5;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .modal-title {{
                font-family: 'Poppins', sans-serif;
                font-weight: 600;
                font-size: 1.5rem;
                color: var(--dark);
            }}

            .modal-close {{
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #6c757d;
                transition: var(--transition);
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .modal-close:hover {{
                background: #f8f9fa;
                color: var(--dark);
            }}

            .modal-body {{
                padding: 30px;
            }}

            .form-group {{
                margin-bottom: 20px;
            }}

            .form-label {{
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: var(--dark);
            }}

            .form-control {{
                width: 100%;
                padding: 12px 15px;
                border-radius: 10px;
                border: 1px solid #dee2e6;
                font-family: 'Inter', sans-serif;
                font-size: 1rem;
                transition: var(--transition);
            }}

            .form-control:focus {{
                outline: none;
                border-color: var(--primary);
                box-shadow: 0 0 0 3px rgba(67, 97, 238, 0.15);
            }}

            .form-row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}

            .form-check {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            .form-check-input {{
                width: 20px;
                height: 20px;
            }}

            .modal-footer {{
                padding: 20px 30px;
                border-top: 1px solid #f1f3f5;
                display: flex;
                justify-content: flex-end;
                gap: 15px;
            }}

            /* Toast */
            .toast {{
                position: fixed;
                top: 30px;
                right: 30px;
                background: white;
                border-radius: var(--radius);
                padding: 20px 25px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
                display: none;
                align-items: center;
                gap: 15px;
                z-index: 1100;
                animation: fadeInRight 0.4s ease;
                max-width: 350px;
                border-left: 5px solid var(--success);
            }}

            .toast-success {{
                border-left-color: var(--success);
            }}

            .toast-error {{
                border-left-color: var(--danger);
            }}

            .toast-icon {{
                font-size: 1.5rem;
            }}

            .toast-success .toast-icon {{ color: var(--success); }}
            .toast-error .toast-icon {{ color: var(--danger); }}

            .toast-message {{
                flex: 1;
                font-weight: 500;
            }}

            .toast-close {{
                background: none;
                border: none;
                color: #6c757d;
                cursor: pointer;
                font-size: 1.2rem;
            }}

            /* Loading */
            .loader {{
                display: none;
                justify-content: center;
                padding: 40px;
            }}

            .spinner {{
                width: 50px;
                height: 50px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }}

            /* Empty State */
            .empty-state {{
                text-align: center;
                padding: 50px 20px;
                color: #6c757d;
            }}

            .empty-state-icon {{
                font-size: 4rem;
                color: #dee2e6;
                margin-bottom: 20px;
            }}

            .empty-state-title {{
                font-size: 1.5rem;
                margin-bottom: 10px;
                color: #6c757d;
            }}

            .empty-state-text {{
                font-size: 1rem;
                max-width: 400px;
                margin: 0 auto 30px;
            }}

            /* Animations */
            @keyframes fadeInDown {{
                from {{ opacity: 0; transform: translateY(-20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            @keyframes fadeInUp {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            @keyframes fadeInRight {{
                from {{ opacity: 0; transform: translateX(20px); }}
                to {{ opacity: 1; transform: translateX(0); }}
            }}

            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}

            /* Responsive */
            @media (max-width: 992px) {{
                .header {{
                    flex-direction: column;
                    text-align: center;
                    gap: 20px;
                }}

                .header-actions {{
                    justify-content: center;
                }}

                .form-row {{
                    grid-template-columns: 1fr;
                }}

                .city-grid {{
                    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                }}

                .storage-controls {{
                    flex-direction: column;
                }}

                .control-group {{
                    min-width: 100%;
                }}
            }}

            @media (max-width: 768px) {{
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}

                .city-grid {{
                    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                }}

                .weather-table {{
                    font-size: 0.9rem;
                }}

                .weather-table th,
                .weather-table td {{
                    padding: 12px 10px;
                }}

                .tabs {{
                    flex-direction: column;
                }}

                .storage-stats-grid {{
                    grid-template-columns: 1fr 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- Header -->
            <header class="header animate__animated animate__fadeInDown">
                <div class="header-content">
                    <h1>
                        <i class="fas fa-cloud-sun"></i> Weather Monitor Pro
                        <span class="header-badge">S3 Edition</span>
                    </h1>
                    <p>Мощная система мониторинга погоды с архивацией и резервным копированием</p>
                </div>
                <div class="header-actions">
                    <button class="btn btn-primary" onclick="openCreateWeatherModal()">
                        <i class="fas fa-plus-circle"></i> Новая запись
                    </button>
                    <button class="btn btn-storage" onclick="openStorageModal()">
                        <i class="fas fa-database"></i> Управление хранилищем
                    </button>
                    <button class="btn btn-warning" onclick="loadWeather()">
                        <i class="fas fa-sync-alt"></i> Обновить
                    </button>
                </div>
            </header>

            <!-- Storage Stats Section -->
            <div class="stats-grid">
                <div class="stat-card animate__animated animate__fadeInLeft storage" style="animation-delay: 0.1s">
                    <div class="stat-icon">
                        <i class="fas fa-database"></i>
                    </div>
                    <div class="stat-number" id="totalRecords">0</div>
                    <div class="stat-label">Всего записей</div>
                </div>

                <div class="stat-card animate__animated animate__fadeInLeft archive" style="animation-delay: 0.2s">
                    <div class="stat-icon">
                        <i class="fas fa-archive"></i>
                    </div>
                    <div class="stat-number" id="archivedRecords">0</div>
                    <div class="stat-label">В архиве</div>
                </div>

                <div class="stat-card animate__animated animate__fadeInLeft backup" style="animation-delay: 0.3s">
                    <div class="stat-icon">
                        <i class="fas fa-save"></i>
                    </div>
                    <div class="stat-number" id="backupCount">0</div>
                    <div class="stat-label">Бэкапов</div>
                </div>

                <div class="stat-card animate__animated animate__fadeInLeft" style="animation-delay: 0.4s">
                    <div class="stat-icon">
                        <i class="fas fa-hdd"></i>
                    </div>
                    <div class="stat-number" id="storageSize">0 MB</div>
                    <div class="stat-label">Размер хранилища</div>
                </div>
            </div>

            <!-- Tabs -->
            <div class="tabs">
                <button class="tab-btn active" onclick="switchTab('weatherTab')">
                    <i class="fas fa-cloud-sun"></i> Погода
                </button>
                <button class="tab-btn" onclick="switchTab('citiesTab')">
                    <i class="fas fa-city"></i> Управление городами
                </button>
                <button class="tab-btn" onclick="switchTab('parserTab')">
                    <i class="fas fa-satellite-dish"></i> Тест парсера
                </button>
                <button class="tab-btn" onclick="switchTab('storageTab')">
                    <i class="fas fa-database"></i> Хранилище
                </button>
            </div>

            <!-- Weather Tab -->
            <div class="tab-content active" id="weatherTab">
                <div class="card animate__animated animate__fadeInUp" style="animation-delay: 0.2s">
                    <div class="card-title">
                        <i class="fas fa-map-marked-alt"></i> Выбор города для парсинга
                    </div>

                    <div class="city-grid" id="cityGrid">
                        <!-- Города будут загружены динамически -->
                    </div>

                    <div style="margin-top: 25px; display: flex; gap: 15px; flex-wrap: wrap;">
                        <div class="search-box">
                            <i class="fas fa-search search-icon"></i>
                            <input type="text" class="form-control" id="searchInput" placeholder="Поиск по городу или условиям...">
                        </div>

                        <div class="select-box">
                            <select class="form-control" id="cityFilter">
                                <option value="">Все города</option>
                            </select>
                        </div>

                        <div class="select-box">
                            <select class="form-control" id="conditionFilter">
                                <option value="">Все условия</option>
                                <option value="ясно">Ясно</option>
                                <option value="облачно">Облачно</option>
                                <option value="снег">Снег</option>
                                <option value="дождь">Дождь</option>
                            </select>
                        </div>

                        <button class="btn btn-warning" onclick="resetFilters()">
                            <i class="fas fa-filter"></i> Сбросить фильтры
                        </button>
                    </div>
                </div>

                <!-- Weather Data -->
                <div class="card animate__animated animate__fadeInUp" style="animation-delay: 0.3s">
                    <div class="card-title">
                        <i class="fas fa-table"></i> Погодные записи
                        <div style="margin-left: auto; display: flex; align-items: center; gap: 10px;">
                            <span class="badge badge-time-now" id="filteredCount">0</span>
                            <span style="color: #6c757d;">из</span>
                            <span class="badge badge-time-night" id="totalCount">0</span>
                        </div>
                    </div>

                    <div class="loader" id="loader">
                        <div class="spinner"></div>
                    </div>

                    <div class="empty-state" id="emptyState" style="display: none;">
                        <div class="empty-state-icon">
                            <i class="fas fa-cloud"></i>
                        </div>
                        <div class="empty-state-title">Нет данных</div>
                        <div class="empty-state-text">Начните с парсинга погоды для одного из городов или добавьте запись вручную</div>
                        <button class="btn btn-primary" onclick="openCreateWeatherModal()">
                            <i class="fas fa-plus-circle"></i> Добавить первую запись
                        </button>
                    </div>

                    <div class="table-container">
                        <table class="weather-table" id="weatherTable">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Дата</th>
                                    <th>Время суток</th>
                                    <th>Город</th>
                                    <th>Температура</th>
                                    <th>Условия</th>
                                    <th>Создано</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody id="weatherTableBody">
                                <!-- Данные будут загружены динамически -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Cities Management Tab -->
            <div class="tab-content" id="citiesTab">
                <div class="card animate__animated animate__fadeInUp">
                    <div class="card-title">
                        <i class="fas fa-city"></i> Управление городами
                        <button class="btn btn-success" style="margin-left: auto;" onclick="openCreateCityModal()">
                            <i class="fas fa-plus"></i> Добавить город
                        </button>
                    </div>

                    <div class="table-container">
                        <table class="weather-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Название (рус.)</th>
                                    <th>Slug (англ.)</th>
                                    <th>Статус</th>
                                    <th>Действия</th>
                                </tr>
                            </thead>
                            <tbody id="citiesTableBody">
                                <!-- Данные будут загружены динамически -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Parser Test Tab -->
            <div class="tab-content" id="parserTab">
                <div class="card animate__animated animate__fadeInUp">
                    <div class="card-title">
                        <i class="fas fa-satellite-dish"></i> Тестирование парсера
                    </div>

                    <div style="margin-bottom: 20px;">
                        <label class="form-label">Выберите город для теста парсера:</label>
                        <select class="form-control" id="testCitySelect" style="max-width: 300px;">
                            <option value="">Выберите город...</option>
                        </select>
                    </div>

                    <button class="btn btn-primary" onclick="testParser()">
                        <i class="fas fa-play"></i> Запустить тест
                    </button>

                    <div class="loader" id="parserLoader" style="display: none;">
                        <div class="spinner"></div>
                    </div>

                    <div id="parserResult" style="margin-top: 20px;"></div>
                </div>
            </div>

            <!-- Storage Management Tab (NEW) -->
            <div class="tab-content" id="storageTab">
                <div class="card animate__animated animate__fadeInUp">
                    <div class="card-title">
                        <i class="fas fa-database"></i> Управление хранилищем
                    </div>

                    <!-- Storage Controls -->
                    <div class="storage-controls">
                        <div class="control-group">
                            <div class="control-title">
                                <i class="fas fa-archive"></i> Архивация
                            </div>
                            <p style="color: #6c757d; margin-bottom: 15px;">
                                Автоматическая архивация записей старше 30 дней. Снижает нагрузку на основную БД.
                            </p>
                            <div class="control-actions">
                                <button class="btn btn-warning" onclick="runArchive()">
                                    <i class="fas fa-archive"></i> Запустить архивацию
                                </button>
                                <button class="btn btn-info" onclick="viewArchive()">
                                    <i class="fas fa-eye"></i> Просмотреть архив
                                </button>
                            </div>
                        </div>

                        <div class="control-group">
                            <div class="control-title">
                                <i class="fas fa-save"></i> Резервное копирование
                            </div>
                            <p style="color: #6c757d; margin-bottom: 15px;">
                                Создание резервных копий данных для восстановления в случае сбоев.
                            </p>
                            <div class="control-actions">
                                <button class="btn btn-success" onclick="createBackup('full')">
                                    <i class="fas fa-plus-circle"></i> Полный бэкап
                                </button>
                                <button class="btn btn-primary" onclick="createBackup('incremental')">
                                    <i class="fas fa-plus"></i> Инкрементальный
                                </button>
                                <button class="btn btn-info" onclick="viewBackups()">
                                    <i class="fas fa-list"></i> Список бэкапов
                                </button>
                            </div>
                        </div>

                        <div class="control-group">
                            <div class="control-title">
                                <i class="fas fa-broom"></i> Очистка
                            </div>
                            <p style="color: #6c757d; margin-bottom: 15px;">
                                Удаление старых бэкапов для освобождения места (старше 90 дней).
                            </p>
                            <div class="control-actions">
                                <button class="btn btn-danger" onclick="cleanupBackups()">
                                    <i class="fas fa-trash-alt"></i> Очистить старые бэкапы
                                </button>
                                <button class="btn btn-warning" onclick="optimizeDatabase()">
                                    <i class="fas fa-magic"></i> Оптимизировать БД
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Storage Statistics -->
                    <div class="card" style="margin-top: 20px;">
                        <div class="card-title">
                            <i class="fas fa-chart-bar"></i> Статистика хранилища
                        </div>
                        <div id="storageStats">
                            <!-- Stats will be loaded here -->
                        </div>
                    </div>

                    <!-- Recent Backups -->
                    <div class="card" style="margin-top: 20px;">
                        <div class="card-title">
                            <i class="fas fa-history"></i> Последние бэкапы
                        </div>
                        <div class="backup-list" id="recentBackups">
                            <!-- Backups will be loaded here -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <footer style="text-align: center; padding: 20px; color: rgba(255, 255, 255, 0.7); font-size: 0.9rem;">
                <p>© 2026 Weather Monitor</p>
            </footer>
        </div>

        <!-- Storage Modal -->
        <div class="modal-overlay" id="storageModal">
            <div class="modal-content" style="max-width: 800px;">
                <div class="modal-header">
                    <div class="modal-title">
                        <i class="fas fa-database"></i> Детальная информация о хранилище
                    </div>
                    <button class="modal-close" onclick="closeStorageModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div id="storageModalContent">
                        <!-- Content will be loaded dynamically -->
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-warning" onclick="closeStorageModal()">
                        <i class="fas fa-times"></i> Закрыть
                    </button>
                </div>
            </div>
        </div>

        <!-- Create/Edit Weather Modal -->
        <div class="modal-overlay" id="weatherModal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title" id="weatherModalTitle">Добавить запись о погоде</div>
                    <button class="modal-close" onclick="closeWeatherModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <form id="weatherForm">
                        <input type="hidden" id="recordId">

                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="date">Дата</label>
                                <input type="date" class="form-control" id="date" required>
                            </div>

                            <div class="form-group">
                                <label class="form-label" for="time_of_day">Время суток</label>
                                <select class="form-control" id="time_of_day" required>
                                    <option value="">Выберите время</option>
                                    <option value="утро">Утро</option>
                                    <option value="день">День</option>
                                    <option value="вечер">Вечер</option>
                                    <option value="ночь">Ночь</option>
                                    <option value="сейчас">Сейчас</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label class="form-label" for="city">Город</label>
                                <input type="text" class="form-control" id="city" required placeholder="Например: Москва">
                            </div>

                            <div class="form-group">
                                <label class="form-label" for="temperature">Температура</label>
                                <input type="text" class="form-control" id="temperature" required placeholder="Например: +15°C">
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="condition">Погодные условия</label>
                            <textarea class="form-control" id="condition" rows="3" placeholder="Опишите погодные условия..." required></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-warning" onclick="closeWeatherModal()">
                        <i class="fas fa-times"></i> Отмена
                    </button>
                    <button class="btn btn-primary" onclick="saveWeather()">
                        <i class="fas fa-save"></i> Сохранить запись
                    </button>
                </div>
            </div>
        </div>

        <!-- Create/Edit City Modal -->
        <div class="modal-overlay" id="cityModal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title" id="cityModalTitle">Добавить город</div>
                    <button class="modal-close" onclick="closeCityModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <form id="cityForm">
                        <input type="hidden" id="cityId">

                        <div class="form-group">
                            <label class="form-label" for="cityName">Название города (русский)</label>
                            <input type="text" class="form-control" id="cityName" required placeholder="Например: Москва">
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="citySlug">Slug для парсинга (английский)</label>
                            <input type="text" class="form-control" id="citySlug" required placeholder="Например: moscow">
                            <small style="color: #6c757d; margin-top: 5px; display: block;">
                                Это название используется в URL для парсинга. Пример: moscow → https://pogoda.mail.ru/prognoz/moscow/extended/
                            </small>
                        </div>

                        <div class="form-check">
                            <input type="checkbox" class="form-check-input" id="cityIsActive" checked>
                            <label class="form-label" for="cityIsActive">Активен для парсинга</label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-warning" onclick="closeCityModal()">
                        <i class="fas fa-times"></i> Отмена
                    </button>
                    <button class="btn btn-primary" onclick="saveCity()">
                        <i class="fas fa-save"></i> Сохранить город
                    </button>
                </div>
            </div>
        </div>

        <!-- Delete Confirmation Modal -->
        <div class="modal-overlay" id="deleteModal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title"><i class="fas fa-exclamation-triangle"></i> Подтверждение удаления</div>
                    <button class="modal-close" onclick="closeDeleteModal()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div style="text-align: center; padding: 20px;">
                        <div style="font-size: 4rem; color: #dc3545; margin-bottom: 20px;">
                            <i class="fas fa-trash-alt"></i>
                        </div>
                        <h3 style="margin-bottom: 10px;">Вы уверены?</h3>
                        <p style="color: #6c757d; margin-bottom: 30px;" id="deleteMessage">Вы собираетесь удалить запись. Это действие нельзя отменить.</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-warning" onclick="closeDeleteModal()">
                        <i class="fas fa-times"></i> Отмена
                    </button>
                    <button class="btn btn-danger" onclick="confirmDelete()">
                        <i class="fas fa-trash-alt"></i> Да, удалить
                    </button>
                </div>
            </div>
        </div>

        <!-- Toast Notification -->
        <div class="toast toast-success" id="successToast">
            <div class="toast-icon">
                <i class="fas fa-check-circle"></i>
            </div>
            <div class="toast-message" id="toastMessage">Успешно!</div>
            <button class="toast-close" onclick="hideToast()">
                <i class="fas fa-times"></i>
            </button>
        </div>

        <script>
            // Основные переменные
            let allWeatherData = [];
            let allCities = [];
            let deleteId = null;
            let deleteType = null; // 'weather' или 'city'
            let currentTab = 'weatherTab';

            // Загрузка при запуске
            document.addEventListener('DOMContentLoaded', function() {{
                loadCities();
                loadWeather();
                loadStorageInfo();

                // Добавляем обработчики клавиш для поиска
                document.getElementById('searchInput').addEventListener('keyup', filterWeather);
                document.getElementById('cityFilter').addEventListener('change', filterWeather);
                document.getElementById('conditionFilter').addEventListener('change', filterWeather);

                // Загружаем города для теста парсера
                loadCitiesForTest();
            }});

            // Переключение вкладок
            function switchTab(tabName) {{
                // Скрываем все вкладки
                document.querySelectorAll('.tab-content').forEach(tab => {{
                    tab.classList.remove('active');
                }});

                // Убираем активный класс у всех кнопок
                document.querySelectorAll('.tab-btn').forEach(btn => {{
                    btn.classList.remove('active');
                }});

                // Показываем выбранную вкладку
                document.getElementById(tabName).classList.add('active');

                // Активируем кнопку
                event.target.classList.add('active');
                currentTab = tabName;

                // Если переключились на вкладку управления городами, обновляем список
                if (tabName === 'citiesTab') {{
                    loadAllCities();
                }}
            }}

            // Загрузка списка городов для парсинга
            async function loadCities() {{
                try {{
                    const response = await fetch('/weather/cities');
                    const data = await response.json();
                    allCities = data.cities;
                    populateCityGrid(data.cities);
                }} catch (error) {{
                    console.error('Ошибка загрузки городов:', error);
                }}
            }}

            // Загрузка всех городов для управления
            async function loadAllCities() {{
                try {{
                    const response = await fetch('/cities');
                    const cities = await response.json();
                    populateCitiesTable(cities);
                }} catch (error) {{
                    console.error('Ошибка загрузки всех городов:', error);
                    showToast('Ошибка загрузки городов: ' + error.message, 'error');
                }}
            }}

            // Загрузка городов для теста парсера
            async function loadCitiesForTest() {{
                try {{
                    const response = await fetch('/cities');
                    const cities = await response.json();
                    const select = document.getElementById('testCitySelect');

                    // Очищаем select
                    select.innerHTML = '<option value="">Выберите город...</option>';

                    // Добавляем города
                    cities.forEach(city => {{
                        const option = document.createElement('option');
                        option.value = city.slug;
                        option.textContent = `${{city.name}} (${{city.slug}})`;
                        select.appendChild(option);
                    }});
                }} catch (error) {{
                    console.error('Ошибка загрузки городов для теста:', error);
                }}
            }}

            // Заполнение сетки городов
            function populateCityGrid(cities) {{
                const cityGrid = document.getElementById('cityGrid');
                cityGrid.innerHTML = '';

                Object.entries(cities).forEach(([slug, name]) => {{
                    const cityCard = document.createElement('div');
                    cityCard.className = 'city-card';
                    cityCard.innerHTML = `
                        <div class="city-name">${{name}}</div>
                        <div class="city-slug">${{slug}}</div>
                    `;
                    cityCard.onclick = () => parseCity(slug);
                    cityGrid.appendChild(cityCard);
                }});
            }}

            // Заполнение таблицы городов для управления
            function populateCitiesTable(cities) {{
                const tbody = document.getElementById('citiesTableBody');
                tbody.innerHTML = '';

                cities.forEach(city => {{
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${{city.id}}</td>
                        <td>${{city.name}}</td>
                        <td>
                            <span class="city-slug">${{city.slug}}</span>
                        </td>
                        <td>
                            <span class="badge ${{city.is_active ? 'status-active' : 'status-inactive'}}">
                                ${{city.is_active ? 'Активен' : 'Неактивен'}}
                            </span>
                        </td>
                        <td>
                            <div class="action-btns">
                                <button class="action-btn action-btn-edit" onclick="editCity(${{city.id}})" title="Редактировать">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="action-btn action-btn-delete" onclick="showDeleteModal(${{city.id}}, 'city', '${{city.name}}')" title="Удалить">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(row);
                }});
            }}

            // Парсинг одного города
            async function parseCity(citySlug) {{
                const cityName = allCities[citySlug];
                if (!confirm(`Запустить парсинг погоды для города "${{cityName}}"?"`)) return;

                showLoader();
                try {{
                    const response = await fetch('/weather/parse', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ city_slug: citySlug }})
                    }});

                    if (response.ok) {{
                        const data = await response.json();
                        showToast(`Парсинг для города "${{cityName}}" запущен!`, 'success');

                        // Анимируем кнопку города
                        const cityCards = document.querySelectorAll('.city-card');
                        Object.keys(allCities).forEach((slug, index) => {{
                            if (slug === citySlug && cityCards[index]) {{
                                cityCards[index].classList.add('active');
                                setTimeout(() => cityCards[index].classList.remove('active'), 2000);
                            }}
                        }});

                        setTimeout(async () => {{
                            await loadWeather();
                            await loadStorageInfo();
                            showToast(`Данные для города "${{cityName}}" обновлены!`, 'success');
                        }}, 5000);
                    }} else {{
                        const error = await response.text();
                        showToast('Ошибка запуска парсера: ' + error, 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            // Тестирование парсера
            async function testParser() {{
                const citySlug = document.getElementById('testCitySelect').value;
                if (!citySlug) {{
                    showToast('Выберите город для теста', 'error');
                    return;
                }}

                const parserLoader = document.getElementById('parserLoader');
                const parserResult = document.getElementById('parserResult');

                parserLoader.style.display = 'flex';
                parserResult.innerHTML = '';

                try {{
                    const response = await fetch(`/weather/parser/test/${{citySlug}}`);
                    const data = await response.json();

                    if (data.success) {{
                        parserResult.innerHTML = `
                            <div style="background: #f8f9fa; padding: 20px; border-radius: var(--radius);">
                                <h4><i class="fas fa-check-circle" style="color: #28a745;"></i> Парсер работает!</h4>
                                <p><strong>Город:</strong> ${{data.city}}</p>
                                <p><strong>URL:</strong> <a href="${{data.url}}" target="_blank">${{data.url}}</a></p>
                                <p><strong>Найдено записей:</strong> ${{data.data_count}}</p>
                                <p><strong>Пример данных:</strong></p>
                                <pre style="background: white; padding: 10px; border-radius: 5px; max-height: 300px; overflow: auto;">${{JSON.stringify(data.data, null, 2)}}</pre>
                            </div>
                        `;
                    }} else {{
                        parserResult.innerHTML = `
                            <div style="background: #f8d7da; padding: 20px; border-radius: var(--radius);">
                                <h4><i class="fas fa-exclamation-circle" style="color: #dc3545;"></i> Ошибка парсера</h4>
                                <p><strong>Город:</strong> ${{data.city}}</p>
                                <p><strong>Ошибка:</strong> ${{data.error}}</p>
                                <p><strong>Сообщение:</strong> ${{data.message}}</p>
                            </div>
                        `;
                    }}
                }} catch (error) {{
                    parserResult.innerHTML = `
                        <div style="background: #f8d7da; padding: 20px; border-radius: var(--radius);">
                            <h4><i class="fas fa-exclamation-circle" style="color: #dc3545;"></i> Ошибка сети</h4>
                            <p>${{error.message}}</p>
                        </div>
                    `;
                }} finally {{
                    parserLoader.style.display = 'none';
                }}
            }}

            // Загрузка погодных данных
            async function loadWeather() {{
                showLoader();
                try {{
                    const response = await fetch('/weather');
                    if (response.ok) {{
                        const data = await response.json();
                        allWeatherData = data.records || [];
                        updateStats(allWeatherData);
                        renderWeatherTable(allWeatherData);
                        updateFilterOptions(allWeatherData);
                    }} else {{
                        showToast('Ошибка загрузки данных', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            // Отрисовка таблицы с данными
            function renderWeatherTable(data) {{
                const tbody = document.getElementById('weatherTableBody');
                const filteredCount = document.getElementById('filteredCount');
                const totalCount = document.getElementById('totalCount');
                const emptyState = document.getElementById('emptyState');

                tbody.innerHTML = '';
                filteredCount.textContent = data.length;
                totalCount.textContent = allWeatherData.length;

                if (data.length === 0) {{
                    emptyState.style.display = 'block';
                    document.getElementById('weatherTable').style.display = 'none';
                    return;
                }} else {{
                    emptyState.style.display = 'none';
                    document.getElementById('weatherTable').style.display = 'table';
                }}

                data.forEach(record => {{
                    const row = document.createElement('tr');
                    const createdDate = new Date(record.created_at);
                    const timeString = createdDate.toLocaleTimeString('ru-RU', {{
                        hour: '2-digit',
                        minute: '2-digit'
                    }});
                    const dateString = createdDate.toLocaleDateString('ru-RU');

                    // Определяем класс для времени суток
                    const timeClass = getTimeBadgeClass(record.time_of_day);

                    // Определяем класс для температуры
                    const tempClass = getTempClass(record.temperature);

                    // Определяем иконку для условий
                    const conditionIcon = getConditionIcon(record.condition);

                    row.innerHTML = `
                        <td class="fw-bold">${{record.id}}</td>
                        <td>${{record.date}}</td>
                        <td>
                            <span class="badge ${{timeClass}}">
                                ${{record.time_of_day}}
                            </span>
                        </td>
                        <td>
                            <span class="condition-badge">
                                <i class="fas fa-city"></i>
                                ${{record.city}}
                            </span>
                        </td>
                        <td>
                            <span class="temp-badge ${{tempClass}}">
                                ${{record.temperature}}
                            </span>
                        </td>
                        <td>
                            <span class="condition-badge">
                                <i class="${{conditionIcon}}"></i>
                                ${{record.condition}}
                            </span>
                        </td>
                        <td>
                            <small>${{dateString}}<br>${{timeString}}</small>
                        </td>
                        <td>
                            <div class="action-btns">
                                <button class="action-btn action-btn-edit" onclick="editWeather(${{record.id}})" title="Редактировать">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="action-btn action-btn-delete" onclick="showDeleteModal(${{record.id}}, 'weather', '${{record.city}} - ${{record.date}} ${{record.time_of_day}}')" title="Удалить">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(row);
                }});
            }}

            // Обновление статистики
            function updateStats(data) {{
                document.getElementById('totalRecords').textContent = data.length;

                const cities = [...new Set(data.map(r => r.city))];
                document.getElementById('totalCities').textContent = cities.length;

                // Рассчитываем среднюю температуру
                const temps = data.map(r => {{
                    const temp = parseInt(r.temperature) || 0;
                    return temp;
                }});
                const avgTemp = temps.length > 0 ?
                    Math.round(temps.reduce((a, b) => a + b) / temps.length) : 0;
                document.getElementById('avgTemp').textContent = `${{avgTemp}}°C`;

                // Последнее обновление
                if (data.length > 0) {{
                    const latest = data[data.length - 1];
                    const now = new Date();
                    const timeString = now.toLocaleTimeString('ru-RU', {{
                        hour: '2-digit',
                        minute: '2-digit'
                    }});
                    document.getElementById('lastUpdate').textContent = timeString;
                }}
            }}

            // Обновление опций фильтров
            function updateFilterOptions(data) {{
                const citySelect = document.getElementById('cityFilter');
                const cities = [...new Set(data.map(r => r.city))];

                // Очищаем существующие опции, кроме первой
                while (citySelect.options.length > 1) {{
                    citySelect.remove(1);
                }}

                cities.forEach(city => {{
                    const option = document.createElement('option');
                    option.value = city;
                    option.textContent = city;
                    citySelect.appendChild(option);
                }});
            }}

            // Фильтрация данных
            function filterWeather() {{
                const searchText = document.getElementById('searchInput').value.toLowerCase();
                const selectedCity = document.getElementById('cityFilter').value;
                const selectedCondition = document.getElementById('conditionFilter').value;

                let filtered = allWeatherData;

                if (searchText) {{
                    filtered = filtered.filter(r =>
                        r.city.toLowerCase().includes(searchText) ||
                        r.condition.toLowerCase().includes(searchText)
                    );
                }}

                if (selectedCity) {{
                    filtered = filtered.filter(r => r.city === selectedCity);
                }}

                if (selectedCondition) {{
                    filtered = filtered.filter(r =>
                        r.condition.toLowerCase().includes(selectedCondition)
                    );
                }}

                renderWeatherTable(filtered);
            }}

            // Сброс фильтров
            function resetFilters() {{
                document.getElementById('searchInput').value = '';
                document.getElementById('cityFilter').value = '';
                document.getElementById('conditionFilter').value = '';
                filterWeather();
            }}

            // CRUD операции для погоды
            function openCreateWeatherModal() {{
                document.getElementById('weatherModalTitle').textContent = 'Добавить запись о погоде';
                document.getElementById('weatherForm').reset();
                document.getElementById('recordId').value = '';

                // Устанавливаем сегодняшнюю дату по умолчанию
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('date').value = today;

                document.getElementById('weatherModal').style.display = 'flex';
            }}

            function closeWeatherModal() {{
                document.getElementById('weatherModal').style.display = 'none';
            }}

            async function editWeather(id) {{
                showLoader();
                try {{
                    const response = await fetch(`/weather/${{id}}`);
                    if (response.ok) {{
                        const record = await response.json();

                        document.getElementById('weatherModalTitle').textContent = 'Редактировать запись';
                        document.getElementById('recordId').value = record.id;
                        document.getElementById('date').value = record.date;
                        document.getElementById('time_of_day').value = record.time_of_day;
                        document.getElementById('city').value = record.city;
                        document.getElementById('temperature').value = record.temperature;
                        document.getElementById('condition').value = record.condition;

                        document.getElementById('weatherModal').style.display = 'flex';
                    }} else {{
                        showToast('Ошибка загрузки записи', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            async function saveWeather() {{
                const form = document.getElementById('weatherForm');
                if (!form.checkValidity()) {{
                    form.reportValidity();
                    return;
                }}

                const recordId = document.getElementById('recordId').value;
                const record = {{
                    date: document.getElementById('date').value,
                    time_of_day: document.getElementById('time_of_day').value,
                    city: document.getElementById('city').value,
                    temperature: document.getElementById('temperature').value,
                    condition: document.getElementById('condition').value
                }};

                showLoader();
                try {{
                    let response;
                    if (recordId) {{
                        // Обновление
                        response = await fetch(`/weather/${{recordId}}`, {{
                            method: 'PATCH',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify(record)
                        }});
                    }} else {{
                        // Создание
                        response = await fetch('/weather', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify(record)
                        }});
                    }}

                    if (response.ok) {{
                        showToast(recordId ? 'Запись обновлена!' : 'Запись создана!', 'success');
                        closeWeatherModal();
                        await loadWeather();
                        await loadStorageInfo();
                    }} else {{
                        const error = await response.text();
                        showToast('Ошибка сохранения: ' + error, 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            // CRUD операции для городов
            function openCreateCityModal() {{
                document.getElementById('cityModalTitle').textContent = 'Добавить город';
                document.getElementById('cityForm').reset();
                document.getElementById('cityId').value = '';
                document.getElementById('cityIsActive').checked = true;

                document.getElementById('cityModal').style.display = 'flex';
            }}

            function closeCityModal() {{
                document.getElementById('cityModal').style.display = 'none';
            }}

            async function editCity(id) {{
                showLoader();
                try {{
                    const response = await fetch(`/cities/${{id}}`);
                    if (response.ok) {{
                        const city = await response.json();

                        document.getElementById('cityModalTitle').textContent = 'Редактировать город';
                        document.getElementById('cityId').value = city.id;
                        document.getElementById('cityName').value = city.name;
                        document.getElementById('citySlug').value = city.slug;
                        document.getElementById('cityIsActive').checked = city.is_active;

                        document.getElementById('cityModal').style.display = 'flex';
                    }} else {{
                        showToast('Ошибка загрузки города', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            async function saveCity() {{
                const form = document.getElementById('cityForm');
                if (!form.checkValidity()) {{
                    form.reportValidity();
                    return;
                }}

                const cityId = document.getElementById('cityId').value;
                const city = {{
                    name: document.getElementById('cityName').value,
                    slug: document.getElementById('citySlug').value,
                    is_active: document.getElementById('cityIsActive').checked
                }};

                showLoader();
                try {{
                    let response;
                    if (cityId) {{
                        // Обновление
                        response = await fetch(`/cities/${{cityId}}`, {{
                            method: 'PATCH',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify(city)
                        }});
                    }} else {{
                        // Создание
                        response = await fetch('/cities', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify(city)
                        }});
                    }}

                    if (response.ok) {{
                        showToast(cityId ? 'Город обновлен!' : 'Город создан!', 'success');
                        closeCityModal();

                        // Обновляем списки городов
                        await loadCities();
                        await loadAllCities();
                        await loadCitiesForTest();
                        await loadStorageInfo();

                        // Переключаемся на вкладку управления городами
                        switchTab('citiesTab');
                    }} else {{
                        const error = await response.json();
                        showToast('Ошибка сохранения: ' + error.detail, 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            // Удаление
            function showDeleteModal(id, type, name) {{
                deleteId = id;
                deleteType = type;

                if (type === 'weather') {{
                    document.getElementById('deleteMessage').textContent = `Вы собираетесь удалить запись о погоде: "${{name}}". Это действие нельзя отменить.`;
                }} else if (type === 'city') {{
                    document.getElementById('deleteMessage').textContent = `Вы собираетесь удалить город: "${{name}}". Это действие нельзя отменить.`;
                }}

                document.getElementById('deleteModal').style.display = 'flex';
            }}

            function closeDeleteModal() {{
                deleteId = null;
                deleteType = null;
                document.getElementById('deleteModal').style.display = 'none';
            }}

            async function confirmDelete() {{
                showLoader();
                try {{
                    let response;
                    let url;

                    if (deleteType === 'weather') {{
                        url = `/weather/${{deleteId}}`;
                    }} else if (deleteType === 'city') {{
                        url = `/cities/${{deleteId}}`;
                    }}

                    response = await fetch(url, {{
                        method: 'DELETE'
                    }});

                    if (response.ok || response.status === 204) {{
                        showToast(deleteType === 'weather' ? 'Запись удалена!' : 'Город удален!', 'success');
                        closeDeleteModal();

                        if (deleteType === 'weather') {{
                            await loadWeather();
                            await loadStorageInfo();
                        }} else if (deleteType === 'city') {{
                            await loadCities();
                            await loadAllCities();
                            await loadCitiesForTest();
                            await loadStorageInfo();
                        }}
                    }} else {{
                        showToast('Ошибка удаления', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                    deleteId = null;
                    deleteType = null;
                }}
            }}

            // Вспомогательные функции
            function getTimeBadgeClass(time) {{
                const classes = {{
                    'утро': 'badge-time-morning',
                    'день': 'badge-time-day',
                    'вечер': 'badge-time-evening',
                    'ночь': 'badge-time-night',
                    'сейчас': 'badge-time-now'
                }};
                return classes[time] || 'badge-time-day';
            }}

            function getTempClass(temp) {{
                const tempNum = parseInt(temp) || 0;
                if (tempNum > 25) return 'temp-hot';
                if (tempNum > 15) return 'temp-warm';
                if (tempNum > 5) return 'temp-mild';
                if (tempNum > -5) return 'temp-cool';
                return 'temp-cold';
            }}

            function getConditionIcon(condition) {{
                const conditionLower = condition.toLowerCase();
                if (conditionLower.includes('ясно')) return 'fas fa-sun';
                if (conditionLower.includes('облачно')) return 'fas fa-cloud';
                if (conditionLower.includes('дождь')) return 'fas fa-cloud-rain';
                if (conditionLower.includes('снег')) return 'fas fa-snowflake';
                if (conditionLower.includes('туман')) return 'fas fa-smog';
                return 'fas fa-cloud';
            }}

            // Управление UI
            function showLoader() {{
                document.getElementById('loader').style.display = 'flex';
            }}

            function hideLoader() {{
                document.getElementById('loader').style.display = 'none';
            }}

            function showToast(message, type = 'success') {{
                const toast = document.getElementById('successToast');
                document.getElementById('toastMessage').textContent = message;

                toast.className = `toast toast-${{type}}`;
                toast.style.display = 'flex';

                setTimeout(hideToast, 5000);
            }}

            function hideToast() {{
                document.getElementById('successToast').style.display = 'none';
            }}

            // Автообновление каждые 5 минут
            setInterval(loadWeather, 5 * 60 * 1000);
            setInterval(loadStorageInfo, 10 * 60 * 1000);

            // Закрытие модальных окон при клике вне их
            window.onclick = function(event) {{
                const weatherModal = document.getElementById('weatherModal');
                const cityModal = document.getElementById('cityModal');
                const deleteModal = document.getElementById('deleteModal');
                const storageModal = document.getElementById('storageModal');

                if (event.target === weatherModal) {{
                    closeWeatherModal();
                }}

                if (event.target === cityModal) {{
                    closeCityModal();
                }}

                if (event.target === deleteModal) {{
                    closeDeleteModal();
                }}

                if (event.target === storageModal) {{
                    closeStorageModal();
                }}
            }}

            // ========== ФУНКЦИИ ДЛЯ ХРАНИЛИЩА (НОВЫЕ) ==========

            // Загрузка информации о хранилище
            async function loadStorageInfo() {{
                try {{
                    const response = await fetch('/storage/info');
                    if (response.ok) {{
                        const data = await response.json();

                        // Обновляем статистику в шапке
                        document.getElementById('totalRecords').textContent = data.total_records || 0;
                        document.getElementById('archivedRecords').textContent = data.archived_records || 0;
                        document.getElementById('backupCount').textContent = data.backup_count || 0;
                        document.getElementById('storageSize').textContent = `${{(data.total_size_mb || 0).toFixed(1)}} MB`;

                        // Обновляем детальную статистику
                        updateStorageStats(data);

                        // Обновляем список бэкапов
                        if (data.recent_backups) {{
                            updateBackupList(data.recent_backups);
                        }}

                        return data;
                    }}
                }} catch (error) {{
                    console.error('Ошибка загрузки информации о хранилище:', error);
                }}
            }}

            function updateStorageStats(data) {{
                const statsDiv = document.getElementById('storageStats');

                if (!data || data.error) {{
                    statsDiv.innerHTML = '<p style="color: #dc3545;">Ошибка загрузки статистики</p>';
                    return;
                }}

                // Расчет процента архивации
                const archivePercent = data.total_records > 0 
                    ? Math.round((data.archived_records / data.total_records) * 100) 
                    : 0;

                // Расчет процента использования
                const maxStorageMB = 1000; // Максимальный предполагаемый размер
                const usagePercent = Math.min(Math.round((data.total_size_mb / maxStorageMB) * 100), 100);

                statsDiv.innerHTML = `
                    <div class="storage-stats-grid">
                        <div class="storage-stat">
                            <div class="storage-stat-label">Всего записей</div>
                            <div class="storage-stat-value">${{data.total_records.toLocaleString()}}</div>
                        </div>
                        <div class="storage-stat">
                            <div class="storage-stat-label">В архиве</div>
                            <div class="storage-stat-value">${{data.archived_records.toLocaleString()}}</div>
                        </div>
                        <div class="storage-stat">
                            <div class="storage-stat-label">Активные</div>
                            <div class="storage-stat-value">${{data.active_records.toLocaleString()}}</div>
                        </div>
                        <div class="storage-stat">
                            <div class="storage-stat-label">Средняя температура</div>
                            <div class="storage-stat-value">${{data.avg_temperature}}°C</div>
                        </div>
                    </div>

                    <div class="progress-container">
                        <div class="progress-label">
                            <span>Архивация: ${{archivePercent}}%</span>
                            <span>${{data.archived_records}} / ${{data.total_records}}</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${{archivePercent}}%;"></div>
                        </div>
                    </div>

                    <div class="progress-container">
                        <div class="progress-label">
                            <span>Использование хранилища: ${{usagePercent}}%</span>
                            <span>${{data.total_size_mb.toFixed(1)}} MB</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${{usagePercent}}%;"></div>
                        </div>
                    </div>

                    <div style="margin-top: 20px; color: #6c757d; font-size: 0.9rem;">
                        <p><i class="fas fa-info-circle"></i> Настройки архивации: записи старше ${{data.settings.archive_after_days}} дней</p>
                        <p><i class="fas fa-info-circle"></i> Бэкапы хранятся: ${{data.settings.backup_retention_days}} дней</p>
                        <p><i class="fas fa-info-circle"></i> Директория бэкапов: ${{data.settings.backup_dir}}</p>
                    </div>
                `;
            }}

            function updateBackupList(backups) {{
                const backupsDiv = document.getElementById('recentBackups');

                if (!backups || backups.length === 0) {{
                    backupsDiv.innerHTML = `
                        <div style="text-align: center; padding: 40px; color: #6c757d;">
                            <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 15px;"></i>
                            <p>Бэкапы еще не созданы</p>
                        </div>
                    `;
                    return;
                }}

                let html = '';
                backups.forEach(backup => {{
                    const date = new Date(backup.created_at);
                    const dateStr = date.toLocaleDateString('ru-RU');
                    const timeStr = date.toLocaleTimeString('ru-RU', {{hour: '2-digit', minute: '2-digit'}});

                    html += `
                        <div class="backup-item">
                            <div class="backup-info">
                                <div class="backup-name">${{backup.filename}}</div>
                                <div class="backup-meta">
                                    <span><i class="far fa-calendar"></i> ${{dateStr}} ${{timeStr}}</span>
                                    <span><i class="fas fa-weight"></i> ${{backup.size_mb.toFixed(2)}} MB</span>
                                    <span><i class="fas fa-list"></i> ${{backup.record_count}} записей</span>
                                </div>
                            </div>
                            <div>
                                <span class="backup-badge badge-${{backup.type}}">${{backup.type === 'full' ? 'Полный' : 'Инкремент'}}</span>
                                <span class="backup-badge badge-${{backup.status}}">${{backup.status === 'completed' ? 'Успешно' : 'Ошибка'}}</span>
                            </div>
                        </div>
                    `;
                }});

                backupsDiv.innerHTML = html;
            }}

            // Функции управления хранилищем
            async function runArchive() {{
                if (!confirm('Запустить архивацию записей старше 30 дней?')) return;

                showLoader();
                try {{
                    const response = await fetch('/storage/archive', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ days_old: 30 }})
                    }});

                    if (response.ok) {{
                        const result = await response.json();
                        showToast(`Архивация завершена: ${{result.archived}} записей архивировано`, 'success');

                        // Обновляем информацию
                        setTimeout(loadStorageInfo, 2000);
                        setTimeout(loadWeather, 3000);
                    }} else {{
                        showToast('Ошибка архивации', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            async function createBackup(type) {{
                const typeName = type === 'full' ? 'полный' : 'инкрементальный';
                if (!confirm(`Создать ${{typeName}} бэкап данных?`)) return;

                showLoader();
                try {{
                    const response = await fetch('/storage/backup', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ backup_type: type }})
                    }});

                    if (response.ok) {{
                        const result = await response.json();
                        showToast(`${{typeName === 'полный' ? 'Полный' : 'Инкрементальный'}} бэкап создан успешно!`, 'success');

                        // Обновляем информацию через 5 секунд
                        setTimeout(loadStorageInfo, 5000);
                    }} else {{
                        showToast('Ошибка создания бэкапа', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            async function cleanupBackups() {{
                if (!confirm('Удалить бэкапы старше 90 дней? Это действие нельзя отменить.')) return;

                showLoader();
                try {{
                    const response = await fetch('/storage/cleanup', {{
                        method: 'POST'
                    }});

                    if (response.ok) {{
                        const result = await response.json();
                        showToast(`Очистка завершена: удалено ${{result.deleted_count}} бэкапов`, 'success');

                        // Обновляем информацию
                        setTimeout(loadStorageInfo, 2000);
                    }} else {{
                        showToast('Ошибка очистки бэкапов', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            async function optimizeDatabase() {{
                if (!confirm('Выполнить оптимизацию базы данных? Это может занять несколько минут.')) return;

                showLoader();
                try {{
                    const response = await fetch('/storage/optimize', {{
                        method: 'POST'
                    }});

                    if (response.ok) {{
                        const result = await response.json();
                        showToast('Оптимизация базы данных завершена!', 'success');
                    }} else {{
                        showToast('Ошибка оптимизации', 'error');
                    }}
                }} catch (error) {{
                    showToast('Ошибка сети: ' + error.message, 'error');
                }} finally {{
                    hideLoader();
                }}
            }}

            async function viewArchive() {{
                openStorageModal();
                const modalContent = document.getElementById('storageModalContent');
                modalContent.innerHTML = '<div class="loader"><div class="spinner"></div></div>';

                try {{
                    const response = await fetch('/storage/archive/list?limit=50');
                    if (response.ok) {{
                        const data = await response.json();

                        let html = '<h4 style="margin-bottom: 20px;"><i class="fas fa-archive"></i> Архивные записи</h4>';

                        if (data.records.length === 0) {{
                            html += '<p style="text-align: center; color: #6c757d; padding: 40px;">Архив пуст</p>';
                        }} else {{
                            html += `
                                <div style="overflow-x: auto;">
                                    <table class="archive-table">
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Дата</th>
                                                <th>Время</th>
                                                <th>Город</th>
                                                <th>Температура</th>
                                                <th>Архивировано</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                            `;

                            data.records.forEach(record => {{
                                const archivedDate = new Date(record.archived_at);
                                const archivedStr = archivedDate.toLocaleDateString('ru-RU') + ' ' + archivedDate.toLocaleTimeString('ru-RU', {{hour: '2-digit', minute: '2-digit'}});

                                html += `
                                    <tr>
                                        <td>${{record.original_id}}</td>
                                        <td>${{record.date}}</td>
                                        <td>${{record.time_of_day}}</td>
                                        <td>${{record.city}}</td>
                                        <td>${{record.temperature}}</td>
                                        <td>${{archivedStr}}</td>
                                    </tr>
                                `;
                            }});

                            html += `
                                        </tbody>
                                    </table>
                                </div>
                                <p style="margin-top: 15px; color: #6c757d; text-align: center;">
                                    Показано ${{data.records.length}} из ${{data.total}} записей
                                </p>
                            `;
                        }}

                        modalContent.innerHTML = html;
                    }}
                }} catch (error) {{
                    modalContent.innerHTML = '<p style="color: #dc3545;">Ошибка загрузки архива: ' + error.message + '</p>';
                }}
            }}

            async function viewBackups() {{
                openStorageModal();
                const modalContent = document.getElementById('storageModalContent');
                modalContent.innerHTML = '<div class="loader"><div class="spinner"></div></div>';

                try {{
                    const response = await fetch('/storage/backup/list?limit=20');
                    if (response.ok) {{
                        const data = await response.json();

                        let html = '<h4 style="margin-bottom: 20px;"><i class="fas fa-save"></i> Список бэкапов</h4>';

                        if (data.backups.length === 0) {{
                            html += '<p style="text-align: center; color: #6c757d; padding: 40px;">Бэкапы отсутствуют</p>';
                        }} else {{
                            data.backups.forEach(backup => {{
                                const date = new Date(backup.created_at);
                                const dateStr = date.toLocaleDateString('ru-RU');
                                const timeStr = date.toLocaleTimeString('ru-RU', {{hour: '2-digit', minute: '2-digit'}});

                                html += `
                                    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <div>
                                                <div style="font-weight: 600;">${{backup.filename}}</div>
                                                <div style="font-size: 0.9rem; color: #6c757d; margin-top: 5px;">
                                                    <span><i class="far fa-calendar"></i> ${{dateStr}} ${{timeStr}}</span>
                                                    <span style="margin-left: 15px;"><i class="fas fa-weight"></i> ${{backup.size_mb.toFixed(2)}} MB</span>
                                                    <span style="margin-left: 15px;"><i class="fas fa-list"></i> ${{backup.record_count}} записей</span>
                                                </div>
                                            </div>
                                            <div style="display: flex; gap: 10px;">
                                                <span class="backup-badge badge-${{backup.backup_type}}" style="margin-right: 10px;">
                                                    ${{backup.backup_type === 'full' ? 'Полный' : 'Инкремент'}}
                                                </span>
                                                <span class="backup-badge badge-${{backup.status}}">
                                                    ${{backup.status === 'completed' ? 'Успешно' : backup.status === 'failed' ? 'Ошибка' : 'В процессе'}}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                `;
                            }});

                            html += `
                                <p style="margin-top: 15px; color: #6c757d; text-align: center;">
                                    Показано ${{data.backups.length}} из ${{data.total}} бэкапов
                                </p>
                            `;
                        }}

                        modalContent.innerHTML = html;
                    }}
                }} catch (error) {{
                    modalContent.innerHTML = '<p style="color: #dc3545;">Ошибка загрузки списка бэкапов: ' + error.message + '</p>';
                }}
            }}

            // Модальное окно хранилища
            function openStorageModal() {{
                document.getElementById('storageModal').style.display = 'flex';
            }}

            function closeStorageModal() {{
                document.getElementById('storageModal').style.display = 'none';
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    from sqlalchemy import text
    from db import engine

    try:
        # Проверяем подключение к базе данных
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    # Проверяем доступность директории бэкапов
    from pathlib import Path
    backup_dir = Path("./backups")
    backup_dir_status = "exists" if backup_dir.exists() else "missing"

    return {
        "status": "healthy",
        "service": "weather-api-s3-edition",
        "timestamp": time.time(),
        "database": db_status,
        "storage": {
            "backup_dir": backup_dir_status,
            "backup_dir_path": str(backup_dir.absolute())
        },
        "version": "2.0"
    }