#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
あきぽす
売上登録・取消・集計機能付き
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import datetime
from typing import List, Tuple, Optional
import os
from zoneinfo import ZoneInfo

class POSDatabase:
    """データベース管理クラス"""
    
    def __init__(self, db_path: str = "pos_data.db"):
        self.db_path = db_path
        self.jst = ZoneInfo("Asia/Tokyo")
        self.init_database()
        self.migrate_database()
    
    def get_current_time(self) -> str:
        """現在の日本標準時を取得"""
        return datetime.datetime.now(self.jst).strftime("%Y-%m-%d %H:%M:%S")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
                                       
        # イベントテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 商品テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                name TEXT NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                price INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        ''')
        
        # 売上テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                total_price INTEGER NOT NULL,
                sale_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cancelled BOOLEAN DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def migrate_database(self):
        """データベースマイグレーション - stockカラム追加"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        
            # stockカラムが存在するかチェック
            cursor.execute("PRAGMA table_info(products)")
            columns = [column[1] for column in cursor.fetchall()]
        
            if 'stock' not in columns:
                # stockカラムを追加
                cursor.execute("ALTER TABLE products ADD COLUMN stock INTEGER NOT NULL DEFAULT 0")
                conn.commit()
                print("データベースにstockカラムを追加しました")
            
        except sqlite3.Error as e:
            print(f"データベースマイグレーションエラー: {e}")
            if conn:
                conn.rollback()
        except Exception as e:
            print(f"マイグレーション処理エラー: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close() 
    
    
    def create_event(self, name: str, date: str) -> int:
        """イベント作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO events (name, date) VALUES (?, ?)", (name, date))
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def get_events(self) -> List[Tuple]:
        """イベント一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, date FROM events ORDER BY created_at DESC")
        events = cursor.fetchall()
        conn.close()
        return events
    
    def add_product(self, event_id: int, name: str, price: int, stock: int = 0) -> int:
        """商品追加"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (event_id, name, price, stock) VALUES (?, ?, ?, ?)", 
                      (event_id, name, price, stock))
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return product_id
        
    def delete_product(self, product_id: int) -> bool:
        """商品削除"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        # 売上履歴があるかチェック
        cursor.execute("SELECT COUNT(*) FROM sales WHERE product_id = ? AND cancelled = FALSE", (product_id,))
        sales_count = cursor.fetchone()[0]
    
        if sales_count > 0:
            conn.close()
            return False  # 売上履歴がある場合は削除不可
    
        # 商品削除
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_products(self, event_id: int) -> List[Tuple]:
        """指定イベントの商品一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, stock FROM products WHERE event_id = ? ORDER BY name", 
                      (event_id,))
        products = cursor.fetchall()
        conn.close()
        return products
    
    def record_sale(self, event_id: int, product_id: int, quantity: int, total_price: int) -> int:
        """売上記録"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        current_time = self.get_current_time()
        cursor.execute("""
            INSERT INTO sales (event_id, product_id, quantity, total_price, sale_time) 
            VALUES (?, ?, ?, ?, ?)
        """, (event_id, product_id, quantity, total_price, current_time))
        sale_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return sale_id
        
    def update_stock(self, product_id: int, quantity_change: int) -> bool:
        """在庫数更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", 
                      (quantity_change, product_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_product_stock(self, product_id: int) -> int:
        """商品の在庫数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def cancel_sale(self, sale_id: int) -> bool:
        """売上取消"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE sales SET cancelled = TRUE WHERE id = ?", (sale_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_recent_sales(self, event_id: int, limit: int = 20) -> List[Tuple]:
        """最近の売上履歴取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, p.name, s.quantity, s.total_price, s.sale_time, s.cancelled
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE s.event_id = ?
            ORDER BY s.sale_time DESC
            LIMIT ?
        """, (event_id, limit))
        sales = cursor.fetchall()
        conn.close()
        return sales
    
    def get_sales_summary(self, event_id: int) -> Tuple[int, int, int]:
        """売上集計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 総売上（キャンセル分除く）
        cursor.execute("""
            SELECT COALESCE(SUM(total_price), 0) 
            FROM sales 
            WHERE event_id = ? AND cancelled = FALSE
        """, (event_id,))
        total_sales = cursor.fetchone()[0]
        
        # 総販売数
        cursor.execute("""
            SELECT COALESCE(SUM(quantity), 0) 
            FROM sales 
            WHERE event_id = ? AND cancelled = FALSE
        """, (event_id,))
        total_quantity = cursor.fetchone()[0]
        
        # 取引数
        cursor.execute("""
            SELECT COUNT(*) 
            FROM sales 
            WHERE event_id = ? AND cancelled = FALSE
        """, (event_id,))
        transaction_count = cursor.fetchone()[0]
        
        conn.close()
        return total_sales, total_quantity, transaction_count
    
    def get_product_sales_summary(self, event_id: int) -> List[Tuple]:
        """商品別売上集計"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name, 
                   COALESCE(SUM(s.quantity), 0) as total_quantity,
                   COALESCE(SUM(s.total_price), 0) as total_sales,
                   p.price
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id AND s.cancelled = FALSE
            WHERE p.event_id = ?
            GROUP BY p.id, p.name, p.price
            ORDER BY total_sales DESC, p.name
        """, (event_id,))
        results = cursor.fetchall()
        conn.close()
        return results


class POSApp:
    """POSアプリメインクラス"""
    
    def __init__(self):
        self.db = POSDatabase()
        self.current_event_id = None
        self.cart_items = []  # [(product_id, name, price, quantity)]
        
        self.setup_gui()
        self.load_events()
    
    def setup_gui(self):
        """GUI初期化"""
        self.root = tk.Tk()
        self.root.title("あきぽす")
        self.root.geometry("1200x1000")
        
        self.time_label = ttk.Label(self.root, text="", font=("Arial", 10))
        self.time_label.pack(anchor=tk.E, padx=10, pady=5)
        self.update_time_display()
        
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上部：イベント選択・管理
        self.setup_event_frame(main_frame)
        
        # 中央：商品選択・カート
        self.setup_main_content(main_frame)
        
        # 下部：売上履歴・集計
        self.setup_bottom_frame(main_frame)
        
    def update_time_display(self):
        """現在時刻表示更新"""
        jst = ZoneInfo("Asia/Tokyo")
        current_time = datetime.datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S JST")
        self.time_label.config(text=f"現在時刻: {current_time}")
        # 1秒後に再実行
        self.root.after(1000, self.update_time_display)
    
    def setup_event_frame(self, parent):
        """イベント管理フレーム"""
        event_frame = ttk.LabelFrame(parent, text="イベント管理")
        event_frame.pack(fill=tk.X, pady=(0, 10))
        
        # イベント選択
        ttk.Label(event_frame, text="現在のイベント:").pack(side=tk.LEFT, padx=5)
        self.event_var = tk.StringVar()
        self.event_combo = ttk.Combobox(event_frame, textvariable=self.event_var, 
                                       state="readonly", width=30)
        self.event_combo.pack(side=tk.LEFT, padx=5)
        self.event_combo.bind("<<ComboboxSelected>>", self.on_event_selected)
        
        # ボタン群
        ttk.Button(event_frame, text="新規イベント", 
                  command=self.create_new_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(event_frame, text="商品管理", 
                  command=self.manage_products).pack(side=tk.LEFT, padx=5)
    
    def setup_main_content(self, parent):
        """メインコンテンツフレーム"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 左側：商品選択
        products_frame = ttk.LabelFrame(content_frame, text="商品選択")
        products_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 商品リスト
        self.products_listbox = tk.Listbox(products_frame, height=5)
        self.products_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.products_listbox.bind("<Double-Button-1>", self.add_to_cart)

        # 在庫表示フレーム追加
        stock_frame = ttk.LabelFrame(products_frame, text="在庫状況")
        stock_frame.pack(fill=tk.X, padx=5, pady=5)

        stock_columns = ("商品名", "在庫数")
        self.stock_tree = ttk.Treeview(stock_frame, columns=stock_columns, show="headings", height=5)
        for col in stock_columns:
            self.stock_tree.heading(col, text=col)
            if col == "商品名":
                self.stock_tree.column(col, width=150)
            else:
                self.stock_tree.column(col, width=80)

        self.stock_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 数量入力
        qty_frame = ttk.Frame(products_frame)
        qty_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(qty_frame, text="数量:").pack(side=tk.LEFT)
        self.quantity_var = tk.StringVar(value="1")
        qty_spin = ttk.Spinbox(qty_frame, from_=1, to=99, textvariable=self.quantity_var, width=5)
        qty_spin.pack(side=tk.LEFT, padx=5)
        ttk.Button(qty_frame, text="カートに追加", 
                  command=self.add_to_cart).pack(side=tk.LEFT, padx=5)
        
        # 右側：カート
        cart_frame = ttk.LabelFrame(content_frame, text="カート")
        cart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # カートリスト
        cart_list_frame = ttk.Frame(cart_frame)
        cart_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("商品名", "単価", "数量", "小計")
        self.cart_tree = ttk.Treeview(cart_list_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=80)
        
        cart_scrollbar = ttk.Scrollbar(cart_list_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_scrollbar.set)
        
        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cart_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # カート操作
        cart_control_frame = ttk.Frame(cart_frame)
        cart_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(cart_control_frame, text="選択削除", 
                  command=self.remove_from_cart).pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_control_frame, text="全削除", 
                  command=self.clear_cart).pack(side=tk.LEFT, padx=5)
        
        # 合計・会計
        total_frame = ttk.Frame(cart_frame)
        total_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.total_label = ttk.Label(total_frame, text="合計: ¥0", font=("Arial", 14, "bold"))
        self.total_label.pack(side=tk.LEFT)
        
        ttk.Button(total_frame, text="会計", command=self.checkout, 
                  style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
    
    def setup_bottom_frame(self, parent):
        """下部フレーム（履歴・集計）"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側：売上履歴
        history_frame = ttk.LabelFrame(bottom_frame, text="売上履歴")
        history_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        history_list_frame = ttk.Frame(history_frame)
        history_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        history_columns = ("ID", "商品名", "数量", "金額", "時刻", "状態")
        self.history_tree = ttk.Treeview(history_list_frame, columns=history_columns, show="headings", height=6)
        for col in history_columns:
            self.history_tree.heading(col, text=col)
            if col == "ID":
                self.history_tree.column(col, width=40)
            elif col == "時刻":
                self.history_tree.column(col, width=120)
            else:
                self.history_tree.column(col, width=80)
        
        history_scrollbar = ttk.Scrollbar(history_list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 履歴操作
        history_control_frame = ttk.Frame(history_frame)
        history_control_frame.pack(fill=tk.X, padx=5, pady=5)


        self.cancel_button = tk.Button(history_control_frame, text="売上取消", 
                                      command=self.cancel_selected_sale, fg="red")
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(history_control_frame, text="更新", 
                  command=self.refresh_history).pack(side=tk.LEFT, padx=5)
        
        # 商品別売上集計
        product_summary_frame = ttk.LabelFrame(history_frame, text="商品別売上集計")
        product_summary_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))
        
        product_summary_list_frame = ttk.Frame(product_summary_frame)
        product_summary_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        product_columns = ("商品名", "販売数", "売上", "単価")
        self.product_summary_tree = ttk.Treeview(product_summary_list_frame, columns=product_columns, show="headings", height=6)
        for col in product_columns:
            self.product_summary_tree.heading(col, text=col)
            if col == "商品名":
                self.product_summary_tree.column(col, width=120)
            else:
                self.product_summary_tree.column(col, width=80)
        
        product_summary_scrollbar = ttk.Scrollbar(product_summary_list_frame, orient=tk.VERTICAL, command=self.product_summary_tree.yview)
        self.product_summary_tree.configure(yscrollcommand=product_summary_scrollbar.set)
        
        self.product_summary_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        product_summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 右側：総合集計
        summary_frame = ttk.LabelFrame(bottom_frame, text="総合集計")
        summary_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        self.summary_labels = {}
        summary_items = [
            ("総売上", "total_sales"),
            ("販売数", "total_quantity"),
            ("取引数", "transaction_count")
        ]
        
        for i, (label, key) in enumerate(summary_items):
            ttk.Label(summary_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=5)
            self.summary_labels[key] = ttk.Label(summary_frame, text="¥0", font=("Arial", 12, "bold"))
            self.summary_labels[key].grid(row=i, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(summary_frame, text="集計更新", 
                  command=self.update_summary).grid(row=len(summary_items), column=0, columnspan=2, pady=10)
    
    def load_events(self):
        """イベント一覧読み込み"""
        events = self.db.get_events()
        event_list = [f"{event[1]} ({event[2]})" for event in events]
        self.event_combo['values'] = event_list
        self.event_data = {f"{event[1]} ({event[2]})": event[0] for event in events}
        
        if event_list:
            self.event_combo.set(event_list[0])
            self.on_event_selected()
    
    def on_event_selected(self, event=None):
        """イベント選択時処理"""
        selected = self.event_var.get()
        if selected in self.event_data:
            self.current_event_id = self.event_data[selected]
            self.load_products()
            self.refresh_history()
            self.update_summary()
            self.clear_cart()
    
    def create_new_event(self):
        """新規イベント作成"""
        dialog = EventDialog(self.root)
        if dialog.result:
            name, date = dialog.result
            event_id = self.db.create_event(name, date)
            self.load_events()
            # 新しいイベントを選択
            new_event_text = f"{name} ({date})"
            self.event_combo.set(new_event_text)
            self.on_event_selected()
    
    def manage_products(self):
        """商品管理"""
        if not self.current_event_id:
            messagebox.showwarning("警告", "イベントを選択してください")
            return
        
        dialog = ProductManagementDialog(self.root, self.db, self.current_event_id)
        if dialog.result:
            self.load_products()
    
    def load_products(self):
        """商品一覧読み込み"""
        if not self.current_event_id:
            return
    
        products = self.db.get_products(self.current_event_id)
        self.products_listbox.delete(0, tk.END)
        self.product_data = {}
    
        # 在庫ツリーをクリア
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
    
        for product in products:
            product_id, name, price, stock = product
            display_text = f"{name} - ¥{price:,}"  # 在庫表示を削除
            self.products_listbox.insert(tk.END, display_text)
            self.product_data[display_text] = product
        
            # 在庫ツリーに追加
            stock_color = "red" if stock == 0 else "orange" if stock <= 5 else "black"
            item_id = self.stock_tree.insert("", tk.END, values=(name, stock))
            if stock == 0:
                self.stock_tree.item(item_id, tags=('out_of_stock',))
            elif stock <= 5:
                self.stock_tree.item(item_id, tags=('low_stock',))
    
        # 在庫状況の色設定
        self.stock_tree.tag_configure('out_of_stock', foreground='red')
        self.stock_tree.tag_configure('low_stock', foreground='orange')
    
    def add_to_cart(self, event=None):
        """カートに追加"""
        selection = self.products_listbox.curselection()
        if not selection:
            return
    
        selected_text = self.products_listbox.get(selection[0])
        if selected_text not in self.product_data:
            return
    
        product_id, name, price, stock = self.product_data[selected_text]  # stock追加
    
        try:
            quantity = int(self.quantity_var.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("エラー", "正しい数量を入力してください")
            return
            
        # 在庫チェック追加
        current_cart_qty = sum(item[3] for item in self.cart_items if item[0] == product_id)
        if current_cart_qty + quantity > stock:
            messagebox.showerror("エラー", f"在庫不足です。在庫数: {stock}")
            return
        
        # 既存アイテムがあるかチェック
        for i, item in enumerate(self.cart_items):
            if item[0] == product_id:
                # 数量を更新
                new_quantity = item[3] + quantity
                self.cart_items[i] = (product_id, name, price, new_quantity)
                break
        else:
            # 新規アイテム追加
            self.cart_items.append((product_id, name, price, quantity))
        
        self.update_cart_display()
    
    def remove_from_cart(self):
        """カートから削除"""
        selection = self.cart_tree.selection()
        if not selection:
            return
        
        item = self.cart_tree.item(selection[0])
        product_name = item['values'][0]
        
        # カートから削除
        self.cart_items = [item for item in self.cart_items if item[1] != product_name]
        self.update_cart_display()
    
    def clear_cart(self):
        """カートクリア"""
        self.cart_items = []
        self.update_cart_display()
    
    def update_cart_display(self):
        """カート表示更新"""
        # ツリーをクリア
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        total = 0
        for product_id, name, price, quantity in self.cart_items:
            subtotal = price * quantity
            total += subtotal
            self.cart_tree.insert("", tk.END, values=(name, f"¥{price:,}", quantity, f"¥{subtotal:,}"))
        
        self.total_label.config(text=f"合計: ¥{total:,}")
    
    def checkout(self):
        """会計処理"""
        if not self.current_event_id:
            messagebox.showwarning("警告", "イベントを選択してください")
            return
        
        if not self.cart_items:
            messagebox.showwarning("警告", "カートが空です")
            return
        
        # 確認ダイアログ
        total = sum(item[2] * item[3] for item in self.cart_items)
        if not messagebox.askyesno("確認", f"合計 ¥{total:,} で会計を実行しますか？"):
            return
        
        try:
            # 売上記録
            for product_id, name, price, quantity in self.cart_items:
                total_price = price * quantity
                self.db.record_sale(self.current_event_id, product_id, quantity, total_price)
                # 在庫減算追加
                self.db.update_stock(product_id, -quantity)
    
            messagebox.showinfo("完了", "会計が完了しました")
            self.clear_cart()
            self.refresh_history()
            self.update_summary()
            self.load_products()  # 商品リスト更新追加
    
        except Exception as e:
            messagebox.showerror("エラー", f"会計処理でエラーが発生しました: {str(e)}")
    
    def refresh_history(self):
        """履歴更新"""
        if not self.current_event_id:
            return
        
        # 売上履歴ツリーをクリア
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        sales = self.db.get_recent_sales(self.current_event_id)
        for sale in sales:
            sale_id, product_name, quantity, total_price, sale_time, cancelled = sale
            status = "キャンセル" if cancelled else "有効"
            # 時刻をフォーマット
            sale_time = sale_time.split('.')[0]  # マイクロ秒を除去
            item_id = self.history_tree.insert("", tk.END, values=(
                sale_id, product_name, quantity, f"¥{total_price:,}", sale_time, status
            ))
            
            if cancelled:
                self.history_tree.set(item_id, "状態", status)
                # Treeviewのtagを使用して色を設定
                self.history_tree.item(item_id, tags=('cancelled',))
                
        self.history_tree.tag_configure('cancelled', foreground='red')
        
        # 商品別集計も更新
        self.update_product_summary()
    
    def cancel_selected_sale(self):
        """選択した売上を取消"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "取消する売上を選択してください")
            return
        
        item = self.history_tree.item(selection[0])
        sale_id = item['values'][0]
        status = item['values'][5]
        
        if status == "取消":
            messagebox.showwarning("警告", "既に取消済みです")
            return
        
        if messagebox.askyesno("確認", "選択した売上を取消しますか？"):
            if self.db.cancel_sale(sale_id):
                messagebox.showinfo("完了", "売上を取消しました")
                self.refresh_history()
                self.update_summary()
            else:
                messagebox.showerror("エラー", "取消処理に失敗しました")
    
    def update_product_summary(self):
        """商品別売上集計更新"""
        if not self.current_event_id:
            return
        
        # 商品別集計ツリーをクリア
        for item in self.product_summary_tree.get_children():
            self.product_summary_tree.delete(item)
        
        product_sales = self.db.get_product_sales_summary(self.current_event_id)
        for product_sale in product_sales:
            product_name, total_quantity, total_sales, unit_price = product_sale
            self.product_summary_tree.insert("", tk.END, values=(
                product_name, total_quantity, f"¥{total_sales:,}", f"¥{unit_price:,}"
            ))
    
    def update_summary(self):
        """集計更新"""
        if not self.current_event_id:
            return
        
        total_sales, total_quantity, transaction_count = self.db.get_sales_summary(self.current_event_id)
        
        self.summary_labels['total_sales'].config(text=f"¥{total_sales:,}")
        self.summary_labels['total_quantity'].config(text=f"{total_quantity}")
        self.summary_labels['transaction_count'].config(text=f"{transaction_count}")
        
        # 商品別集計も更新
        self.update_product_summary()
    
    def run(self):
        """アプリケーション実行"""
        self.root.mainloop()


class EventDialog:
    """イベント作成ダイアログ"""
    
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("新規イベント作成")
        self.dialog.geometry("400x250")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # イベント名
        ttk.Label(self.dialog, text="イベント名:").pack(pady=10)
        self.name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.name_var, width=40).pack(pady=5)
        
        # 開催日
        ttk.Label(self.dialog, text="開催日 (YYYY-MM-DD):").pack(pady=10)
        self.date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        ttk.Entry(self.dialog, textvariable=self.date_var, width=40).pack(pady=5)
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="作成", command=self.create_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        self.dialog.wait_window()
    
    def create_event(self):
        name = self.name_var.get().strip()
        date = self.date_var.get().strip()
        
        if not name:
            messagebox.showerror("エラー", "イベント名を入力してください")
            return
        
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("エラー", "正しい日付形式で入力してください (YYYY-MM-DD)")
            return
        
        self.result = (name, date)
        self.dialog.destroy()


class ProductManagementDialog:
    """商品管理ダイアログ"""
    
    def __init__(self, parent, db: POSDatabase, event_id: int):
        self.db = db
        self.event_id = event_id
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("商品管理")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 商品リスト
        list_frame = ttk.LabelFrame(self.dialog, text="登録済み商品")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("商品名", "価格", "在庫")  # 在庫列追加
        self.product_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        for col in columns:
            self.product_tree.heading(col, text=col)
            if col == "商品名":
                self.product_tree.column(col, width=200)
            else:
                self.product_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.product_tree.yview)
        self.product_tree.configure(yscrollcommand=scrollbar.set)
        
        self.product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 商品追加フォーム
        add_frame = ttk.LabelFrame(self.dialog, text="商品追加")
        add_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        form_frame = ttk.Frame(add_frame)
        form_frame.pack(padx=10, pady=10)
        
        ttk.Label(form_frame, text="商品名:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(form_frame, text="価格:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.price_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.price_var, width=30).grid(row=1, column=1, padx=5, pady=2)

        # 在庫入力追加
        ttk.Label(form_frame, text="在庫数:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.stock_var = tk.StringVar(value="0")
        ttk.Entry(form_frame, textvariable=self.stock_var, width=30).grid(row=2, column=1, padx=5, pady=2)

        ttk.Button(form_frame, text="追加", command=self.add_product).grid(row=2, column=2, padx=5)
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="閉じる", command=self.close_dialog).pack()
        
        self.load_products()
        self.dialog.wait_window()
        
        # 商品操作ボタンフレーム
        product_control_frame = ttk.Frame(list_frame)
        product_control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(product_control_frame, text="選択した商品を削除", 
              command=self.delete_selected_product, 
              style="Accent.TButton").pack(side=tk.LEFT, padx=5)
              
    def delete_selected_product(self):
        """選択した商品を削除"""
        selection = self.product_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "削除する商品を選択してください")
            return
    
        item = self.product_tree.item(selection[0])
        product_name = item['values'][0]
    
        # 商品IDを取得するため、商品情報を再取得
        products = self.db.get_products(self.event_id)
        product_id = None
        for product in products:
            if product[1] == product_name:  # 商品名で一致
                product_id = product[0]
                break
    
        if not product_id:
            messagebox.showerror("エラー", "商品情報の取得に失敗しました")
            return
    
        # 確認ダイアログ
        if not messagebox.askyesno("確認", f"商品「{product_name}」を削除しますか？\n※売上履歴がある商品は削除できません"):
            return
    
        try:
            if self.db.delete_product(product_id):
                messagebox.showinfo("完了", "商品を削除しました")
                self.load_products()
                self.result = True
            else:
                messagebox.showerror("エラー", "商品を削除できませんでした。\n売上履歴がある商品は削除できません。")
        except Exception as e:
            messagebox.showerror("エラー", f"商品削除でエラーが発生しました: {str(e)}")
    
    def load_products(self):
        """商品一覧読み込み"""
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        products = self.db.get_products(self.event_id)
        self.product_data = {}  # 商品データ保持用辞書を追加
    
        for product in products:
            product_id, name, price, stock = product
            item_id = self.product_tree.insert("", tk.END, values=(name, f"¥{price:,}", stock))
            self.product_data[item_id] = product_id 

    def add_product(self):
        """商品追加"""
        name = self.name_var.get().strip()
        price_str = self.price_var.get().strip()
        stock_str = self.stock_var.get().strip()  # 追加
    
        if not name:
            messagebox.showerror("エラー", "商品名を入力してください")
            return        
        
        try:
            price = int(price_str)
            stock = int(stock_str)  # 追加
            if price < 0 or stock < 0:  # 在庫チェック追加
                raise ValueError
        except ValueError:
            messagebox.showerror("エラー", "正しい価格と在庫数を入力してください")  # メッセージ修正
            return
    
        try:
            self.db.add_product(self.event_id, name, price, stock)  # stock引数追加
            messagebox.showinfo("完了", "商品を追加しました")
            self.name_var.set("")
            self.price_var.set("")
            self.stock_var.set("0")  # 追加
            self.load_products()
            self.result = True
        except Exception as e:
            messagebox.showerror("エラー", f"商品追加でエラーが発生しました: {str(e)}")
            
    def close_dialog(self):
        """ダイアログを閉じる"""
        self.dialog.destroy()


def main():
    """メイン関数"""
    try:
        app = POSApp()
        app.run()
    except Exception as e:
        print(f"アプリケーション実行エラー: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()