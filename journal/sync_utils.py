"""
أدوات مزامنة أرصدة الصناديق والبنوك
"""
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def sync_all_cashboxes_and_banks():
    """
    مزامنة جميع أرصدة الصناديق والبنوك مع أرصدة حساباتهم المحاسبية
    
    Returns:
        dict: تقرير المزامنة
    """
    from cashboxes.models import Cashbox
    from banks.models import BankAccount
    from journal.models import Account
    
    report = {
        'cashboxes': {'synced': 0, 'errors': []},
        'banks': {'synced': 0, 'errors': []}
    }
    
    # مزامنة الصناديق
    for cashbox in Cashbox.objects.all():
        try:
            # البحث عن الحساب المحاسبي المرتبط
            account = None
            
            if '1001' in cashbox.name:
                account = Account.objects.filter(code='101004').first()
            elif '1002' in cashbox.name:
                account = Account.objects.filter(code='101005').first()
            else:
                # بحث عام
                account = Account.objects.filter(
                    code__startswith='101',
                    name__icontains=cashbox.name.split()[-1]
                ).first()
            
            if account:
                old_balance = cashbox.balance
                new_balance = account.balance
                
                if old_balance != new_balance:
                    cashbox.balance = new_balance
                    cashbox.save(update_fields=['balance'])
                    report['cashboxes']['synced'] += 1
                    logger.info(f"✅ مزامنة صندوق '{cashbox.name}': {old_balance} → {new_balance}")
            else:
                report['cashboxes']['errors'].append(
                    f"لم يتم العثور على حساب محاسبي للصندوق: {cashbox.name}"
                )
                
        except Exception as e:
            report['cashboxes']['errors'].append(
                f"خطأ في مزامنة الصندوق {cashbox.name}: {str(e)}"
            )
    
    # مزامنة البنوك
    for bank in BankAccount.objects.all():
        try:
            # البحث عن الحساب المحاسبي المرتبط
            account = Account.objects.filter(
                code__startswith='1101',
                name__icontains=bank.name.split()[0]
            ).first()
            
            if not account:
                # محاولة بحث بواسطة اسم البنك
                account = Account.objects.filter(
                    code__startswith='1101',
                    name__icontains=bank.bank_name
                ).first()
            
            if account:
                old_balance = bank.balance
                new_balance = account.balance
                
                if old_balance != new_balance:
                    bank.balance = new_balance
                    bank.save(update_fields=['balance'])
                    report['banks']['synced'] += 1
                    logger.info(f"✅ مزامنة بنك '{bank.name}': {old_balance} → {new_balance}")
            else:
                report['banks']['errors'].append(
                    f"لم يتم العثور على حساب محاسبي للبنك: {bank.name} - {bank.bank_name}"
                )
                
        except Exception as e:
            report['banks']['errors'].append(
                f"خطأ في مزامنة البنك {bank.name}: {str(e)}"
            )
    
    return report
