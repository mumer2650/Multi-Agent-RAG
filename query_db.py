import sqlite3
conn = sqlite3.connect('backend/storage/sqlite/sage_appliances.db')
cursor = conn.cursor()
cursor.execute("SELECT p.model_name, c.category_name FROM products p JOIN categories c ON p.category_id = c.id WHERE c.category_name = 'washing_machines';")
print("Washing machines in DB:", cursor.fetchall())
cursor.execute("SELECT p.model_name, c.category_name FROM products p JOIN categories c ON p.category_id = c.id;")
print("All products:", cursor.fetchall())
conn.close()
