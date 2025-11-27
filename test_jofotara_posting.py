#!/usr/bin/env python
"""
Test script for JoFotara posting functionality with QR Code validation
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from settings.utils import send_invoice_to_jofotara as send_invoice_api
from django.contrib.auth import get_user_model

User = get_user_model()

def test_jofotara_posting():
    """Test JoFotara posting with QR Code validation"""
    
    print("=" * 70)
    print("Testing JoFotara QR Code Integration")
    print("=" * 70)
    
    # Get the most recent invoice
    invoice = SalesInvoice.objects.order_by('-created_at').first()
    
    if not invoice:
        print("❌ No invoices found in database. Please create an invoice first.")
        return
    
    print(f"\n✅ Found invoice: {invoice.invoice_number}")
    print(f"   Customer: {invoice.customer.name}")
    print(f"   Total: {invoice.total_amount}")
    print(f"   Date: {invoice.date}")
    
    # Check current JoFotara status
    print(f"\n📊 Current JoFotara Status:")
    print(f"   Posted to Tax: {invoice.is_posted_to_tax}")
    print(f"   UUID: {invoice.jofotara_uuid or 'Not sent'}")
    print(f"   QR Code: {'✅ Present' if invoice.jofotara_qr_code else '❌ Missing'}")
    
    if invoice.jofotara_qr_code:
        print(f"   QR Code length: {len(invoice.jofotara_qr_code)} characters")
    
    # Prepare invoice data for API
    print("\n🔄 Preparing to send invoice to JoFotara...")
    
    # Get company settings
    from settings.models import CompanySettings
    company = CompanySettings.objects.first()
    
    invoice_data = {
        'invoice_number': invoice.invoice_number,
        'issue_date': invoice.date.isoformat(),
        'issue_time': invoice.created_at.time().isoformat() if hasattr(invoice, 'created_at') else '12:00:00',
        'seller': {
            'name': company.company_name if company else 'Test Company',
            'tax_number': company.tax_number if company else '123456789',
        },
        'buyer': {
            'name': invoice.customer.name,
            'tax_number': getattr(invoice.customer, 'tax_number', ''),
        },
        'lines': [
            {
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'tax_percent': float(item.tax_rate) if hasattr(item, 'tax_rate') else 0,
                'total': float(item.total_amount),
            } for item in invoice.items.all()
        ],
        'currency': 'JOD',
    }
    
    print(f"   Invoice data prepared with {len(invoice_data['lines'])} items")
    
    # Send to JoFotara
    print("\n📤 Sending to JoFotara API...")
    result = send_invoice_api(invoice_data, 'sales')
    
    print("\n📬 API Response:")
    print(f"   Success: {result.get('success', False)}")
    
    if result.get('success'):
        print(f"   ✅ UUID: {result.get('uuid', 'N/A')}")
        print(f"   ✅ QR Code: {'Present' if result.get('qr_code') else '❌ MISSING'}")
        print(f"   ✅ Verification URL: {result.get('verification_url', 'N/A')}")
        
        if result.get('qr_code'):
            qr_length = len(result['qr_code'])
            print(f"   ✅ QR Code Length: {qr_length} characters")
            
            # Validate QR Code format
            if result['qr_code'].startswith('data:image'):
                print(f"   ✅ QR Code Format: Base64 image")
            elif result['qr_code'].startswith('http'):
                print(f"   ✅ QR Code Format: URL")
            else:
                print(f"   ⚠️  QR Code Format: Unknown (first 50 chars: {result['qr_code'][:50]})")
        else:
            print(f"   ❌ WARNING: No QR Code received from server!")
            print(f"   ⚠️  Posting should be marked as failed!")
        
        # Save to database (simulating the view logic)
        print("\n💾 Saving to database...")
        invoice.jofotara_uuid = result.get('uuid')
        invoice.jofotara_verification_url = result.get('verification_url')
        invoice.jofotara_qr_code = result.get('qr_code')
        
        # Only mark as posted if QR Code is present
        if result.get('qr_code'):
            invoice.is_posted_to_tax = True
            print("   ✅ Marked as posted to tax (QR Code validated)")
        else:
            invoice.is_posted_to_tax = False
            print("   ❌ NOT marked as posted to tax (QR Code missing)")
        
        invoice.save()
        print("   ✅ Invoice saved successfully")
        
        # Verify database update
        print("\n🔍 Verifying database update...")
        invoice.refresh_from_db()
        print(f"   Posted to Tax: {invoice.is_posted_to_tax}")
        print(f"   UUID in DB: {invoice.jofotara_uuid or 'Not saved'}")
        print(f"   QR Code in DB: {'✅ Present' if invoice.jofotara_qr_code else '❌ Missing'}")
        
        if invoice.jofotara_qr_code:
            print(f"   QR Code length in DB: {len(invoice.jofotara_qr_code)} characters")
    else:
        print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)
    
    # Summary
    print("\n📋 Summary:")
    if result.get('success') and result.get('qr_code'):
        print("   ✅ Test PASSED: Invoice posted successfully with QR Code")
        print("   ✅ QR Code validation: Working correctly")
        print("   ✅ Database update: Successful")
    elif result.get('success') and not result.get('qr_code'):
        print("   ⚠️  Test PARTIAL: Invoice posted but QR Code missing")
        print("   ❌ QR Code validation: FAILED - No QR Code received")
        print("   ⚠️  This should trigger a warning message to user")
    else:
        print("   ❌ Test FAILED: API error")
        print(f"   ❌ Error: {result.get('error', 'Unknown')}")
    
    return result

if __name__ == '__main__':
    try:
        result = test_jofotara_posting()
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
