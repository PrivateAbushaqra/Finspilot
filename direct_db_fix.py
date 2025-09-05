import sqlite3
import uuid
from datetime import date

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# الحصول على بيانات مردود المشتريات
cursor.execute("""
    SELECT pr.id, pr.return_number, pr.date, pr.total_amount,
           pi.supplier_id, cs.name as supplier_name
    FROM purchases_purchasereturn pr
    JOIN purchases_purchaseinvoice pi ON pr.original_invoice_id = pi.id
    JOIN customers_customersupplier cs ON pi.supplier_id = cs.id
    WHERE pr.id = 2
""")

purchase_return_data = cursor.fetchone()

if purchase_return_data:
    pr_id, return_number, pr_date, total_amount, supplier_id, supplier_name = purchase_return_data
    print(f"مردود المشتريات: {return_number}")
    print(f"المورد: {supplier_name} (ID: {supplier_id})")
    print(f"المبلغ: {total_amount}")
    
    # البحث عن عميل بنفس الاسم
    cursor.execute("""
        SELECT id, name, type FROM customers_customersupplier 
        WHERE name = ? AND type IN ('customer', 'both') AND id != ?
    """, (supplier_name, supplier_id))
    
    matching_customers = cursor.fetchall()
    
    if matching_customers:
        for customer_id, customer_name, customer_type in matching_customers:
            print(f"عميل مطابق: {customer_name} (ID: {customer_id}, نوع: {customer_type})")
            
            # فحص إذا كانت المعاملة موجودة
            cursor.execute("""
                SELECT id FROM accounts_accounttransaction 
                WHERE customer_supplier_id = ? AND transaction_type = 'purchase_return' AND reference_id = ?
            """, (customer_id, pr_id))
            
            existing = cursor.fetchone()
            
            if not existing:
                # إنشاء معاملة جديدة
                transaction_number = f"PRET-C-{uuid.uuid4().hex[:8].upper()}"
                
                # حساب الرصيد السابق
                cursor.execute("""
                    SELECT balance_after FROM accounts_accounttransaction 
                    WHERE customer_supplier_id = ? ORDER BY created_at DESC LIMIT 1
                """, (customer_id,))
                
                last_balance = cursor.fetchone()
                previous_balance = last_balance[0] if last_balance else 0
                new_balance = previous_balance + float(total_amount)
                
                # إدراج المعاملة الجديدة
                cursor.execute("""
                    INSERT INTO accounts_accounttransaction 
                    (transaction_number, date, customer_supplier_id, transaction_type, direction, 
                     amount, reference_type, reference_id, description, balance_after, 
                     created_by_id, created_at, updated_at)
                    VALUES (?, ?, ?, 'purchase_return', 'credit', ?, 'purchase_return', ?, ?, ?, 1, 
                            datetime('now'), datetime('now'))
                """, (
                    transaction_number, pr_date, customer_id, total_amount, pr_id,
                    f'مردود مشتريات - فاتورة رقم {return_number}', new_balance
                ))
                
                print(f"✓ تم إنشاء معاملة: {transaction_number}")
                print(f"  - الرصيد الجديد: {new_balance}")
                
            else:
                print("المعاملة موجودة مسبقاً")
    else:
        print("لا يوجد عميل مطابق")
else:
    print("مردود المشتريات غير موجود")

# حفظ التغييرات
conn.commit()
conn.close()
print("تم حفظ التغييرات")
