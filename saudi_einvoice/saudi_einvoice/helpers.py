import base64
import hashlib
import json
import xml.etree.ElementTree as ET
import datetime
import uuid
import qrcode
from OpenSSL import crypto
from PIL import Image

# all invoice data to used in the template
# invoice_data = {
#     "id": id,
#     "seller_name": "ABC Company",
#     "seller_vat": "310864207200003",
#     "seller_street": "street",
#     "seller_building": "1",
#     "postal_zone": "11417",
#     "seller_city_name": "city",
#     "seller_country_code": "SA",
#     "invoice_number": "INV-20220001",
#     "invoice_date": date,
#     "invoice_time": time,
#     "invoice_amount": "1000.00",
#     "tax_amount": "150.00",
#     "currency_code": "SAR",
#     "buyer_name": "XYZ Corporation",
#     "buyer_vat": "310864207200003",
#     "buyer_street": "street",
#     "buyer_building": "1",
#     "buyer_city_name": "Riyadh",
#     "buyer_country_code": "SA",
#     "buyer_postal_code": "11417",
#     "line_items": [
#         {"id": "1", "unit_code": "1", "description": "abc", "product": "product1",
#             "quantity": "1", "price": "1000", "total": "1000"}
#     ]
# }


class SaudiEInvoice:
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path

    def get_keys(self):
        with open(self.config_file_path) as f:
            config = json.load(f)
        return config['username'], config['password'], config['private_key_path'], config['url']

    def create_invoice(self, invoice_data):
        private_key_path = self.get_keys()[2]
        with open(private_key_path, "rb") as key_file:
            private_key = key_file.read()

        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)

        path = 'Simplified_Invoice.xml'  # Replace with actual path to invoice template file
        tree = ET.parse(path)
        root = tree.getroot()

        # Add QR code to invoice
        qr_data = f"||1|1|{invoice_data['seller_name']}|{invoice_data['seller_vat']}|{invoice_data['invoice_number']}|{invoice_data['invoice_date']}|{invoice_data['invoice_time']}|{invoice_data['invoice_amount']}|{invoice_data['currency_code']}|{invoice_data['buyer_name']}|{invoice_data['buyer_vat']}"
        qr_code = base64.b64encode(qr_data.encode()).decode()

        # Find the relevant elements to replace
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'ns4': 'namespace4-URI',
            'ns8': 'namespace8-URI'
        }
        seller_name = root.find('.//cbc:RegistrationName', ns)
        seller_vat = root.find('.//cbc:CompanyID', ns)
        seller_street = root.find('.//cbc:StreetName', ns)
        seller_building = root.find('.//cbc:BuildingNumber', ns)
        postal_zone = root.find('.//cbc:PostalZone', ns)
        seller_city_name = root.find('.//cbc:CityName', ns)
        invoice_number = root.find('.//cbc:ID', ns)
        invoice_date = root.find('.//cbc:IssueDate', ns)
        invoice_time = root.find('.//cbc:IssueTime', ns)
        invoice_amount = root.find('.//cbc:PayableAmount', ns)
        currency_code = root.find('.//cbc:DocumentCurrencyCode', ns)
        # buyer_name = root.find('.//cbc:BuyerReference', ns)
        # buyer_vat = root.find('.//cbc:CustomerAssignedAccountID', ns)
        # line_items = root.find('LineItems')
        X509Certificate = root.find('.//cbc:X509Certificate', ns)
        SigningTime = root.find('.//cbc:IssueDate', ns)
        signing_cert = root.find(
            './/ds:DigestValue', {'ds': 'http://www.w3.org/2000/09/xmldsig#'})
        X509SerialNumber = root.find(
            './/ds:X509SerialNumber', {'ds': 'http://www.w3.org/2000/09/xmldsig#'})
        ID = root.find('.//cbc:ID', ns)
        UUID = root.find('.//cbc:UUID', ns)
        QR = root.find('.//cbc:EmbeddedDocumentBinaryObject', ns)
        # Replace the data with your own values

        seller_name.text = invoice_data["seller_name"]
        seller_vat.text = invoice_data["seller_vat"]
        seller_street.text = invoice_data["seller_street"]
        seller_building.text = invoice_data["seller_building"]
        postal_zone.text = invoice_data["postal_zone"]
        seller_city_name.text = invoice_data["seller_city_name"]
        invoice_number.text = invoice_data["invoice_number"]
        invoice_date.text = invoice_data["invoice_date"]
        invoice_time.text = invoice_data["invoice_time"]
        invoice_amount.text = invoice_data["invoice_amount"]
        currency_code.text = invoice_data["currency_code"]
        QR.text = qr_code
        ID.text = invoice_data["id"]
        UUID.text = invoice_data["id"]
        # buyer_name.text = invoice_data["invoice_number"]
        # buyer_vat.text = invoice_data["invoice_number"]
        # Replace the line items
        line_items = root.find('LineItems', ns)
        TaxTotal = root.find('.//cac:TaxTotal', ns)
        TaxAmount1 = TaxTotal.find('.//cbc:TaxAmount', ns)
        TaxSubtotal = ET.Element(TaxTotal).find('.//cbc:TaxSubtotal', ns)
        TaxableAmount = ET.Element(TaxSubtotal).find(
            './/cbc:TaxableAmount', ns)
        TaxAmount = ET.Element(TaxSubtotal).find('.//ns4:TaxAmount', ns)
        if TaxAmount1 is not None:
            TaxAmount1.text = invoice_data["tax_amount"]
        if TaxableAmount is not None:
            TaxableAmount.text = invoice_data["invoice_amount"]
        if TaxAmount is not None:
            TaxAmount.text = invoice_data["tax_amount"]

        # find line items in the tepmlate file and replace it with invoice data
        if line_items is not None:
            for item in invoice_data['line_items']:
                line_item = ET.Element('LineItem')
                item_description = ET.SubElement(line_item, 'ItemDescription')
                item_description.text = item['product']
                quantity = ET.SubElement(line_item, 'Quantity')
                quantity.text = str(item['quantity'])
                unit_price = ET.SubElement(line_item, 'UnitPrice')
                unit_price.text = str(item['price'])
                line_items.append(line_item)
        in_name = str(invoice_data['number'])
        # Calculate the invoice hash and sign it
        invoice_hash = hashlib.sha256(
            ET.tostring(root, encoding='utf-8')).hexdigest()
        with open(in_name+'.txt', 'w') as f:
            f.write(invoice_hash)
        signature = crypto.sign(pkey, invoice_hash, "sha256")

        # Load the certificate, get its hash, and sign the final invoice with ZATCA signature
        with open('certificate.txt', "rb") as cert_file:
            cert = cert_file.read()
            cert_hash = hashlib.sha256(cert_file.read()).hexdigest()
        zatca_signature = crypto.sign(
            pkey, ET.tostring(root, encoding='utf-8'), "sha256")
        zatca_signed_data = ET.tostring(root, encoding='utf-8')
        signed_zatca_invoice_data = zatca_signed_data + zatca_signature
        # Write the signed invoice to a file
        tree.write(in_name+'.xml')

        # Encode the signed ZATCA invoice data in base64
        encoded_zatca_invoice_data = base64.b64encode(
            signed_zatca_invoice_data).decode('utf-8')
        return {'encoded': encoded_zatca_invoice_data, 'hash': invoice_hash}

    def generate_qr_code(self, invoice_data):
        invoice_number = str(invoice_data["invoice_number"])
        invoice_date = invoice_data["invoice_date"]
        invoice_time = invoice_data["invoice_time"]
        invoice_amount = invoice_data["invoice_amount"]
        currency_code = invoice_data["currency_code"]
        seller_name = invoice_data["seller_name"]
        seller_vat = invoice_data["seller_vat"]
        buyer_name = invoice_data["buyer_name"]
        buyer_vat = invoice_data["buyer_vat"]

        # e-invoice QR code data
        qr_data = f"||1|1|{seller_name}|{seller_vat}|{invoice_number}|{invoice_date}|{invoice_time}|{invoice_amount}|{currency_code}|{buyer_name}|{buyer_vat}||"

        # generate QR code
        qr = qrcode.QRCode(
            version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # save QR code image
        img.save("e-invoice-qr.png")

        return qr

    def create_signed_properties(self, pkey):
        # Create signed properties for the invoice signature
        # This method returns a string that should be added to the SignedProperties tag
        signed_properties = "Signed properties data"
        # Modify signed_properties variable to create the actual signed properties
        return signed_properties