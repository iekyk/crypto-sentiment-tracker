import tkinter as tk
from tkinter import ttk
import mysql.connector
from mysql.connector import Error  # 🟢 안전한 DB 예외 처리를 위해 추가
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import subprocess
import sys
import numpy as np

# ─── CONFIGURATIONS & THEMES ──────────────────────────────────────────────
BG       = "#0A1628"
CARD     = "#112235"
CARD2    = "#0D1B2E"
CYAN     = "#00C4CC"
WHITE    = "#FFFFFF"
GRAY     = "#8BA4BE"
GRAY2    = "#4A6580"
GREEN    = "#00FF88"
RED      = "#FF4466"
YELLOW   = "#FFD700"
ORANGE   = "#FF8800"
FONT     = "Segoe UI"

COIN_COLORS = {
    "bitcoin":  "#F7931A",
    "ethereum": "#627EEA",
    "solana":   "#9945FF"
}

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Danish12",
        database="crypto_sentiment"
    )

class CryptoDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Market Health Analysis Engine")
        self.root.state("zoomed")
        self.root.configure(bg=BG)

        self.selected_coin = tk.StringVar(value="bitcoin")
        self.selected_days = tk.IntVar(value=365)
        self.clicked_date  = None

        self.build_ui()
        self.refresh_data()

    # ─── BUILD UI ─────────────────────────────────────────────────────────
    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=CYAN, height=55)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header,
                 text="  📊  Crypto Market Health Analysis Dashboard",
                 bg=CYAN, fg=BG, font=(FONT, 14, "bold")).pack(side="left", pady=12)
                 
        # 👤 계정 관리 버튼 추가 (헤더 우측 배치)
        btn_account = tk.Button(header, text="👤  Account Manage",
                                bg=CARD, fg=CYAN, font=(FONT, 10, "bold"),
                                relief="flat", padx=15, pady=5,
                                command=self.open_account_manage_window)
        btn_account.pack(side="right", padx=15, pady=10)

        tk.Label(header,
                 text="JBNU 2026 Database Design Term Project    ",
                 bg=CYAN, fg=BG, font=(FONT, 10)).pack(side="right", pady=12)

        # Instruction banner
        sub_banner = tk.Frame(self.root, bg=CARD2, pady=8)
        sub_banner.pack(fill="x")
        tk.Label(sub_banner,
                 text="  💡 TIP: Click anywhere on the left Price chart to analyse a specific historical date.",
                 bg=CARD2, fg=CYAN, font=(FONT, 10, "bold"), anchor="w").pack(fill="x", padx=10)

        # Controls
        controls = tk.Frame(self.root, bg=BG, pady=10)
        controls.pack(fill="x", padx=15)

        tk.Label(controls, text="Select Coin:", bg=BG, fg=GRAY,
                 font=(FONT, 10, "bold")).pack(side="left", padx=(0, 6))
        for text, val in [("Bitcoin (BTC)", "bitcoin"),
                           ("Ethereum (ETH)", "ethereum"),
                           ("Solana (SOL)", "solana")]:
            tk.Radiobutton(controls, text=text, variable=self.selected_coin,
                           value=val, bg=BG, fg=WHITE, selectcolor=CARD,
                           activebackground=BG, font=(FONT, 10),
                           command=self.reset_and_refresh).pack(side="left", padx=5)

        tk.Label(controls, text=" | ", bg=BG, fg=GRAY2,
                 font=(FONT, 12)).pack(side="left", padx=10)

        tk.Label(controls, text="Analysis Window:", bg=BG, fg=GRAY,
                 font=(FONT, 10, "bold")).pack(side="left", padx=(0, 6))
        for d_val in [90, 180, 270, 365]:
            tk.Radiobutton(controls, text=f"{d_val} Days",
                           variable=self.selected_days, value=d_val,
                           bg=BG, fg=WHITE, selectcolor=CARD,
                           activebackground=BG, font=(FONT, 10),
                           command=self.reset_and_refresh).pack(side="left", padx=5)

        tk.Button(controls, text="⬇  Fetch New Data",
                  bg=CARD, fg=CYAN, font=(FONT, 9, "bold"),
                  relief="flat", padx=10,
                  command=self.trigger_pipeline_fetch).pack(side="right", padx=5)
        tk.Button(controls, text="⟳  Clear Date Selection",
                  bg=CARD, fg=YELLOW, font=(FONT, 9, "bold"),
                  relief="flat", padx=10,
                  command=self.clear_click_constraints).pack(side="right", padx=5)
        tk.Button(controls, text="⚙  Run Regression",
                  bg=CARD, fg=CYAN, font=(FONT, 9, "bold"),
                  relief="flat", padx=10,
                  command=self.trigger_regression).pack(side="right", padx=5)

        # Workspace
        workspace = tk.Frame(self.root, bg=BG)
        workspace.pack(fill="both", expand=True, padx=15, pady=5)

        left_panel = tk.Frame(workspace, bg=BG, width=320)
        left_panel.pack(side="left", fill="y", padx=(0, 15))
        left_panel.pack_propagate(False)

        self.right_panel = tk.Frame(workspace, bg=BG)
        self.right_panel.pack(side="left", fill="both", expand=True)

        # ── Health Status Card ──
        self.health_card = tk.Frame(left_panel, bg=CARD, pady=15, padx=15,
                                    highlightthickness=1, highlightbackground=GRAY2)
        self.health_card.pack(fill="x", pady=(0, 10))
        tk.Label(self.health_card, text="ANALYSIS RESULT",
                 bg=CARD, fg=GRAY, font=(FONT, 9, "bold")).pack(anchor="w")
        self.lbl_health_status = tk.Label(self.health_card, text="Loading...",
                                           bg=CARD, fg=WHITE, font=(FONT, 13, "bold"),
                                           wraplength=270, justify="left")
        self.lbl_health_status.pack(anchor="w", pady=4)

        # ── Snapshot Stats ──
        tk.Label(left_panel, text="CURRENT DATA SNAPSHOT",
                 bg=BG, fg=CYAN, font=(FONT, 9, "bold")).pack(anchor="w", pady=(5, 2))
        stat_box = tk.Frame(left_panel, bg=CARD, pady=10, padx=12)
        stat_box.pack(fill="x", pady=(0, 10))
        self.lbl_view_asset  = self.make_stat_row(stat_box, "Monitored Coin")
        self.lbl_view_price  = self.make_stat_row(stat_box, "Latest Price (USD)")
        self.lbl_view_change = self.make_stat_row(stat_box, "24h Change")
        self.lbl_view_mood   = self.make_stat_row(stat_box, "Today's Mood Score")
        self.lbl_view_scope  = self.make_stat_row(stat_box, "Analysis Window")
        self.lbl_view_target = self.make_stat_row(stat_box, "Analysis Split Date")
        self.lbl_view_r      = self.make_stat_row(stat_box, "Correlation (r)")
        self.lbl_view_r2     = self.make_stat_row(stat_box, "R² Score")
        self.lbl_view_days   = self.make_stat_row(stat_box, "Data Points Used")

        # ── What does this mean ──
        tk.Label(left_panel, text="WHAT DOES THIS MEAN?",
                 bg=BG, fg=CYAN, font=(FONT, 9, "bold")).pack(anchor="w", pady=(5, 2))
        info_box = tk.Frame(left_panel, bg=CARD, pady=12, padx=12)
        info_box.pack(fill="x", pady=(0, 10))
        self.lbl_interpretation = tk.Label(info_box, text="Loading data...",
                                            bg=CARD, fg=WHITE, font=(FONT, 10),
                                            wraplength=270, justify="left")
        self.lbl_interpretation.pack(anchor="w")

        # ── Data Sources ──
        tk.Label(left_panel, text="DATA SOURCES",
                 bg=BG, fg=CYAN, font=(FONT, 9, "bold")).pack(anchor="w", pady=(5, 2))
        src_box = tk.Frame(left_panel, bg=CARD, pady=10, padx=12)
        src_box.pack(fill="x", pady=(0, 10))
        tk.Label(src_box,
                 text="Price Data:\ncoingecko.com/en/api\n\nMood Score:\nalternative.me/crypto/\nfear-and-greed-index",
                 bg=CARD, fg=GRAY, font=(FONT, 9), justify="left").pack(anchor="w")

        # Status bar
        self.status_var = tk.StringVar(value="System Ready")
        tk.Label(self.root, textvariable=self.status_var,
                 bg=BG, fg=GRAY2, font=(FONT, 8), anchor="w").pack(
                 fill="x", padx=15, pady=4)

        self.setup_charts()


    # ─── 👤 ACCOUNT MANAGEMENT SYSTEM FUNCTIONS ──────────────────────────────────
    def open_account_manage_window(self):
        """ 계정 관리를 위한 팝업 서브 윈도우 생성 """
        acc_win = tk.Toplevel(self.root)
        acc_win.title("User Account Engine Control")
        acc_win.geometry("450x520")
        acc_win.configure(bg=BG)
        acc_win.grab_set()

        # 팝업 제목
        tk.Label(acc_win, text="👤 User Account Management", bg=BG, fg=CYAN, 
                 font=(FONT, 14, "bold"), pady=15).pack()

        # 노트북 스타일 조정 (배경을 완전한 다크모드로 통일)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=BG, borderwidth=0, padding=0)
        style.configure('TNotebook.Tab', background=CARD, foreground=GRAY, font=(FONT, 10), padding=[10, 4])
        style.map('TNotebook.Tab', background=[('selected', CARD2)], foreground=[('selected', CYAN)])

        notebook = ttk.Notebook(acc_win)
        notebook.pack(fill="both", expand=True, padx=15, pady=15)

        # 탭 1: 계정 생성 (Create)
        tab_create = tk.Frame(notebook, bg=CARD2, padx=15, pady=15)
        notebook.add(tab_create, text=" Create Account ")
        
        tk.Label(tab_create, text="New Username:", bg=CARD2, fg=GRAY).grid(row=0, column=0, sticky="w", pady=8)
        ent_c_user = tk.Entry(tab_create, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_c_user.grid(row=0, column=1, pady=8, padx=5)

        tk.Label(tab_create, text="Password:", bg=CARD2, fg=GRAY).grid(row=1, column=0, sticky="w", pady=8)
        ent_c_pw = tk.Entry(tab_create, show="*", bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_c_pw.grid(row=1, column=1, pady=8, padx=5)

        tk.Label(tab_create, text="Email Address:", bg=CARD2, fg=GRAY).grid(row=2, column=0, sticky="w", pady=8)
        ent_c_email = tk.Entry(tab_create, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_c_email.grid(row=2, column=1, pady=8, padx=5)

        lbl_c_status = tk.Label(tab_create, text="", bg=CARD2, fg=YELLOW, font=(FONT, 9))
        lbl_c_status.grid(row=3, column=0, columnspan=2, pady=10)

        def cmd_create():
            u, p, e = ent_c_user.get().strip(), ent_c_pw.get().strip(), ent_c_email.get().strip()
            if not u or not p:
                lbl_c_status.config(text="❌ ID and Password are required!", fg=RED)
                return
            try:
                db = get_connection()
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, email) 
                    VALUES (%s, %s, %s)
                """, (u, p, e if e else None))
                db.commit()
                lbl_c_status.config(text=f"🟢 User '{u}' created successfully!", fg=GREEN)
                ent_c_user.delete(0, 'end'); ent_c_pw.delete(0, 'end'); ent_c_email.delete(0, 'end')
            except Error as err:
                lbl_c_status.config(text=f"❌ Error: {err.msg}", fg=RED)
            finally:
                if 'db' in locals() and db.is_connected():
                    db.close()

        tk.Button(tab_create, text="Register User", bg=CARD, fg=GREEN, relief="flat", font=(FONT, 10, "bold"),
                  command=cmd_create, padx=10, pady=3).grid(row=4, column=0, columnspan=2, pady=5)


        # 탭 2: ID 변경 (Update)
        tab_update = tk.Frame(notebook, bg=CARD2, padx=15, pady=15)
        notebook.add(tab_update, text=" Change Username ")

        tk.Label(tab_update, text="Current Username:", bg=CARD2, fg=GRAY).grid(row=0, column=0, sticky="w", pady=8)
        ent_u_curr = tk.Entry(tab_update, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_u_curr.grid(row=0, column=1, pady=8, padx=5)

        tk.Label(tab_update, text="Verify Password:", bg=CARD2, fg=GRAY).grid(row=1, column=0, sticky="w", pady=8)
        ent_u_pw = tk.Entry(tab_update, show="*", bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_u_pw.grid(row=1, column=1, pady=8, padx=5)

        tk.Label(tab_update, text="New Username:", bg=CARD2, fg=GRAY).grid(row=2, column=0, sticky="w", pady=8)
        ent_u_new = tk.Entry(tab_update, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_u_new.grid(row=2, column=1, pady=8, padx=5)

        lbl_u_status = tk.Label(tab_update, text="", bg=CARD2, fg=YELLOW, font=(FONT, 9))
        lbl_u_status.grid(row=3, column=0, columnspan=2, pady=10)

        def cmd_update():
            curr_u, pw, new_u = ent_u_curr.get().strip(), ent_u_pw.get().strip(), ent_u_new.get().strip()
            if not curr_u or not pw or not new_u:
                lbl_u_status.config(text="❌ All fields are required!", fg=RED)
                return
            try:
                db = get_connection()
                cursor = db.cursor()
                cursor.execute("SELECT id FROM users WHERE username=%s AND password_hash=%s", (curr_u, pw))
                user_row = cursor.fetchone()
                if not user_row:
                    lbl_u_status.config(text="❌ Invalid current username or password.", fg=RED)
                    return
                
                cursor.execute("UPDATE users SET username=%s WHERE id=%s", (new_u, user_row[0]))
                db.commit()
                lbl_u_status.config(text=f"🟢 Changed ID to '{new_u}'!", fg=GREEN)
                ent_u_curr.delete(0, 'end'); ent_u_pw.delete(0, 'end'); ent_u_new.delete(0, 'end')
            except Error as err:
                lbl_u_status.config(text=f"❌ Error: {err.msg}", fg=RED)
            finally:
                if 'db' in locals() and db.is_connected():
                    db.close()

        tk.Button(tab_update, text="Update Username", bg=CARD, fg=CYAN, relief="flat", font=(FONT, 10, "bold"),
                  command=cmd_update, padx=10, pady=3).grid(row=4, column=0, columnspan=2, pady=5)


        # 탭 3: 계정 삭제 (Delete)
        tab_delete = tk.Frame(notebook, bg=CARD2, padx=15, pady=15)
        notebook.add(tab_delete, text=" Delete Account ")

        tk.Label(tab_delete, text="Target Username:", bg=CARD2, fg=GRAY).grid(row=0, column=0, sticky="w", pady=8)
        ent_d_user = tk.Entry(tab_delete, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_d_user.grid(row=0, column=1, pady=8, padx=5)

        tk.Label(tab_delete, text="Confirm Password:", bg=CARD2, fg=GRAY).grid(row=1, column=0, sticky="w", pady=8)
        ent_d_pw = tk.Entry(tab_delete, show="*", bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat", width=25)
        ent_d_pw.grid(row=1, column=1, pady=8, padx=5)

        lbl_d_status = tk.Label(tab_delete, text="⚠️ Warning: This operation cannot be undone.", bg=CARD2, fg=ORANGE, font=(FONT, 9))
        lbl_d_status.grid(row=2, column=0, columnspan=2, pady=15)

        def cmd_delete():
            u, p = ent_d_user.get().strip(), ent_d_pw.get().strip()
            if not u or not p:
                lbl_d_status.config(text="❌ ID and Password are required!", fg=RED)
                return
            try:
                db = get_connection()
                cursor = db.cursor()
                cursor.execute("SELECT id FROM users WHERE username=%s AND password_hash=%s", (u, p))
                user_row = cursor.fetchone()
                if not user_row:
                    lbl_d_status.config(text="❌ Authentication failed. Check info.", fg=RED)
                    return
                
                cursor.execute("DELETE FROM users WHERE id=%s", (user_row[0],))
                db.commit()
                lbl_d_status.config(text=f"🔴 Account '{u}' has been deleted.", fg=RED)
                ent_d_user.delete(0, 'end'); ent_d_pw.delete(0, 'end')
            except Error as err:
                lbl_d_status.config(text=f"❌ Error: {err.msg}", fg=RED)
            finally:
                if 'db' in locals() and db.is_connected():
                    db.close()

        tk.Button(tab_delete, text="Terminate Account", bg=CARD, fg=RED, relief="flat", font=(FONT, 10, "bold"),
                  command=cmd_delete, padx=10, pady=3).grid(row=3, column=0, columnspan=2, pady=5)

    def make_stat_row(self, parent, text):
        row = tk.Frame(parent, bg=parent["bg"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=text + ":", bg=parent["bg"], fg=GRAY,
                 font=(FONT, 9), width=18, anchor="w").pack(side="left")
        lbl = tk.Label(row, text="--", bg=parent["bg"], fg=WHITE,
                       font=(FONT, 9, "bold"), anchor="w")
        lbl.pack(side="left")
        return lbl

    def setup_charts(self):
        self.fig, self.axes = plt.subplots(1, 3, figsize=(14, 5))
        self.fig.patch.set_facecolor(BG)
        self.fig.subplots_adjust(left=0.06, right=0.96, top=0.88,
                                 bottom=0.22, wspace=0.35)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_panel)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

        self.fig.canvas.mpl_connect('button_press_event', self.handle_graph_click)

    # ─── LOADING STATE ────────────────────────────────────────────────────
    def display_loading_state(self):
        for ax in self.axes:
            ax.clear()
            ax.set_facecolor(CARD)
            ax.text(0.5, 0.5, "Loading data...",
                    color=CYAN, fontsize=12, weight="bold",
                    ha='center', va='center', transform=ax.transAxes)
            ax.get_xaxis().set_visible(False)
            ax.get_yaxis().set_visible(False)
        self.canvas.draw()
        self.root.update()

    def reset_and_refresh(self):
        self.clicked_date = None
        self.refresh_data()

    def clear_click_constraints(self):
        self.clicked_date = None
        self.refresh_data()

    # ─── CLICK EVENT ──────────────────────────────────────────────────────
    def handle_graph_click(self, event):
        if event.inaxes != self.axes[0]:
            return
        try:
            num_date = event.xdata
            clicked_dt = plt.matplotlib.dates.num2date(num_date).date()
            self.clicked_date = clicked_dt
            self.refresh_data()
        except Exception:
            pass

    # ─── TRIGGER EXTERNAL SCRIPTS ─────────────────────────────────────────
    def trigger_pipeline_fetch(self):
        self.display_loading_state()
        self.status_var.set("Fetching new data from APIs... please wait")
        self.root.update()
        subprocess.run([sys.executable, "fetcher.py"])
        self.reset_and_refresh()

    def trigger_regression(self):
        self.status_var.set("Running regression analysis...")
        self.root.update()
        subprocess.run([sys.executable, "regression.py"])
        self.refresh_data()

    # ─── MAIN REFRESH ─────────────────────────────────────────────────────
    def refresh_data(self):
        self.display_loading_state()
        try:
            db = get_connection()
            cursor = db.cursor()
            coin      = self.selected_coin.get()
            days_limit= self.selected_days.get()
            color     = COIN_COLORS[coin]
            cutoff    = (datetime.now() - timedelta(days=days_limit)).date()

            # ── Price records ──
            cursor.execute("""
                SELECT DATE(recorded_at) as dt,
                       AVG(price_usd),
                       AVG(price_change_24h)
                FROM price_data
                WHERE coin_id = %s AND DATE(recorded_at) >= %s
                GROUP BY DATE(recorded_at)
                ORDER BY dt
            """, (coin, cutoff))
            p_records = cursor.fetchall()

            if not p_records:
                self.reset_axes_messages("No data found.\nPlease click 'Fetch New Data' first.")
                return

            all_dates  = [r[0] for r in p_records]
            all_prices = [float(r[1]) for r in p_records]

            if self.clicked_date and self.clicked_date in all_dates:
                pivot_index    = all_dates.index(self.clicked_date)
                working_dates  = all_dates[:pivot_index + 1]
                working_prices = all_prices[:pivot_index + 1]
                display_target = self.clicked_date.strftime("%Y-%m-%d")
            else:
                working_dates  = all_dates
                working_prices = all_prices
                display_target = "Full Period"

            # ── Sentiment records ──
            cursor.execute("""
                SELECT DATE(recorded_at) as dt, AVG(score)
                FROM sentiment_data
                WHERE DATE(recorded_at) >= %s
                GROUP BY DATE(recorded_at)
                ORDER BY dt
            """, (cutoff,))
            s_records = dict(cursor.fetchall())

            # Latest sentiment
            cursor.execute("""
                SELECT score, sentiment_label FROM sentiment_data
                ORDER BY recorded_at DESC LIMIT 1
            """)
            sent_row = cursor.fetchone()
            today_mood = int(sent_row[0]) if sent_row else 50
            today_label = sent_row[1] if sent_row else "Unknown"

            # Latest price change
            cursor.execute("""
                SELECT price_change_24h FROM price_data
                WHERE coin_id = %s ORDER BY recorded_at DESC LIMIT 1
            """, (coin,))
            change_row = cursor.fetchone()
            latest_change = float(change_row[0]) if change_row and change_row[0] else 0.0

            # Sync mood + price change
            synced_mood   = []
            synced_change = []
            for r in p_records:
                d = r[0]
                if d in working_dates and d in s_records and r[2] is not None:
                    synced_mood.append(float(s_records[d]))
                    synced_change.append(float(r[2]))

            # Linear Regression
            r_val     = 0.0
            r_squared = 0.0

            if (len(synced_mood) > 5
                    and np.std(synced_mood) > 0
                    and np.std(synced_change) > 0):
                X = np.array(synced_mood).reshape(-1, 1)
                y = np.array(synced_change)
                model = LinearRegression().fit(X, y)
                matrix = np.corrcoef(np.array(synced_mood), y)
                if not np.isnan(matrix[0][1]):
                    r_val     = float(matrix[0][1])
                    r_squared = r_val ** 2

            if abs(r_val) > 0.7:
                status_txt  = "🟢 STRONG LINK\nPublic mood strongly predicts price"
                theme_color = GREEN
                summary     = (f"Over the {days_limit}-day window up to {display_target}, "
                               f"{coin.upper()} price movements closely followed public "
                               f"confidence scores. The connection is strong and meaningful.")
            elif abs(r_val) > 0.5:
                status_txt  = "🟡 MODERATE LINK\nSome connection found"
                theme_color = YELLOW
                summary     = (f"Over the {days_limit}-day window up to {display_target}, "
                               f"{coin.upper()} shows a moderate connection between public "
                               f"mood and price. The link exists but is not always consistent.")
            elif abs(r_val) > 0.3:
                status_txt  = "🟠 WEAK LINK\nVery limited connection"
                theme_color = ORANGE
                summary     = (f"Over the {days_limit}-day window up to {display_target}, "
                               f"{coin.upper()} shows only a weak connection to public mood. "
                               f"Other factors dominate price movement.")
            else:
                status_txt  = "🔴 NO MEANINGFUL LINK\nMood does not predict price"
                theme_color = RED
                summary     = (f"Over the {days_limit}-day window up to {display_target}, "
                               f"{coin.upper()} price moved independently of public mood "
                               f"scores. This is a valid finding — markets are complex.")

            # Update left panel
            self.lbl_health_status.config(text=status_txt, fg=theme_color)
            self.health_card.config(highlightbackground=theme_color)

            self.lbl_view_asset.config(text=coin.capitalize(), fg=color)
            self.lbl_view_price.config(text=f"${all_prices[-1]:,.2f}")

            change_color = GREEN if latest_change >= 0 else RED
            sign = "+" if latest_change >= 0 else ""
            self.lbl_view_change.config(text=f"{sign}{latest_change:.2f}%", fg=change_color)

            self.lbl_view_mood.config(text=f"{today_mood} — {today_label}")
            self.lbl_view_scope.config(text=f"{days_limit} Day Window")
            self.lbl_view_target.config(text=display_target, fg=CYAN)
            self.lbl_view_r.config(text=f"{r_val:.4f}")
            self.lbl_view_r2.config(text=f"{r_squared:.4f}")
            self.lbl_view_days.config(text=f"{len(synced_mood)} matched records")
            self.lbl_interpretation.config(text=summary)

            # Chart 1
            ax = self.axes[0]
            ax.clear()
            ax.set_facecolor(CARD)
            ax.get_xaxis().set_visible(True)
            ax.get_yaxis().set_visible(True)

            ax.plot(all_dates, all_prices, color=color, linewidth=1.5, alpha=0.35, label="Full Period")
            ax.plot(working_dates, working_prices, color=color, linewidth=2.5, label="Analyzed Period")
            ax.fill_between(working_dates, working_prices, min(working_prices), alpha=0.08, color=color)

            info_text = f"r  = {r_val:.3f}\nR² = {r_squared:.3f}\nn  = {len(synced_mood)} days"
            ax.text(0.05, 0.75, info_text, color=WHITE, fontsize=8, weight="bold",
                    bbox=dict(facecolor=BG, edgecolor=theme_color, boxstyle="round,pad=0.5"),
                    transform=ax.transAxes)

            if self.clicked_date:
                ax.axvline(x=self.clicked_date, color=WHITE, linestyle=":", alpha=0.8, label="Split Date")

            ax.set_title("Price History", color=CYAN, fontsize=10, pad=8)
            ax.set_ylabel("USD", color=GRAY, fontsize=8)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
            ax.xaxis.set_major_locator(plt.MaxNLocator(4))
            ax.tick_params(colors=GRAY, labelsize=7)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
            for sp in ax.spines.values(): sp.set_edgecolor(GRAY2)

            # Chart 2
            ax = self.axes[1]
            ax.clear()
            ax.set_facecolor(CARD)
            ax.get_xaxis().set_visible(True)
            ax.get_yaxis().set_visible(True)

            s_dates = sorted(s_records.keys())
            s_vals  = [s_records[k] for k in s_dates]

            ax.plot(s_dates, s_vals, color=YELLOW, linewidth=1.5)
            ax.fill_between(s_dates, s_vals, 50, where=[v >= 50 for v in s_vals], alpha=0.25, color=GREEN, label="Confident")
            ax.fill_between(s_dates, s_vals, 50, where=[v < 50 for v in s_vals], alpha=0.25, color=RED, label="Nervous")
            ax.axhline(y=50, color=GRAY, linestyle=":", alpha=0.5)

            if self.clicked_date:
                ax.axvline(x=self.clicked_date, color=WHITE, linestyle=":", alpha=0.8)

            ax.set_ylim(0, 100)
            ax.set_yticks([0, 25, 50, 75, 100])
            ax.set_yticklabels(["0\nVery\nNervous", "25\nNervous", "50\nBalanced", "75\nConfident", "100\nVery\nConfident"], fontsize=6, color=GRAY)
            ax.set_title("Daily Public Mood Score\n(0 = Very Nervous  →  100 = Very Confident)", color=CYAN, fontsize=9, pad=8)
            ax.xaxis.set_major_locator(plt.MaxNLocator(4))
            ax.tick_params(colors=GRAY, labelsize=7)
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha="right")
            for sp in ax.spines.values(): sp.set_edgecolor(GRAY2)
            ax.legend(fontsize=7, facecolor=CARD, labelcolor=GRAY, edgecolor=GRAY2)

            # Chart 3
            ax = self.axes[2]
            ax.clear()
            ax.set_facecolor(CARD)
            ax.get_xaxis().set_visible(True)
            ax.get_yaxis().set_visible(True)

            ax.scatter(synced_mood, synced_change, color=color, alpha=0.6, s=15, zorder=3)
            ax.axhline(y=0, color=GRAY2, linewidth=0.7)

            if len(synced_mood) > 2 and np.std(synced_mood) > 0:
                x_space = np.linspace(min(synced_mood), max(synced_mood), 100)
                y_line  = np.poly1d(np.polyfit(synced_mood, synced_change, 1))(x_space)
                ax.plot(x_space, y_line, color=CYAN, linewidth=2, linestyle="--", label="Regression line", zorder=4)
                ax.legend(fontsize=7, facecolor=CARD, labelcolor=GRAY, edgecolor=GRAY2)

            ax.set_title("Does Public Confidence Affect Price?", color=CYAN, fontsize=10, pad=8)
            ax.set_xlabel("Public Confidence Score →", color=GRAY, fontsize=8)
            ax.set_ylabel("Price Change %", color=GRAY, fontsize=8)
            ax.tick_params(colors=GRAY, labelsize=7)
            for sp in ax.spines.values(): sp.set_edgecolor(GRAY2)

            self.canvas.draw()
            cursor.close()
            db.close()

            self.status_var.set(
                f"Loaded {len(synced_mood)} data records  |  "
                f"Source: CoinGecko API + Alternative.me Fear & Greed Index  |  "
                f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        except Exception as e:
            if hasattr(self, 'status_var'):
                self.status_var.set(f"Error: {str(e)}")

    def reset_axes_messages(self, text):
        for ax in self.axes:
            ax.clear()
            ax.set_facecolor(CARD)
            ax.text(0.5, 0.5, text, color=YELLOW, ha='center', va='center', transform=ax.transAxes, fontsize=11, weight="bold")
        self.canvas.draw()

# ─── LAUNCH ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app_root = tk.Tk()
    app_instance = CryptoDashboard(app_root)
    app_root.mainloop()
