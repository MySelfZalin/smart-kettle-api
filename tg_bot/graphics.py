import io
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns

from fast_api.api.metrics import metrics_client

sns.set_theme(style="darkgrid")


async def generate_graphics_image() -> tuple[io.BytesIO, dict]:
    times, temps, statuses = await metrics_client.get_data_for_period(24)

    dates = [datetime.fromtimestamp(t) for t in times]

    # Настраиваем темную тему под стиль Telegram
    plt.style.use("dark_background")
    bg_color = "#1c1c1d"
    
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=bg_color)
    ax.set_facecolor(bg_color)

    if temps:
        # Основная линия и градиентная заливка
        line_color = "#ff7e67"  # Теплый оранжевый цвет
        ax.plot(dates, temps, color=line_color, linewidth=2.5, zorder=3)
        ax.fill_between(dates, 0, temps, color=line_color, alpha=0.15, zorder=2)
        
        # Точка и подпись текущей (последней) температуры
        last_temp = temps[-1]
        last_date = dates[-1]
        ax.scatter(last_date, last_temp, color="#ffffff", zorder=5, s=60, edgecolors=line_color, linewidths=2)
        ax.annotate(f"{last_temp:.1f}°C", 
                    xy=(last_date, last_temp), 
                    xytext=(-5, 15), 
                    textcoords="offset points", 
                    color="#ffffff", 
                    fontweight="bold",
                    fontsize=12,
                    ha='center')

    ax.set_title("Температура воды (последние 24 часа)", fontsize=14, pad=20, color="#ffffff", fontweight="bold")
    ax.set_ylabel("Температура (°C)", fontsize=11, color="#aaaaaa")
    
    # Ось X и Y
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_ylim(0, 110)

    # Убираем лишние рамки, делаем красивую сетку
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#333333')
    ax.spines['bottom'].set_color('#333333')
    ax.tick_params(colors='#aaaaaa', labelsize=10)
    ax.yaxis.grid(True, linestyle='--', alpha=0.15, color='#ffffff')
    ax.xaxis.grid(False)

    fig.autofmt_xdate(rotation=0, ha='center')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=bg_color, edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    stats = {}
    for period_name, days in [("24 часа", 1), ("7 дней", 7), ("30 дней", 30), ("1 год", 365)]:
        kwh, cost = await metrics_client.get_energy_consumption(days)
        stats[period_name] = {"kwh": round(kwh, 2), "cost": round(cost, 2)}

    return buf, stats
