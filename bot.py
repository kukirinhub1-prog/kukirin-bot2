import time
import telebot
from telebot import types
import requests
import csv
import os
from datetime import datetime
import threading
from tkinter import messagebox, ttk, filedialog

TOKEN = '8628639179:AAHKiLkF93MX1kqhXLDTiv7YpRcg5bncpAk'
MY_ADMIN_ID = 1794972022  # Твій Telegram ID

bot = telebot.TeleBot(TOKEN)
user_data = {}
admin_temp_data = {}
FILENAME = "orders.csv"

def safe_send_message(chat_id, text, **kwargs):
    for _ in range(3):
        try:
            return bot.send_message(chat_id, text, **kwargs)
        except Exception:
            time.sleep(1)
    return None

def save_to_database(chat_id, data):
    file_exists = os.path.exists(FILENAME)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(FILENAME, mode="a", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            if not file_exists:
                writer.writerow(["Дата", "ID клієнта", "ПІБ", "Телефон", "Товар", "Місто", "Пошта"])
            writer.writerow([
                current_time,
                str(chat_id),
                str(data.get('name', '')),
                str(data.get('phone', '')),
                str(data.get('item', '')),
                str(data.get('city', '')),
                str(data.get('post', ''))
            ])
        print(f"✅ Замовлення від {chat_id} успішно записано в базу!")
    except Exception as e:
        print(f"❌ ПОМИЛКА збереження: {e}")

def load_orders():
    if not os.path.exists(FILENAME):
        return []
    orders = []
    with open(FILENAME, mode="r", encoding="utf-8-sig") as file:
        reader = csv.reader(file, delimiter=";")
        next(reader, None)
        for row in reader:
            if row:
                orders.append(row)
    return orders

def save_all_orders(orders):
    with open(FILENAME, mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Дата", "ID клієнта", "ПІБ", "Телефон", "Товар", "Місто", "Пошта"])
        for order in orders:
            writer.writerow(order)

def get_cancel_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Скасувати замовлення", callback_data='cancel_order'))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data.pop(message.chat.id, None)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🛒 Зробити замовлення", callback_data='start_order'))
    
    safe_send_message(
        message.chat.id, 
        "Вітаю! ✌️ Раді вітати в **Kukirin Hub**.\n\n"
        "Тут ти можеш швидко оформити замовлення на запчастини до самокатів.\n\n"
        "Натисни кнопку нижче, щоб почати:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == 'start_order')
def ask_item(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass

    msg = safe_send_message(
        chat_id, 
        "📦 **Крок 1 з 5**\n\nЩо саме замовляєш? (Введи назву товару або деталі):",
        reply_markup=get_cancel_markup(),
        parse_mode="Markdown"
    )
    if msg:
        user_data[chat_id] = {'messages_to_delete': [msg.message_id]}
        bot.register_next_step_handler(msg, process_item)

def process_item(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    user_data[chat_id]['item'] = message.text
    user_data[chat_id]['messages_to_delete'].append(message.message_id)
    
    msg = safe_send_message(chat_id, "🏙 **Крок 2 з 5**\n\nВведи твоє місто та область:", reply_markup=get_cancel_markup(), parse_mode="Markdown")
    if msg:
        user_data[chat_id]['messages_to_delete'].append(msg.message_id)
        bot.register_next_step_handler(msg, process_city)

def process_city(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    user_data[chat_id]['city'] = message.text
    user_data[chat_id]['messages_to_delete'].append(message.message_id)
    
    msg = safe_send_message(chat_id, "📮 **Крок 3 з 5**\n\nВведи номер відділення Нової Пошти:", reply_markup=get_cancel_markup(), parse_mode="Markdown")
    if msg:
        user_data[chat_id]['messages_to_delete'].append(msg.message_id)
        bot.register_next_step_handler(msg, process_post)

def process_post(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    user_data[chat_id]['post'] = message.text
    user_data[chat_id]['messages_to_delete'].append(message.message_id)
    
    msg = safe_send_message(chat_id, "👤 **Крок 4 з 5**\n\nВведи своє ПІБ (Прізвище Ім'я По батькові):", reply_markup=get_cancel_markup(), parse_mode="Markdown")
    if msg:
        user_data[chat_id]['messages_to_delete'].append(msg.message_id)
        bot.register_next_step_handler(msg, process_name)

def process_name(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    user_data[chat_id]['name'] = message.text
    user_data[chat_id]['messages_to_delete'].append(message.message_id)
    
    phone_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    phone_markup.add(types.KeyboardButton("📱 Поділитися контактом", request_contact=True))
    
    cancel_msg = safe_send_message(chat_id, "❌ Якщо хочеш скасувати замовлення, натисни тут:", reply_markup=get_cancel_markup())
    if cancel_msg:
        user_data[chat_id]['messages_to_delete'].append(cancel_msg.message_id)

    msg = safe_send_message(
        chat_id, "📞 **Крок 5 з 5**\n\nНатисни кнопку нижче, щоб швидко передати свій номер телефону:",
        reply_markup=phone_markup, parse_mode="Markdown"
    )
    if msg:
        user_data[chat_id]['messages_to_delete'].append(msg.message_id)
        bot.register_next_step_handler(msg, process_phone)

def process_phone(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    
    phone = message.contact.phone_number if message.contact else message.text
    user_data[chat_id]['phone'] = phone
    user_data[chat_id]['messages_to_delete'].append(message.message_id)
    
    data = user_data.get(chat_id)
    if not data:
        return

    username = f"@{message.from_user.username}" if message.from_user.username else "немає ніка"
    order_text = (
        f"🚨 **НОВЕ ЗАМОВЛЕННЯ З БОТА!** 🚨\n\n"
        f"📦 **Товар:** {data['item']}\n"
        f"🏙 **Місто:** {data['city']}\n"
        f"📮 **Пошта:** {data['post']}\n"
        f"👤 **ПІБ:** {data['name']}\n"
        f"📞 **Телефон:** {data['phone']}\n"
        f"💬 **Клієнт:** {username}\n"
        f"🆔 **ID клієнта:** `{chat_id}`"
    )
    
    admin_temp_data[chat_id] = data
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.row(
        types.InlineKeyboardButton("✅ Прийняти", callback_data=f"accept_{chat_id}"),
        types.InlineKeyboardButton("❌ Немає в наявності", callback_data=f"no_stock_{chat_id}")
    )
    admin_markup.row(
        types.InlineKeyboardButton("❌ Скасувати замовлення (з причиною)", callback_data=f"admin_cancel_{chat_id}")
    )
    
    for msg_id in data.get('messages_to_delete', []):
        try:
            bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

    safe_send_message(
        chat_id, 
        "✅ **Твоє замовлення успішно створено!**\n\nМи передали дані менеджеру на перевірку. Очікуй сповіщення про статус замовлення. 🚀",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    safe_send_message(MY_ADMIN_ID, order_text, reply_markup=admin_markup, parse_mode="Markdown")
    user_data.pop(chat_id, None)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_order')
def client_cancel_order(call):
    bot.answer_callback_query(call.id, "Замовлення скасовано")
    chat_id = call.message.chat.id
    user_data.pop(chat_id, None)
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🛒 Зробити замовлення", callback_data='start_order'))
    safe_send_message(chat_id, "❌ Замовлення було скасоване. Якщо надумаєш — тисни кнопку нижче:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_'))
def admin_accept(call):
    chat_id = int(call.data.split('_')[1])
    bot.answer_callback_query(call.id, "Замовлення прийнято!")
    if chat_id in admin_temp_data:
        save_to_database(chat_id, admin_temp_data[chat_id])
        admin_temp_data.pop(chat_id, None)

    safe_send_message(chat_id, "🎉 **Ваше замовлення прийнято в роботу!**\n\n📦 Орієнтовний час відправки: сьогодні-завтра.", parse_mode="Markdown")
    try:
        bot.edit_message_text(call.message.text + "\n\n🟢 **СТАТУС:** Замовлення прийнято ✅", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('no_stock_'))
def admin_no_stock(call):
    chat_id = int(call.data.split('_')[-1])
    bot.answer_callback_query(call.id, "Позначено як 'Немає в наявності'")
    admin_temp_data.pop(chat_id, None)
    safe_send_message(chat_id, "⚠️ На жаль, вибраного товару зараз немає в наявності.", parse_mode="Markdown")
    try:
        bot.edit_message_text(call.message.text + "\n\n🔴 **СТАТУС:** Немає в наявності ❌", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_cancel_'))
def admin_ask_cancel_reason(call):
    chat_id = int(call.data.split('_')[2])
    bot.answer_callback_query(call.id)
    admin_temp_data[call.from_user.id] = {
        'target_chat_id': chat_id,
        'admin_msg_id': call.message.message_id,
        'admin_msg_text': call.message.text
    }
    msg = safe_send_message(MY_ADMIN_ID, "✍️ **Введи причину скасування замовлення:**", parse_mode="Markdown")
    if msg:
        bot.register_next_step_handler(msg, process_admin_cancel_reason)

def process_admin_cancel_reason(message):
    admin_id = message.from_user.id
    reason = message.text
    if admin_id not in admin_temp_data:
        return
    target_chat_id = admin_temp_data[admin_id]['target_chat_id']
    admin_msg_id = admin_temp_data[admin_id]['admin_msg_id']
    admin_msg_text = admin_temp_data[admin_id]['admin_msg_text']
    
    safe_send_message(target_chat_id, f"❌ Ваше замовлення скасовано.\n\n💬 **Причина:** {reason}", parse_mode="Markdown")
    try:
        bot.edit_message_text(admin_msg_text + f"\n\n❌ **СТАТУС:** Скасовано\n💬 Причина: {reason}", chat_id=MY_ADMIN_ID, message_id=admin_msg_id, parse_mode="Markdown")
    except Exception:
        pass
    admin_temp_data.pop(admin_id, None)

# Графічна панель адміністратора (Tkinter)
class AdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kukirin Hub — Панель замовлень")
        self.root.geometry("980x520")
        
        self.title_label = tk.Label(root, text="📦 Активні замовлення клієнтів (0)", font=("Arial", 15, "bold"))
        self.title_label.pack(pady=10)
        
        columns = ("Дата", "ID клієнта", "ПІБ", "Телефон", "Товар", "Місто", "Пошта")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=12)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=125, anchor=tk.CENTER)
            
        self.tree.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        
        refresh_btn = tk.Button(btn_frame, text="🔄 Оновити", font=("Arial", 10, "bold"), command=self.populate_table, bg="#e0e0e0", width=12)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        complete_btn = tk.Button(btn_frame, text="✅ Виконано", font=("Arial", 10, "bold"), command=self.complete_order, bg="#d4edda", width=14)
        complete_btn.pack(side=tk.LEFT, padx=5)

        export_btn = tk.Button(btn_frame, text="📊 Експорт в Excel", font=("Arial", 10, "bold"), command=self.export_excel, bg="#cce5ff", width=16)
        export_btn.pack(side=tk.LEFT, padx=5)

        clear_all_btn = tk.Button(btn_frame, text="🗑 Видалити все", font=("Arial", 10, "bold"), command=self.clear_all, bg="#f8d7da", width=15)
        clear_all_btn.pack(side=tk.LEFT, padx=5)
        
        self.populate_table()

    def populate_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        orders = load_orders()
        for order in orders:
            self.tree.insert("", tk.END, values=order)
        self.title_label.config(text=f"📦 Активні замовлення клієнтів ({len(orders)})")

    def complete_order(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Увага", "Вибери замовлення зі списку!")
            return
            
        if messagebox.askyesno("Підтвердження", "Позначити це замовлення як виконане і видалити зі списку?"):
            values = self.tree.item(selected_item, "values")
            client_chat_id = values[1]  # Беремо ID клієнта з другої колонки
            
            # Пишемо повідомлення клієнту в Telegram
            success_text = (
                "🚀 **Ваше замовлення успішно виконано!**\n\n"
                "Дякуємо, що обрали **Kukirin Hub** ⚡️\n"
                "Нехай поїздки приносять лише задоволення! Якщо знадобляться ще якісь запчастини чи тюнінг — ми завжди на зв'язку. Ровер та самокат під надійним контролем! 🔥"
            )
            safe_send_message(int(client_chat_id), success_text, parse_mode="Markdown")

            # Видаляємо з бази та оновлюємо таблицю
            orders = load_orders()
            updated_orders = [o for o in orders if o[0] != values[0] or o[1] != values[1]]
            save_all_orders(updated_orders)
            self.populate_table()
            messagebox.showinfo("Успіх", "Замовлення виконано, клієнту надіслано сповіщення!")

    def export_excel(self):
        orders = load_orders()
        if not orders:
            messagebox.showwarning("Увага", "Немає замовлень для експорту!")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.xlsx")], title="Зберегти як")
        if file_path:
            try:
                with open(file_path, mode="w", encoding="utf-8-sig", newline="") as file:
                    writer = csv.writer(file, delimiter=";")
                    writer.writerow(["Дата", "ID клієнта", "ПІБ", "Телефон", "Товар", "Місто", "Пошта"])
                    writer.writerows(orders)
                messagebox.showinfo("Успіх", "Базу успішно експортовано!")
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося зберегти файл: {e}")

    def clear_all(self):
        orders = load_orders()
        if not orders:
            messagebox.showwarning("Увага", "База і так порожня!")
            return
        if messagebox.askyesno("УВАГА!", "Ви впевнені, що хочете видалити ВСІ замовлення?"):
            if os.path.exists(FILENAME):
                os.remove(FILENAME)
            self.populate_table()
            messagebox.showinfo("Успіх", "Всі замовлення видалено!")

def run_bot():
    print("Бот запущено і працює...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
        except Exception as e:
            print(f"⚠️ Збій зв'язку: {e}. Перепідключення через 5 сек...")
            time.sleep(5)

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    root = tk.Tk()
    app = AdminApp(root)
    root.mainloop()