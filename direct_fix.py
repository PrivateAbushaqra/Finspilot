import sqlite3
import uuid
from datetime import datetime

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

print("إصلاح معاملات مردود المشتريات:")
print("=" * 40)

# فحص مردودات المشتريات
cursor.execute("""
    SELECT pr.id, pr.return_number, pr.date, pr.total_amount,
           pi.supplier_id, cs.name as supplier_name, cs.type as supplier_type
    FROM purchases_purchasereturn pr
    JOIN purchases_purchaseinvoice pi ON pr.original_invoice_id = pi.id
    JOIN customers_customersupplier cs ON pi.supplier_id = cs.id
""")

purchase_returns = cursor.fetchall()
print(f"مردودات المشتريات: {len(purchase_returns)}")

for pr in purchase_returns:
    pr_id, return_number, date, amount, supplier_id, supplier_name, supplier_type = pr
    print(f"\nمردود {pr_id}: {return_number}")
    print(f"  المورد: {supplier_name} (ID: {supplier_id})")
    
    # فحص المعاملات الموجودة
    cursor.execute("""
        SELECT COUNT(*) FROM accounts_accounttransaction 
        WHERE transaction_type = 'purchase_return' AND reference_id = ?
    """, (pr_id,))
    
    existing_count = cursor.fetchone()[0]
    print(f"  معاملات موجودة: {existing_count}")
    
    if existing_count == 0:
        print("  إنشاء معاملة للمورد...")
        
        # إنشاء معاملة للمورد
        transaction_number = f"PRET-{uuid.uuid4().hex[:8].upper()}"
        
        # حساب الرصيد السابق
        cursor.execute("""
            SELECT balance_after FROM accounts_accounttransaction 
            WHERE customer_supplier_id = ? ORDER BY created_at DESC LIMIT 1
        """, (supplier_id,))
        
        last_balance = cursor.fetchone()
        previous_balance = last_balance[0] if last_balance else 0
        new_balance = previous_balance - float(amount)
        
        # إدراج معاملة المورد
        cursor.execute("""
            INSERT INTO accounts_accounttransaction 
            (transaction_number, date, customer_supplier_id, transaction_type, direction, 
             amount, reference_type, reference_id, description, balance_after, 
             created_by_id, created_at, updated_at)
            VALUES (?, ?, ?, 'purchase_return', 'debit', ?, 'purchase_return', ?, ?, ?, 1, 
                    datetime('now'), datetime('now'))
        """, (
            transaction_number, date, supplier_id, amount, pr_id,
            f'مردود مشتريات - فاتورة رقم {return_number}', new_balance
        ))
        
        print(f"  ✓ معاملة المورد: {transaction_number}")
        
        # البحث عن عميل بنفس الاسم
        cursor.execute("""
            SELECT id, name FROM customers_customersupplier 
            WHERE name = ? AND type IN ('customer', 'both') AND id != ?
        """, (supplier_name, supplier_id))
        
        matching_customers = cursor.fetchall()
        print(f"  عملاء مطابقون: {len(matching_customers)}")
        
        for customer_id, customer_name in matching_customers:
            print(f"    العميل: {customer_name} (ID: {customer_id})")
            
            # فحص إذا كانت معاملة العميل موجودة
            cursor.execute("""
                SELECT COUNT(*) FROM accounts_accounttransaction 
                WHERE customer_supplier_id = ? AND transaction_type = 'purchase_return' AND reference_id = ?
            """, (customer_id, pr_id))
            
            customer_existing = cursor.fetchone()[0]
            
            if customer_existing == 0:
                # إنشاء معاملة للعميل
                customer_transaction_number = f"PRET-C-{uuid.uuid4().hex[:8].upper()}"
                
                # حساب الرصيد السابق للعميل
                cursor.execute("""
                    SELECT balance_after FROM accounts_accounttransaction 
                    WHERE customer_supplier_id = ? ORDER BY created_at DESC LIMIT 1
                """, (customer_id,))
                
                customer_last_balance = cursor.fetchone()
                customer_previous_balance = customer_last_balance[0] if customer_last_balance else 0
                customer_new_balance = customer_previous_balance + float(amount)
                
                # إدراج معاملة العميل
                cursor.execute("""
                    INSERT INTO accounts_accounttransaction 
                    (transaction_number, date, customer_supplier_id, transaction_type, direction, 
                     amount, reference_type, reference_id, description, balance_after, 
                     created_by_id, created_at, updated_at)
                    VALUES (?, ?, ?, 'purchase_return', 'credit', ?, 'purchase_return', ?, ?, ?, 1, 
                            datetime('now'), datetime('now'))
                """, (
                    customer_transaction_number, date, customer_id, amount, pr_id,
                    f'مردود مشتريات - فاتورة رقم {return_number} (عميل مرتبط)', customer_new_balance
                ))
                
                print(f"    ✓ معاملة العميل: {customer_transaction_number}")
            else:
                print(f"    ✓ معاملة العميل موجودة مسبقاً")

# فحص نهائي للعميل رقم 14
cursor.execute("""
    SELECT COUNT(*) FROM accounts_accounttransaction 
    WHERE customer_supplier_id = 14 AND transaction_type = 'purchase_return'
""")

final_count = cursor.fetchone()[0]
print(f"\nمعاملات مردود المشتريات للعميل 14: {final_count}")

# حفظ التغييرات
conn.commit()
conn.close()
print("تم حفظ التغييرات بنجاح")
