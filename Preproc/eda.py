"""
EDA для датасета IEEE-CIS Fraud Detection.
Читает весь train_transaction.csv (590k строк).
Сохраняет графики в docs/images/.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Пути ──────────────────────────────────────────────────────────────────────
DATA_PATH = 'Data/train_transaction.csv'
OUT_DIR   = 'docs/images'
os.makedirs(OUT_DIR, exist_ok=True)

# ── Загрузка (только нужные колонки, весь датасет) ────────────────────────────
COLS = ['TransactionAmt', 'ProductCD', 'isFraud']
df = pd.read_csv(DATA_PATH, usecols=COLS)

print(f"Загружено строк : {len(df):,}")
print(f"Фрод            : {df['isFraud'].sum():,}  ({df['isFraud'].mean()*100:.2f}%)")
print()

# ── Статистика TransactionAmt по классам ──────────────────────────────────────
print("=== TransactionAmt по классам ===")
print(df.groupby('isFraud')['TransactionAmt'].describe().round(2))
print()

# ── Фрод-рейт по ProductCD ────────────────────────────────────────────────────
_grp = df.groupby('ProductCD')['isFraud']
prod: pd.DataFrame = pd.DataFrame({
    'fraud_count': _grp.sum(),
    'total':       _grp.count(),
    'fraud_rate':  (_grp.mean() * 100).round(2),
})
print("=== Фрод-рейт по ProductCD ===")
print(prod.sort_values(by='fraud_rate', ascending=False))
print()

# ══════════════════════════════════════════════════════════════════════════════
# График 1: Распределение классов + фрод-рейт по ProductCD
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# --- Pie: баланс классов ---
counts = df['isFraud'].value_counts().sort_index()
axes[0].pie(
    counts,
    labels=['Легитимные (0)', 'Мошеннические (1)'],
    autopct='%1.1f%%',
    colors=['#4CAF50', '#F44336'],
    startangle=90,
    textprops={'fontsize': 12},
    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
)
axes[0].set_title('Распределение классов (isFraud)', fontsize=13, fontweight='bold')

# --- Bar: фрод-рейт по ProductCD ---
prod_sorted: pd.DataFrame = prod.sort_values(by='fraud_rate', ascending=True)
colors = ['#F44336' if r > 4 else '#FF9800' if r > 3 else '#4CAF50'
          for r in prod_sorted['fraud_rate']]
bars = axes[1].barh(prod_sorted.index, prod_sorted['fraud_rate'], color=colors, edgecolor='white')
axes[1].set_xlabel('Уровень фрода (%)', fontsize=11)
axes[1].set_title('Уровень фрода по типу продукта (ProductCD)', fontsize=13, fontweight='bold')
for bar, val in zip(bars, prod_sorted['fraud_rate']):
    axes[1].text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}%', va='center', fontsize=10)
axes[1].set_xlim(0, prod_sorted['fraud_rate'].max() * 1.25)

plt.tight_layout()
out1 = os.path.join(OUT_DIR, 'eda_class_distribution.png')
plt.savefig(out1, dpi=120, bbox_inches='tight')
plt.close()
print(f"Сохранён: {out1}")

# ══════════════════════════════════════════════════════════════════════════════
# График 2: Распределение TransactionAmt (обычная + log-шкала)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

legit = df[df['isFraud'] == 0]['TransactionAmt'].clip(upper=1000)
fraud = df[df['isFraud'] == 1]['TransactionAmt'].clip(upper=1000)

# Обычная шкала (обрезано до 1000 USD для читаемости)
axes[0].hist(legit, bins=60, alpha=0.6, color='#4CAF50', label='Легитимные', density=True)
axes[0].hist(fraud, bins=60, alpha=0.6, color='#F44336', label='Мошеннические', density=True)
axes[0].set_xlabel('Сумма транзакции, USD (clip=1000)', fontsize=11)
axes[0].set_ylabel('Плотность', fontsize=11)
axes[0].set_title('Распределение TransactionAmt', fontsize=13, fontweight='bold')
axes[0].legend(fontsize=10)

# Log-шкала
axes[1].hist(np.log1p(df[df['isFraud'] == 0]['TransactionAmt']),
             bins=60, alpha=0.6, color='#4CAF50', label='Легитимные', density=True)
axes[1].hist(np.log1p(df[df['isFraud'] == 1]['TransactionAmt']),
             bins=60, alpha=0.6, color='#F44336', label='Мошеннические', density=True)
axes[1].set_xlabel('log(1 + TransactionAmt)', fontsize=11)
axes[1].set_ylabel('Плотность', fontsize=11)
axes[1].set_title('TransactionAmt (log-шкала)', fontsize=13, fontweight='bold')
axes[1].legend(fontsize=10)

plt.tight_layout()
out2 = os.path.join(OUT_DIR, 'eda_transaction_amt.png')
plt.savefig(out2, dpi=120, bbox_inches='tight')
plt.close()
print(f"Сохранён: {out2}")

print("\nEDA завершён.")
