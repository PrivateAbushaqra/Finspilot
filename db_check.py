import sqlite3

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

print("فحص مردودات المشتريات ومعاملات العميل:")
print("=" * 50)

# فحص العميل رقم 14
cursor.execute("SELECT id, name, type FROM customers_customersupplier WHERE id = 14")
customer = cursor.fetchone()
if customer:
    print(f"العميل: {customer[1]} (ID: {customer[0]}, نوع: {customer[2]})")
else:
    print("العميل رقم 14 غير موجود")
    exit()

# فحص مردودات المشتريات
cursor.execute("""
    SELECT pr.id, pr.return_number, pr.date, pr.total_amount,
           cs.id as supplier_id, cs.name as supplier_name, cs.type as supplier_type
    FROM purchases_purchasereturn pr
    JOIN purchases_purchaseinvoice pi ON pr.original_invoice_id = pi.id
    JOIN customers_customersupplier cs ON pi.supplier_id = cs.id
    ORDER BY pr.id
""")

purchase_returns = cursor.fetchall()
print(f"\nمردودات المشتريات: {len(purchase_returns)}")

for pr in purchase_returns:
    pr_id, return_number, date, amount, supplier_id, supplier_name, supplier_type = pr
    print(f"\nمردود {pr_id}: {return_number}")
    print(f"  - المورد: {supplier_name} (ID: {supplier_id}, نوع: {supplier_type})")
    print(f"  - التاريخ: {date}")
    print(f"  - المبلغ: {amount}")
    
    # فحص العلاقة مع العميل
    if supplier_id == 14:
        print("  ✓ المورد هو نفس العميل")
    elif supplier_name == customer[1]:
        print("  ⚠ المورد والعميل لهما نفس الاسم")
    else:
        print("  ✗ المورد مختلف عن العميل")

# فحص معاملات العميل
cursor.execute("""
    SELECT transaction_type, reference_id, amount, description
    FROM accounts_accounttransaction 
    WHERE customer_supplier_id = 14
    ORDER BY created_at DESC
""")

transactions = cursor.fetchall()
print(f"\nمعاملات العميل رقم 14: {len(transactions)}")

purchase_return_transactions = [t for t in transactions if t[0] == 'purchase_return']
print(f"معاملات مردود المشتريات: {len(purchase_return_transactions)}")

for trans in purchase_return_transactions:
    print(f"  - {trans[0]}: مرجع {trans[1]} - {trans[2]} - {trans[3]}")

# فحص جميع معاملات مردود المشتريات
cursor.execute("""
    SELECT at.transaction_number, at.customer_supplier_id, cs.name, at.reference_id, at.amount
    FROM accounts_accounttransaction at
    JOIN customers_customersupplier cs ON at.customer_supplier_id = cs.id
    WHERE at.transaction_type = 'purchase_return'
    ORDER BY at.created_at DESC
""")

all_return_transactions = cursor.fetchall()
print(f"\nجميع معاملات مردود المشتريات: {len(all_return_transactions)}")

for trans in all_return_transactions:
    trans_num, cust_id, cust_name, ref_id, amount = trans
    print(f"  - {trans_num}: {cust_name} (ID: {cust_id}) - مرجع {ref_id} - {amount}")
    if cust_id == 14:
        print("    ✓ هذه معاملة العميل رقم 14")

conn.close()
