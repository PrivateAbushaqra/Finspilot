import json
import uuid
import base64
import requests
from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree as ET
from xml.dom import minidom
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import JoFotaraSettings
import logging

logger = logging.getLogger(__name__)

class JoFotaraAPI:
    """JoFotara API integration class for electronic invoicing"""

    def __init__(self):
        self.settings = JoFotaraSettings.objects.first()
        if not self.settings:
            raise ValueError("JoFotara settings not configured")
        self.access_token = None
        self.token_expires_at = None

    def test_connection(self):
        """Test connection to JoFotara API"""
        try:
            if self.settings.use_mock_api:
                return {
                    'success': True,
                    'message': 'Mock API connection successful',
                    'response_time': '0.1s'
                }

            # Real API test
            headers = self._get_headers()
            test_url = f"{self.settings.api_url.rstrip('/')}/config"

            response = requests.get(test_url, headers=headers, timeout=30)

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'API connection successful',
                    'response_time': f"{response.elapsed.total_seconds():.2f}s"
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }

        except requests.RequestException as e:
            logger.error(f"JoFotara API connection test failed: {str(e)}")
            return {
                'success': False,
                'error': f"Connection failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error in test_connection: {str(e)}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }

    def send_invoice(self, invoice_data, invoice_type='sales'):
        """Send invoice to JoFotara API"""
        try:
            # Check if JoFotara integration is enabled
            if not self.settings.is_active:
                return {
                    'success': False,
                    'error': 'تكامل JoFotara غير مفعل. يرجى تفعيله في إعدادات JoFotara.'
                }

            # Generate JSON data
            json_data = self.generate_invoice_json(invoice_data, invoice_type)

            # Convert to UBL XML
            xml_content = self.convert_to_ubl_xml(json_data)

            if self.settings.use_mock_api:
                return self._mock_send_invoice(xml_content, json_data)

            # Get headers with OAuth token
            headers = self._get_headers()
            
            # Debug: Log headers being sent
            logger.info(f"Sending request to JoFotara with Authorization: Bearer {headers.get('Authorization', '')[:50]}...")

            # Encode XML to base64
            xml_base64 = base64.b64encode(xml_content.encode('utf-8')).decode('utf-8')

            # Prepare payload according to server specification
            payload = {
                'invoice': xml_base64,
                'invoiceNumber': invoice_data.get('invoice_number', 'UNKNOWN')
            }

            # Use data parameter with json.dumps to preserve headers
            import json as json_module
            response = requests.post(
                f"{self.settings.api_url.rstrip('/')}/core/invoices",
                data=json_module.dumps(payload),
                headers=headers,
                timeout=60
            )
            
            # Debug: Log response
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:200]}")

            if response.status_code == 200:
                response_data = response.json()
                # Map server response to expected format
                return {
                    'success': True,
                    'uuid': response_data.get('uuid'),
                    'qr_code': response_data.get('qrCode'),
                    'verification_url': response_data.get('verificationUrl'),
                    'xml_content': xml_content,
                    'message': response_data.get('message')
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }

        except Exception as e:
            logger.error(f"Error sending invoice to JoFotara: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_invoice_json(self, invoice_data, invoice_type='sales'):
        """Generate JSON data for invoice according to JoFotara schema"""
        try:
            # Base invoice structure
            invoice_json = {
                "InvoiceID": invoice_data.get('invoice_number', ''),
                "IssueDate": invoice_data.get('issue_date', datetime.now().date().isoformat()),
                "IssueTime": invoice_data.get('issue_time', datetime.now().time().isoformat()),
                "InvoiceType": self._get_invoice_type_code(invoice_type),
                "CurrencyCode": invoice_data.get('currency', 'JOD'),
                "TaxCurrencyCode": "JOD",
                "Seller": self._format_party_data(invoice_data.get('seller', {})),
                "Buyer": self._format_party_data(invoice_data.get('buyer', {})),
                "InvoiceLines": self._format_invoice_lines(invoice_data.get('lines', [])),
                "TaxTotals": self._calculate_tax_totals(invoice_data.get('lines', [])),
                "LegalMonetaryTotal": self._calculate_legal_monetary_total(invoice_data.get('lines', []))
            }

            # Add credit/debit note specific fields
            if invoice_type in ['credit_note', 'debit_note']:
                invoice_json.update({
                    "BillingReference": {
                        "InvoiceDocumentReference": {
                            "ID": invoice_data.get('original_invoice_number', ''),
                            "IssueDate": invoice_data.get('original_invoice_date', '')
                        }
                    }
                })

            return invoice_json

        except Exception as e:
            logger.error(f"Error generating invoice JSON: {str(e)}")
            raise

    def convert_to_ubl_xml(self, json_data):
        """Convert JSON invoice data to UBL 2.1 XML format"""
        try:
            # Create root element
            root = ET.Element("Invoice", xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2")

            # Add namespaces
            root.set("xmlns:cac", "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2")
            root.set("xmlns:cbc", "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2")

            # Add UBLVersionID
            ubl_version = ET.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}UBLVersionID")
            ubl_version.text = "2.1"

            # Add Invoice ID
            invoice_id = ET.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            invoice_id.text = json_data.get('InvoiceID', '')

            # Add Issue Date
            issue_date = ET.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}IssueDate")
            issue_date.text = json_data.get('IssueDate', '')

            # Add Invoice Type Code
            invoice_type_code = ET.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode")
            invoice_type_code.text = json_data.get('InvoiceType', '380')

            # Add Seller Party
            self._add_party_to_xml(root, json_data.get('Seller', {}), "AccountingSupplierParty")

            # Add Buyer Party
            self._add_party_to_xml(root, json_data.get('Buyer', {}), "AccountingCustomerParty")

            # Add Invoice Lines
            for line_data in json_data.get('InvoiceLines', []):
                self._add_invoice_line_to_xml(root, line_data)

            # Convert to string and pretty print
            rough_string = ET.tostring(root, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            xml_content = reparsed.toprettyxml(indent="  ", encoding=None)

            # Remove XML declaration and clean up
            lines = xml_content.split('\n')
            xml_content = '\n'.join(lines[1:])  # Remove first line (XML declaration)

            return xml_content.strip()

        except Exception as e:
            logger.error(f"Error converting to UBL XML: {str(e)}")
            raise

    def _get_oauth_token(self):
        """Get OAuth 2.0 access token from JoFotara API"""
        try:
            # Check if we have a valid token
            if self.access_token and self.token_expires_at:
                from datetime import datetime, timezone
                if datetime.now(timezone.utc) < self.token_expires_at:
                    return self.access_token
            
            # Request new token
            token_url = f"{self.settings.api_url.rstrip('/')}/oauth/token"
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.settings.client_id,
                'client_secret': self.settings.client_secret
            }
            
            response = requests.post(
                token_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                
                # Calculate expiry time
                from datetime import datetime, timedelta, timezone
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
                
                logger.info(f"OAuth token obtained successfully, expires in {expires_in}s")
                return self.access_token
            else:
                logger.error(f"Failed to get OAuth token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting OAuth token: {str(e)}")
            return None

    def _get_headers(self):
        """Get authentication headers for API requests"""
        if self.settings.use_mock_api:
            return {'Content-Type': 'application/json'}

        # Get OAuth token
        token = self._get_oauth_token()
        if not token:
            raise ValueError("Failed to obtain OAuth access token")

        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    def _get_invoice_type_code(self, invoice_type):
        """Get UBL invoice type code"""
        type_codes = {
            'sales': '380',  # Commercial Invoice
            'credit_note': '381',  # Credit Note
            'debit_note': '384'  # Debit Note
        }
        return type_codes.get(invoice_type, '380')

    def _format_party_data(self, party_data):
        """Format party data for JSON"""
        return {
            "PartyIdentification": {
                "ID": party_data.get('id', ''),
                "schemeID": party_data.get('scheme_id', 'TN')
            },
            "PostalAddress": {
                "StreetName": party_data.get('street', ''),
                "BuildingNumber": party_data.get('building_number', ''),
                "CityName": party_data.get('city', ''),
                "PostalZone": party_data.get('postal_code', ''),
                "Country": {
                    "IdentificationCode": party_data.get('country_code', 'JO')
                }
            },
            "PartyTaxScheme": {
                "CompanyID": party_data.get('tax_id', ''),
                "TaxScheme": {
                    "ID": "VAT"
                }
            },
            "PartyLegalEntity": {
                "RegistrationName": party_data.get('name', ''),
                "CompanyID": party_data.get('company_id', '')
            },
            "Contact": {
                "ElectronicMail": party_data.get('email', ''),
                "Telephone": party_data.get('phone', '')
            }
        }

    def _format_invoice_lines(self, lines_data):
        """Format invoice lines for JSON"""
        formatted_lines = []
        for line in lines_data:
            formatted_line = {
                "ID": str(line.get('id', '')),
                "InvoicedQuantity": {
                    "unitCode": line.get('unit_code', 'EA'),
                    "_text": str(line.get('quantity', 0))
                },
                "LineExtensionAmount": {
                    "currencyID": "JOD",
                    "_text": str(line.get('line_extension_amount', 0))
                },
                "Item": {
                    "Name": line.get('name', ''),
                    "ClassifiedTaxCategory": {
                        "ID": "S",
                        "Percent": str(line.get('tax_percent', 16)),
                        "TaxScheme": {
                            "ID": "VAT"
                        }
                    }
                },
                "Price": {
                    "PriceAmount": {
                        "currencyID": "JOD",
                        "_text": str(line.get('unit_price', 0))
                    }
                }
            }
            formatted_lines.append(formatted_line)
        return formatted_lines

    def _calculate_tax_totals(self, lines_data):
        """Calculate tax totals from invoice lines"""
        total_tax = Decimal('0')
        for line in lines_data:
            quantity = Decimal(str(line.get('quantity', 0)))
            unit_price = Decimal(str(line.get('unit_price', 0)))
            tax_percent = Decimal(str(line.get('tax_percent', 16)))
            line_total = quantity * unit_price
            tax_amount = line_total * (tax_percent / Decimal('100'))
            total_tax += tax_amount

        return [{
            "TaxAmount": {
                "currencyID": "JOD",
                "_text": str(total_tax)
            },
            "TaxSubtotal": {
                "TaxableAmount": {
                    "currencyID": "JOD",
                    "_text": str(total_tax / (Decimal('1') + Decimal('16')/Decimal('100')))
                },
                "TaxAmount": {
                    "currencyID": "JOD",
                    "_text": str(total_tax)
                },
                "TaxCategory": {
                    "ID": "S",
                    "Percent": "16",
                    "TaxScheme": {
                        "ID": "VAT"
                    }
                }
            }
        }]

    def _calculate_legal_monetary_total(self, lines_data):
        """Calculate legal monetary total"""
        total_amount = Decimal('0')
        for line in lines_data:
            quantity = Decimal(str(line.get('quantity', 0)))
            unit_price = Decimal(str(line.get('unit_price', 0)))
            total_amount += quantity * unit_price

        tax_total = self._calculate_tax_totals(lines_data)[0]['TaxAmount']['_text']
        tax_total = Decimal(tax_total)
        grand_total = total_amount + tax_total

        return {
            "LineExtensionAmount": {
                "currencyID": "JOD",
                "_text": str(total_amount)
            },
            "TaxExclusiveAmount": {
                "currencyID": "JOD",
                "_text": str(total_amount)
            },
            "TaxInclusiveAmount": {
                "currencyID": "JOD",
                "_text": str(grand_total)
            },
            "PayableAmount": {
                "currencyID": "JOD",
                "_text": str(grand_total)
            }
        }

    def _add_party_to_xml(self, root, party_data, party_type):
        """Add party information to XML"""
        party_element = ET.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}{party_type}")
        party = ET.SubElement(party_element, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Party")

        # Party Identification
        if party_data.get('PartyIdentification', {}).get('ID'):
            party_identification = ET.SubElement(party, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyIdentification")
            party_id = ET.SubElement(party_identification, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
            party_id.text = party_data['PartyIdentification']['ID']
            if party_data['PartyIdentification'].get('schemeID'):
                party_id.set("schemeID", party_data['PartyIdentification']['schemeID'])

        # Party Name
        if party_data.get('PartyLegalEntity', {}).get('RegistrationName'):
            party_name = ET.SubElement(party, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}PartyName")
            name = ET.SubElement(party_name, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name")
            name.text = party_data['PartyLegalEntity']['RegistrationName']

    def _add_invoice_line_to_xml(self, root, line_data):
        """Add invoice line to XML"""
        invoice_line = ET.SubElement(root, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}InvoiceLine")

        # Line ID
        line_id = ET.SubElement(invoice_line, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID")
        line_id.text = line_data.get('ID', '')

        # Invoiced Quantity
        quantity = ET.SubElement(invoice_line, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoicedQuantity")
        quantity.text = line_data.get('InvoicedQuantity', {}).get('_text', '0')
        quantity.set("unitCode", line_data.get('InvoicedQuantity', {}).get('unitCode', 'EA'))

        # Line Extension Amount
        line_extension = ET.SubElement(invoice_line, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}LineExtensionAmount")
        line_extension.text = line_data.get('LineExtensionAmount', {}).get('_text', '0')
        line_extension.set("currencyID", line_data.get('LineExtensionAmount', {}).get('currencyID', 'JOD'))

        # Item
        item = ET.SubElement(invoice_line, "{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}Item")
        item_name = ET.SubElement(item, "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}Name")
        item_name.text = line_data.get('Item', {}).get('Name', '')

    def _mock_send_invoice(self, xml_content, json_data):
        """Mock API response for testing"""
        try:
            # Generate fake UUID
            fake_uuid = str(uuid.uuid4())

            # Generate fake QR code as Data URL (ready to display in <img> tag)
            # Create a simple PNG QR code data URL for testing
            fake_qr_base64 = base64.b64encode(b"Mock QR Code Data").decode()
            # Format as data URL so it can be used directly in <img src="">
            fake_qr_data_url = f"data:image/png;base64,{fake_qr_base64}"

            # Save XML file locally
            file_name = f"invoice_{json_data.get('InvoiceID', fake_uuid)}.xml"
            file_path = f"invoices/{file_name}"

            # Ensure directory exists
            default_storage.save(file_path, ContentFile(xml_content.encode('utf-8')))

            return {
                'success': True,
                'uuid': fake_uuid,
                'qr_code': fake_qr_data_url,  # Return as data URL
                'verification_url': f"https://mock.jofotara.gov.jo/verify/{fake_uuid}",
                'xml_content': xml_content,
                'saved_file': file_path
            }

        except Exception as e:
            logger.error(f"Error in mock send invoice: {str(e)}")
            return {
                'success': False,
                'error': f"Mock API error: {str(e)}"
            }


def get_jofotara_api():
    """Factory function to get JoFotaraAPI instance"""
    return JoFotaraAPI()


def test_jofotara_connection():
    """Test JoFotara API connection"""
    try:
        api = get_jofotara_api()
        return api.test_connection()
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def send_invoice_to_jofotara(invoice_data, invoice_type='sales'):
    """Send invoice to JoFotara API"""
    try:
        api = get_jofotara_api()
        return api.send_invoice(invoice_data, invoice_type)
    except Exception as e:
        logger.error(f"Error sending invoice: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def prepare_sales_invoice_data(sales_invoice):
    """Prepare sales invoice data for JoFotara API"""
    from sales.models import SalesInvoice, SalesInvoiceItem
    from customers.models import CustomerSupplier as Customer
    from core.models import CompanySettings

    try:
        # Get company settings
        company_settings = CompanySettings.objects.first()
        if not company_settings:
            raise ValueError("Company settings not found")

        # Get customer data
        customer = sales_invoice.customer

        # Prepare seller data
        seller_data = {
            'id': company_settings.tax_number or '',
            'scheme_id': 'TN',
            'name': company_settings.company_name or '',
            'street': company_settings.address or '',
            'city': '',  # CompanySettings doesn't have city field
            'country_code': 'JO',
            'tax_id': company_settings.tax_number or '',
            'company_id': '',  # CompanySettings doesn't have registration_number field
            'email': company_settings.email or '',
            'phone': company_settings.phone or ''
        }

        # Prepare buyer data
        buyer_data = {
            'id': customer.tax_number or str(customer.sequence_number) or '',
            'scheme_id': 'TN' if customer.tax_number else 'ID',
            'name': customer.name or '',
            'street': customer.address or '',
            'city': customer.city or '',
            'country_code': 'JO',
            'tax_id': customer.tax_number or '',
            'company_id': str(customer.sequence_number) or '',  # Use sequence_number as company_id
            'email': customer.email or '',
            'phone': customer.phone or ''
        }

        # Prepare invoice lines
        lines_data = []
        for item in sales_invoice.items.all():
            line_data = {
                'id': str(item.id),
                'name': item.product.name if item.product else item.description,
                'quantity': float(item.quantity),
                'unit_code': 'EA',  # Default unit
                'unit_price': float(item.unit_price),
                'line_extension_amount': float(item.total_amount),  # Use total_amount instead of total
                'tax_percent': 16  # Standard VAT rate
            }
            lines_data.append(line_data)

        # Prepare invoice data
        invoice_data = {
            'invoice_number': sales_invoice.invoice_number,
            'issue_date': sales_invoice.date.isoformat(),
            'issue_time': sales_invoice.created_at.time().isoformat() if sales_invoice.created_at else datetime.now().time().isoformat(),
            'currency': company_settings.currency,  # Use company currency instead of invoice.currency
            'seller': seller_data,
            'buyer': buyer_data,
            'lines': lines_data
        }

        return invoice_data

    except Exception as e:
        logger.error(f"Error preparing sales invoice data: {str(e)}")
        raise


def prepare_credit_note_data(credit_note):
    """Prepare credit note data for JoFotara API"""
    from sales.models import SalesCreditNote
    from core.models import CompanySettings
    
    try:
        # Get company settings
        company_settings = CompanySettings.objects.first()
        if not company_settings:
            raise ValueError("Company settings not found")

        # Get customer data
        customer = credit_note.customer

        # Prepare seller data
        seller_data = {
            'id': company_settings.tax_number or '',
            'scheme_id': 'TN',
            'name': company_settings.company_name or '',
            'street': company_settings.address or '',
            'city': '',  # CompanySettings doesn't have city field
            'country_code': 'JO',
            'tax_id': company_settings.tax_number or '',
            'company_id': '',  # CompanySettings doesn't have registration_number field
            'email': company_settings.email or '',
            'phone': company_settings.phone or ''
        }

        # Prepare buyer data
        buyer_data = {
            'id': customer.tax_number or str(customer.sequence_number) or '',
            'scheme_id': 'TN' if customer.tax_number else 'ID',
            'name': customer.name or '',
            'street': customer.address or '',
            'city': customer.city or '',
            'country_code': 'JO',
            'tax_id': customer.tax_number or '',
            'company_id': str(customer.sequence_number) or '',
            'email': customer.email or '',
            'phone': customer.phone or ''
        }

        # Since credit note doesn't have items, create a single line with the total amount
        lines_data = [{
            'id': '1',
            'description': credit_note.notes or 'Credit Note',
            'quantity': 1,
            'unit_price': float(credit_note.subtotal),
            'tax_amount': float(credit_note.total_amount - credit_note.subtotal),
            'line_total': float(credit_note.total_amount)
        }]

        # Prepare invoice data
        invoice_data = {
            'invoice_number': credit_note.note_number,
            'issue_date': credit_note.date.isoformat(),
            'issue_time': credit_note.created_at.time().isoformat() if credit_note.created_at else datetime.now().time().isoformat(),
            'currency': company_settings.currency,
            'seller': seller_data,
            'buyer': buyer_data,
            'lines': lines_data
        }

        # Check if credit note has original_invoice field (optional)
        if hasattr(credit_note, 'original_invoice') and credit_note.original_invoice:
            invoice_data.update({
                'original_invoice_number': credit_note.original_invoice.invoice_number,
                'original_invoice_date': credit_note.original_invoice.date.isoformat()
            })

        return invoice_data

    except Exception as e:
        logger.error(f"Error preparing credit note data: {str(e)}")
        raise


def prepare_debit_note_data(debit_note):
    """Prepare debit note data for JoFotara API"""
    from purchases.models import PurchaseDebitNote
    from core.models import CompanySettings

    try:
        # Get company settings for seller information
        company_settings = CompanySettings.objects.first()
        if not company_settings:
            raise ValueError("Company settings not configured")

        # Get supplier (buyer in debit note context) information
        supplier = debit_note.supplier

        # Prepare seller data (company)
        seller_data = {
            'id': company_settings.tax_number or '',
            'scheme_id': 'TN',
            'name': company_settings.company_name or '',
            'street': company_settings.address or '',
            'city': '',  # CompanySettings doesn't have city field
            'country_code': 'JO',
            'tax_id': company_settings.tax_number or '',
            'company_id': '',  # CompanySettings doesn't have registration_number
            'email': company_settings.email or '',
            'phone': company_settings.phone or ''
        }

        # Prepare buyer data (supplier)
        buyer_data = {
            'id': supplier.tax_number or str(supplier.sequence_number) or '',
            'scheme_id': 'TN' if supplier.tax_number else 'ID',
            'name': supplier.name or '',
            'street': supplier.address or '',
            'city': supplier.city or '',
            'country_code': 'JO',
            'tax_id': supplier.tax_number or '',
            'company_id': str(supplier.sequence_number) or '',
            'email': supplier.email or '',
            'phone': supplier.phone or ''
        }

        # Since debit note doesn't have items, create a single line with the total amount
        lines_data = [{
            'id': '1',
            'description': debit_note.notes or f'Debit Note {debit_note.note_number}',
            'quantity': 1,
            'unit_price': float(debit_note.subtotal),
            'tax_amount': float(debit_note.total_amount - debit_note.subtotal),
            'line_total': float(debit_note.total_amount)
        }]

        # Prepare invoice data
        invoice_data = {
            'invoice_number': debit_note.note_number,
            'issue_date': debit_note.date.isoformat(),
            'issue_time': debit_note.created_at.time().isoformat() if debit_note.created_at else datetime.now().time().isoformat(),
            'currency': company_settings.currency,
            'seller': seller_data,
            'buyer': buyer_data,
            'lines': lines_data
        }

        return invoice_data

    except Exception as e:
        logger.error(f"Error preparing debit note data: {str(e)}")
        raise


def send_sales_invoice_to_jofotara(sales_invoice, user=None):
    """Send sales invoice to JoFotara"""
    try:
        invoice_data = prepare_sales_invoice_data(sales_invoice)
        result = send_invoice_to_jofotara(invoice_data, 'sales')

        # Log the result only if user is provided
        if user:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action_type='send_invoice',
                content_type='SalesInvoice',
                object_id=sales_invoice.id,
                description=f'إرسال فاتورة مبيعات {sales_invoice.invoice_number} إلى JoFotara: {"نجح" if result["success"] else "فشل"}'
            )

        return result

    except Exception as e:
        logger.error(f"Error sending sales invoice: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def send_credit_note_to_jofotara(credit_note, user=None):
    """Send credit note to JoFotara"""
    try:
        invoice_data = prepare_credit_note_data(credit_note)
        result = send_invoice_to_jofotara(invoice_data, 'credit_note')

        # Log the result only if user is provided
        if user:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action_type='send_credit_note',
                content_type='SalesCreditNote',
                object_id=credit_note.id,
                description=f'إرسال إشعار خصم {credit_note.note_number} إلى JoFotara: {"نجح" if result["success"] else "فشل"}'
            )

        return result

    except Exception as e:
        logger.error(f"Error sending credit note: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def send_debit_note_to_jofotara(debit_note, user=None):
    """Send debit note to JoFotara"""
    try:
        invoice_data = prepare_debit_note_data(debit_note)
        result = send_invoice_to_jofotara(invoice_data, 'debit_note')

        # Log the result only if user is provided
        if user:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action_type='send_debit_note',
                content_type='PurchaseDebitNote',
                object_id=debit_note.id,
                description=f'إرسال إشعار إضافة {debit_note.note_number} إلى JoFotara: {"نجح" if result["success"] else "فشل"}'
            )

        return result

    except Exception as e:
        logger.error(f"Error sending debit note: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def send_return_to_jofotara(sales_return, user=None):
    """Send sales return to JoFotara"""
    try:
        # Get company settings
        from settings.models import CompanySettings
        company = CompanySettings.objects.first()
        
        # Prepare return data similar to credit note (returns are treated as credit notes)
        invoice_data = {
            'invoice_number': sales_return.return_number,
            'issue_date': sales_return.date.isoformat(),  # Fixed: use 'date' not 'return_date'
            'issue_time': sales_return.created_at.time().isoformat() if hasattr(sales_return, 'created_at') else datetime.now().time().isoformat(),
            'original_invoice_number': sales_return.original_invoice.invoice_number if sales_return.original_invoice else '',  # Fixed: use 'original_invoice'
            'original_invoice_date': sales_return.original_invoice.date.isoformat() if sales_return.original_invoice else '',  # Fixed: use 'date'
            'seller': {
                'name': company.company_name if company else 'Test Company',  # Fixed: use CompanySettings
                'tax_number': company.tax_number if company else '123456789',
            },
            'buyer': {
                'name': sales_return.customer.name,
                'tax_number': getattr(sales_return.customer, 'tax_number', ''),
            },
            'lines': [
                {
                    'product_name': item.product.name,
                    'quantity': float(item.quantity),
                    'unit_price': float(item.unit_price),
                    'tax_percent': float(item.tax_rate) if hasattr(item, 'tax_rate') else 0,
                    'total': float(item.total_amount),  # Fixed: use 'total_amount'
                } for item in sales_return.items.all()
            ],
            'currency': 'JOD',
        }
        
        result = send_invoice_to_jofotara(invoice_data, 'credit_note')

        # Log the result only if user is provided
        if user:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=user,
                action_type='send_return',
                content_type='SalesReturn',
                object_id=sales_return.id,
                description=f'إرسال مرتجع مبيعات {sales_return.return_number} إلى JoFotara: {"نجح" if result["success"] else "فشل"}'
            )

        return result

    except Exception as e:
        logger.error(f"Error sending return: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

