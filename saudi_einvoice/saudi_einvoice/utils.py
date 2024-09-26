import io
import json
from pickle import FALSE
import os
import frappe
from frappe import _
from frappe.utils.data import add_to_date, get_time, getdate
from frappe.utils import cstr, flt
from frappe.utils.file_manager import remove_file
import uuid
from xml.etree import ElementTree as ET
import base64
import requests
from OpenSSL import crypto
import datetime
from os import sys
from .templates import SIGNATURE_TEMPLATE, SIGNATURE_TEMPLATE, SELLER_TEMPLATE, CUSTOMER_ID_TEMPLATE, CUSTOMER_INFO_TEMPLATE, INSTRUCTION_NOTES_TEMPLATE, PAYMENT_TEMPLATE, BILLING_REFRENCE_TEMPLATE, INVOICE_LINE_ITEM_TEMPLATE, NO_TAX_TEMPLATE, TAX_SUBTOTAL_TEMPLATE, PIH_TEMPLATE, MAIN_TEMPLATE, UBL_TEMPLATE, QR_TEMPLATE
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
import hashlib
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives.asymmetric import ec
import segno
from erpnext.controllers.taxes_and_totals import get_itemised_tax
from cryptography.hazmat.primitives.asymmetric import rsa

xml_version = '''<?xml version="1.0" encoding="UTF-8"?>
'''

def update_itemised_tax_data(doc,method):
    if not doc.taxes:
        return

    if doc.doctype == "Purchase Invoice":
        return

    itemised_tax = get_itemised_tax(doc.taxes)

    for row in doc.items:
        tax_rate = 0.0
        if itemised_tax.get(row.item_code):
            tax_rate = sum([tax.get("tax_rate", 0)
                           for d, tax in itemised_tax.get(row.item_code).items()])
        tax= row.item_tax_template
        x=frappe.get_doc("Item Tax Template",tax)
        y= x.as_dict()
        row.tax=y['taxes'][0].tax_rate
        row.tax_rate = flt(tax_rate)
        row.tax_amount = flt((row.net_amount * tax_rate) /
                             100, row.net_amount)
        
        row.total_amount = flt(
            (row.net_amount + row.tax_amount))


@frappe.whitelist()
def export_invoices(filters=None):
    frappe.has_permission("Sales Invoice", throw=True)

    invoices = frappe.get_all(
        "Sales Invoice", filters=get_conditions(filters), fields=["name", "company_tax_id"]
    )

    # attachments = get_e_invoice_attachments(invoices)

    zip_filename = "{0}-einvoices.zip".format(
        frappe.utils.get_datetime().strftime("%Y%m%d_%H%M%S"))

    # download_zip(attachments, zip_filename)


def prepare_invoice(invoice, progressive_number):
    # set company information
    company = frappe.get_doc("Company", invoice.company)
    # load_tax_itemised = update_itemised_tax_data()
    invoice.progressive_number = progressive_number
    invoice.unamended_name = get_unamended_name(invoice)
    invoice.company_data = company
    company_address = frappe.get_doc("Address", invoice.company_address)
    invoice.company_address_data = company_address

    invoice.customer_data = frappe.get_doc("Customer", invoice.customer)
    customer_address = frappe.get_doc("Address", invoice.customer_address)
    
    invoice.customer_address_data = customer_address

    
    if invoice.shipping_address_name:
        invoice.shipping_address_data = frappe.get_doc(
            "Address", invoice.shipping_address_name)

    # if invoice.customer_data.is_public_administration:
    #     invoice.transmission_format_code = "FPA12"
    # else:
    #     invoice.transmission_format_code = "FPR12"

    invoice.e_invoice_items = [item for item in invoice.items]
    tax_data = get_invoice_summary(invoice.e_invoice_items, invoice.taxes)
    invoice.tax_data = tax_data

    # Check if stamp duty (Bollo) of 2 EUR exists.
    stamp_duty_charge_row = next(
        (tax for tax in invoice.taxes if tax.charge_type ==
         "Actual" and tax.tax_amount == 2), None
    )
    if stamp_duty_charge_row:
        invoice.stamp_duty = stamp_duty_charge_row.tax_amount
    customer_po_data = {}
    
    if invoice.po_no and invoice.po_date and invoice.po_no not in customer_po_data:
        customer_po_data[invoice.po_no] = invoice.po_date

    invoice.customer_po_data = customer_po_data
    seller_name = frappe.db.get_value("Company", invoice.company, "name")
    tax_id = frappe.db.get_value("Company", invoice.company, "tax_id")
    posting_date = getdate(invoice.posting_date)
    time = get_time(invoice.posting_time)
    seconds = time.hour * 60 * 60 + time.minute * 60 + time.second
    time_stamp = add_to_date(posting_date, seconds=seconds)
    time_stamp = time_stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    invoice_amount = invoice.grand_total
    vat_amount = get_vat_amount(invoice)

    items = []
    for item in invoice.e_invoice_items:
      item_tax = frappe.get_doc("Item Tax Template", item.item_tax_template)
      main_tax = item_tax.taxes[0]
      tax_rate = main_tax.tax_rate
      net = item.qty * item.rate
      vat = net * tax_rate / 100
      total_price = net + vat
      items.append({
        "item_id": item.name[:6],
        "category_id": "S",
        "item_name": str(item.item_code),
        "item_qty": str(item.qty),
        "vat": "%1.2f"%vat,
        "qty_price": "%1.2f"%item.rate,
        "vat_percent": "%1.2f"%tax_rate,
        "total_price": "%1.2f"%total_price,
        "item_net_price": "%1.2f"%item.rate,
        "discount": "0.00",
        "item_price": "%1.2f"%item.rate
      })
    invoice.uuid = str(uuid.uuid4())
    in_count = frappe.db.count('Sales Invoice', {
      'custom_hash': ["is", "set"]
    })
    last_hashed = "Bu9BxfjjJ6cQYcyP+5Nrm6y3DJZp/mQlTOY0zM34c1U="
    if in_count > 0:
      last_hashed_doc = frappe.get_last_doc('Sales Invoice', filters={'custom_hash': ["is", "set"]}, order_by="posting_date asc")
      if last_hashed_doc:
        last_hashed = last_hashed_doc.custom_hash
    vat_amount = invoice.total_taxes_and_charges
    tot = invoice_amount - vat_amount
    simple_invoice_data = {
      "company_id": tax_id,
      "uuid": str(invoice.uuid),
      "invoice_id": "2M",    
      "company_name": seller_name,
      "postal_code": company_address.pincode or "12345",
      "city_name": company_address.city or "Riyadh",
      "pih": last_hashed,
      "district": company_address.custom_district,
      "building_number": company_address.custom_building_no,
      "street_name": company_address.custom_street,
      "customer_name": invoice.customer_data.name,
      "customer_vat": invoice.customer_data.tax_id,
      "issue_date": str(posting_date),
      'invoice_counter': in_count,
      "issue_time": time.strftime('%H:%M:%S'),
      "doc_discount": "0.00",
      "pre_payed": "0.00",
      "total_without_tax": tot,
      "total_without_tax_after_doc_discount": tot,
      "total_with_tax": "%1.2f"%invoice_amount,
      "pre_pay": "0.00",
      "payed": "%1.2f"%invoice_amount,
      "total_tax": "%1.2f"%vat_amount,
      "subtotal": {
          "taxable_amount": "%1.2f"%tot,
          "tax_amount": "%1.2f"%vat_amount,
          "category_id": "S",
          "tax_percent": "%1.2f"%(vat_amount/tot*100),
      },
      "_invoice_type_id": 1,
      "_isCitizen": 0,
      "customer": {
          "id": invoice.customer_data.tax_id,
          "street_name": customer_address.custom_street,
          "building_number": customer_address.custom_building_no or "",
          "district": customer_address.custom_district or "",
          "city_name": customer_address.city,
          "postal_code": customer_address.pincode or "67890",
          "customer_name": invoice.customer_data.name,
      },
      "items": items,
      "customer_id": "",
      "payment": {
          "payment_type": "10",
      }
      
    }
    t = "simple"
    if invoice.customer_data.tax_id and invoice.customer_data.tax_id[0] == "1":
      t = "standard"
    key_path = os.path.abspath(os.path.join('../apps','saudi_einvoice', 'saudi_einvoice', 'saudi_einvoice', 'keys', company.custom_k_file))
    private_key_path = key_path
    with open(private_key_path, "rb") as key_file:
        setting_data = json.load(key_file)
    out = building_invoice(simple_invoice_data, setting_data, t)
    print(simple_invoice_data)
    invoice.db_set('custom_uuid', invoice.uuid)
    out_path = os.path.join('assets', 'custom_app', 'images', 'qrcode', str(invoice.uuid)+'.png')
    qr_code = segno.make(out['qr'])
    qr_code.save(out_path)
    invoice.db_set('custom_qr_code_invoice', '/'+out_path)
    #raise Exception('error in data')
    res = send(out['xml'].encode('utf-8'), out['hash'].encode('utf-8'), out['uuid'], setting_data)
    if not res:
        raise Exception('error in data receipt not reported')
    invoice.db_set('custom_receipt_status', 'sent')
    invoice.db_set('custom_hash', out['hash'], commit=True)
    # invoice.db_set('custom_submission_reason', res, commit=True)
    return invoice


def get_conditions(filters):
    filters = json.loads(filters)

    conditions = {"docstatus": 1, "company_tax_id": ("!=", "")}

    if filters.get("company"):
        conditions["company"] = filters["company"]
    if filters.get("customer"):
        conditions["customer"] = filters["customer"]

    if filters.get("from_date"):
        conditions["posting_date"] = (">=", filters["from_date"])
    if filters.get("to_date"):
        conditions["posting_date"] = ("<=", filters["to_date"])

    if filters.get("from_date") and filters.get("to_date"):
        conditions["posting_date"] = (
            "between", [filters.get("from_date"), filters.get("to_date")])

    return conditions


def download_zip(files, output_filename):
    import zipfile

    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            file_path = frappe.utils.get_files_path(
                file.file_name, is_private=file.is_private)

            zip_file.write(file_path, arcname=file.file_name)

    frappe.local.response.filename = output_filename
    frappe.local.response.filecontent = zip_stream.getvalue()
    frappe.local.response.type = "download"
    zip_stream.close()


def get_invoice_summary(items, taxes):
    summary_data = frappe._dict()
    for tax in taxes:
        # Include only VAT charges.
        if tax.charge_type == "Actual":
            continue

        # Charges to appear as items in the e-invoice.
        if tax.charge_type in ["On Previous Row Total", "On Previous Row Amount"]:
            reference_row = next(
                (row for row in taxes if row.idx == int(tax.row_id or 0)), None)
            if reference_row:
                items.append(
                    frappe._dict(
                        idx=len(items) + 1,
                        item_code=reference_row.description,
                        item_name=reference_row.description,
                        description=reference_row.description,
                        rate=reference_row.tax_amount,
                        qty=1.0,
                        amount=reference_row.tax_amount,
                        stock_uom=frappe.db.get_single_value(
                            "Stock Settings", "stock_uom") or _("Nos"),
                        tax_rate=tax.rate,
                        tax_amount=(reference_row.tax_amount * tax.rate) / 100,
                        net_amount=reference_row.tax_amount,
                        taxable_amount=reference_row.tax_amount,
                        item_tax_rate={tax.account_head: tax.rate},
                        charges=True,
                    )
                )

        # Check item tax rates if tax rate is zero.
        if tax.rate == 0:
            for item in items:
                item_tax_rate = item.item_tax_rate
                if isinstance(item.item_tax_rate, str):
                    item_tax_rate = json.loads(item.item_tax_rate)

                if item_tax_rate and tax.account_head in item_tax_rate:
                    key = cstr(item_tax_rate[tax.account_head])
                    if key not in summary_data:
                        summary_data.setdefault(
                            key,
                            {
                                "tax_amount": 0.0,
                                "taxable_amount": 0.0,
                                "tax_exemption_reason": "",
                                "tax_exemption_law": "",
                            },
                        )

                    summary_data[key]["tax_amount"] += tax.tax_amount
                    summary_data[key]["taxable_amount"] += item.net_amount
                    if key == "0.0":
                        summary_data[key]["tax_exemption_reason"] = tax.tax_exemption_reason
                        summary_data[key]["tax_exemption_law"] = tax.tax_exemption_law

            if summary_data.get("0.0") and tax.charge_type in [
                    "On Previous Row Total",
                    "On Previous Row Amount",
            ]:
                summary_data[key]["taxable_amount"] = tax.total

            if summary_data == {}:  # Implies that Zero VAT has not been set on any item.
                summary_data.setdefault(
                    "0.0",
                    {
                        "tax_amount": 0.0,
                        "taxable_amount": tax.total,
                        "tax_exemption_reason": tax.tax_exemption_reason,
                        "tax_exemption_law": tax.tax_exemption_law,
                    },
                )

        else:
            item_wise_tax_detail = json.loads(tax.item_wise_tax_detail)
            for rate_item in [
                    tax_item for tax_item in item_wise_tax_detail.items() if tax_item[1][0] == tax.rate
            ]:
                key = cstr(tax.rate)
                if not summary_data.get(key):
                    summary_data.setdefault(
                        key, {"tax_amount": 0.0, "taxable_amount": 0.0})
                summary_data[key]["tax_amount"] += rate_item[1][1]
                summary_data[key]["taxable_amount"] += sum(
                    [item.net_amount for item in items if item.item_code == rate_item[0]]
                )

            for item in items:
                key = cstr(tax.rate)
                if item.get("charges"):
                    if not summary_data.get(key):
                        summary_data.setdefault(key, {"taxable_amount": 0.0})
                    summary_data[key]["taxable_amount"] += item.taxable_amount

    return summary_data


# Preflight for successful e-invoice export.
def sales_invoice_validate(doc):
    # Validate company
    if doc.doctype != "Sales Invoice":
        return

    if not doc.company_address:
        frappe.throw(
            _("Please set an Address on the Company '%s'" % doc.company),
            title=_("E-Invoicing Information Missing"),
        )
    else:
        validate_address(doc.company_address)

    company_fiscal_regime = frappe.get_cached_value(
        "Company", doc.company, "fiscal_regime")
    if not company_fiscal_regime:
        frappe.throw(
            _("Fiscal Regime is mandatory, kindly set the fiscal regime in the company {0}").format(
                doc.company
            )
        )
    else:
        doc.company_fiscal_regime = company_fiscal_regime

    doc.company_tax_id = frappe.get_cached_value(
        "Company", doc.company, "tax_id")
    doc.company_fiscal_code = frappe.get_cached_value(
        "Company", doc.company, "fiscal_code")
    if not doc.company_tax_id and not doc.company_fiscal_code:
        frappe.throw(
            _("Please set either the Tax ID or Fiscal Code on Company '%s'" %
              doc.company),
            title=_("E-Invoicing Information Missing"),
        )

    # Validate customer details
    customer = frappe.get_doc("Customer", doc.customer)

    if customer.customer_type == "Individual":
        doc.customer_fiscal_code = customer.fiscal_code
        if not doc.customer_fiscal_code:
            frappe.throw(
                _("Please set Fiscal Code for the customer '%s'" % doc.customer),
                title=_("E-Invoicing Information Missing"),
            )
    else:
        if customer.is_public_administration:
            doc.customer_fiscal_code = customer.fiscal_code
            if not doc.customer_fiscal_code:
                frappe.throw(
                    _("Please set Fiscal Code for the public administration '%s'" %
                      doc.customer),
                    title=_("E-Invoicing Information Missing"),
                )
        else:
            doc.tax_id = customer.tax_id
            if not doc.tax_id:
                frappe.throw(
                    _("Please set Tax ID for the customer '%s'" % doc.customer),
                    title=_("E-Invoicing Information Missing"),
                )

    if not doc.customer_address:
        frappe.throw(_("Please set the Customer Address"),
                     title=_("E-Invoicing Information Missing"))
    else:
        validate_address(doc.customer_address)

    if not len(doc.taxes):
        frappe.throw(
            _("Please set at least one row in the Taxes and Charges Table"),
            title=_("E-Invoicing Information Missing"),
        )
    else:
        for row in doc.taxes:
            if row.rate == 0 and row.tax_amount == 0 and not row.tax_exemption_reason:
                frappe.throw(
                    _("Row {0}: Please set at Tax Exemption Reason in Sales Taxes and Charges").format(
                        row.idx),
                    title=_("E-Invoicing Information Missing"),
                )

    for schedule in doc.payment_schedule:
        if schedule.mode_of_payment and not schedule.mode_of_payment_code:
            schedule.mode_of_payment_code = frappe.get_cached_value(
                "Mode of Payment", schedule.mode_of_payment, "mode_of_payment_code"
            )


# Ensure payment details are valid for e-invoice.
def sales_invoice_on_submit(doc, method):
    # Validate payment details
    if get_company_country(doc.company) not in [
            "Saudi Arabia"

    ]:
        return

    if not len(doc.payment_schedule):
        frappe.throw(_("Please set the Payment Schedule"),
                     title=_("E-Invoicing Information Missing"))
    else:
        for schedule in doc.payment_schedule:
            if not schedule.mode_of_payment:
                frappe.throw(
                    _("Row {0}: Please set the Mode of Payment in Payment Schedule").format(
                        schedule.idx),
                    title=_("E-Invoicing Information Missing"),
                )
            elif not frappe.db.get_value(
                    "Mode of Payment", schedule.mode_of_payment, "mode_of_payment_code"
            ):
                frappe.throw(
                    _("Row {0}: Please set the correct code on Mode of Payment {1}").format(
                        schedule.idx, schedule.mode_of_payment
                    ),
                    title=_("E-Invoicing Information Missing"),
                )

    prepare_send_attach_invoice(doc)


def prepare_send_attach_invoice(doc, replace=False):
    progressive_name, progressive_number = get_progressive_name_and_number(
        doc, replace)


    invoice = prepare_invoice(doc, progressive_number)
  
    return invoice


@frappe.whitelist()
def generate_single_invoice(docname):
    doc = frappe.get_doc("Sales Invoice", docname)
    frappe.has_permission("Sales Invoice", doc=doc, throw=True)

    e_invoice = prepare_send_attach_invoice(doc, True)
    return e_invoice.file_url


# Delete e-invoice attachment on cancel.
def sales_invoice_on_cancel(doc, method):
    if get_company_country(doc.company) not in [
            "Saudi Arabia"
    ]:
        return

    for attachment in get_e_invoice_attachments(doc):
    	remove_file(attachment.name, attached_to_doctype=doc.doctype, attached_to_name=doc.name)


def get_company_country(company):
    return frappe.get_cached_value("Company", company, "country")


def get_e_invoice_attachments(invoices):
	if not isinstance(invoices, list):
		if not invoices.company_tax_id:
			return

		invoices = [invoices]

	tax_id_map = {
		invoice.name: (
			invoice.company_tax_id
			if invoice.company_tax_id.startswith("SA")
			else "SA" + invoice.company_tax_id
		)
		for invoice in invoices
	}

	attachments = frappe.get_all(
		"File",
		fields=("name", "file_name", "attached_to_name", "is_private"),
		filters={"attached_to_name": ("in", tax_id_map), "attached_to_doctype": "Sales Invoice"},
	)

	out = []
	for attachment in attachments:
		if (
			attachment.file_name
			and attachment.file_name.endswith(".xml")
			and attachment.file_name.startswith(tax_id_map.get(attachment.attached_to_name))
		):
			out.append(attachment)

	return out


def validate_address(address_name):
    fields = ["pincode", "city", "country_code"]
    data = frappe.get_cached_value(
        "Address", address_name, fields, as_dict=1) or {}

    for field in fields:
        if not data.get(field):
            frappe.throw(
                _("Please set {0} for address {1}").format(
                    field.replace("-", ""), address_name),
                title=_("E-Invoicing Information Missing"),
            )


def get_unamended_name(doc):
    attributes = ["naming_series", "amended_from"]
    for attribute in attributes:
        if not hasattr(doc, attribute):
            return doc.name

    if doc.amended_from:
        return "-".join(doc.name.split("-")[:-1])
    else:
        return doc.name


def get_progressive_name_and_number(doc, replace=False):
	if replace:
		for attachment in get_e_invoice_attachments(doc):
			remove_file(attachment.name, attached_to_doctype=doc.doctype, attached_to_name=doc.name)
			filename = attachment.file_name.split(".xml")[0]
			return filename, filename.split("_")[1]

	company_tax_id = (
		doc.company_tax_id if doc.company_tax_id.startswith("SA") else "SA" + doc.company_tax_id
	)
	progressive_name = frappe.model.naming.make_autoname(company_tax_id + "_.#####")
	progressive_number = progressive_name.split("_")[1]

	return progressive_name, progressive_number



def log_data(data):
    logger = frappe.logger("file-log", allow_site=True, file_count=50)
    logger.info(data)


# @frappe.whitelist(allow_guest=True)
# def read_file(doc ,method =None):
#     file_path = '/files/QRCode-00210.png'
#     with open(file=file_path) as image_file:
#         pass
 





@frappe.whitelist(allow_guest=True)
def generate_sign(doc ,method):
    BINARY_SECURITY_TOKEN_FILE = 'binarySecurityToken.txt'
    SECRET_FILE = 'secret.txt'
    in_name = str(doc.id)
    INVOICE_HASH_FILE = in_name+'.txt'
    INVOICE_FILE = in_name+'.xml'
    INVOICE_REPORTING_URL = 'https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/invoices/reporting/single'

    # Load files
    with open(BINARY_SECURITY_TOKEN_FILE, "rb") as file:
        binarySecurityToken = file.read().strip()

    with open(SECRET_FILE, "rb") as file:
        secret = file.read().strip()

    with open(INVOICE_HASH_FILE, "rb") as file:
        invoicehash = file.read().decode('utf-8').strip()

    with open(INVOICE_FILE, "rb") as file:
        invoice = base64.b64encode(file.read()).decode('utf-8').strip()

    # Prepare request
    auth_str = f'{binarySecurityToken}:{secret}'
    auth2 = base64.b64encode(auth_str.encode('utf-8'))
    # print(auth2)

    headers = {
        'accept': 'application/json',
        'accept-language': 'en',
        'Clearance-Status': '0',
        'Accept-Version': 'V2',
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth2}',
    }

    json_data = {
        'invoiceHash': invoicehash,
        'uuid': str(uuid.uuid4()),
        'invoice': invoice,
    }

    # Send request
    try:
        response = requests.post(
            INVOICE_REPORTING_URL,
            headers=headers,
            json=json_data,
        )
        response.raise_for_status()
        print(response.json())
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f'Error 401: Invalid credentials')
        else:
            print(f'Error {e.response.status_code}: {e.response.text}')
    except requests.exceptions.RequestException as e:
        print(f'Error: {e}')
    
    return signed_file




def get_vat_amount(doc):
	vat_settings = frappe.db.get_value("KSA VAT Setting", {"company": doc.company})
	vat_accounts = []
	vat_amount = 0

	if vat_settings:
		vat_settings_doc = frappe.get_cached_doc("KSA VAT Setting", vat_settings)

		for row in vat_settings_doc.get("ksa_vat_sales_accounts"):
			vat_accounts.append(row.account)

	for tax in doc.get("taxes"):
		if tax.account_head in vat_accounts:
			vat_amount += tax.tax_amount

	return vat_amount





# @frappe.whitelist(allow_guest=True)
# def generate_pkey():
#     # provide the location to store private key
#     cwd = os.getcwd()   
#     pkey = cwd+'/mum128.erpgulf.com'+"/public/files/testpkeyyo.pem"
    
#     key = OpenSSL.crypto.PKey()
#     key.generate_key( OpenSSL.crypto.TYPE_RSA, 1024 )
    
#     open( pkey, 'wb' ).write( 
#     OpenSSL.crypto.dump_privatekey( OpenSSL.crypto.FILETYPE_PEM, key ) )

    
    
  #   attachments = frappe.get_all(
	# 	"File",
	# 	fields=("name", "file_name", "attached_to_name","file_url"),
	# 	filters={"attached_to_name": ("in", doc.name), "attached_to_doctype": "Sales Invoice"},
	# )
    
  #   for attachment in attachments:
  #       if (
	# 		attachment.file_name.startswith("Signed")
	# 		and attachment.file_name.endswith(".xml")
			
	# 	):
  #           xml_filename = attachment.file_name
  #           file_url = attachment.file_url
          
    
    
  #   # xml_file = cwd+'/mum128.erpgulf.com/public'+file_url
  #   xml_file=cwd+'/'+site+'/public'+file_url
   
    
  #   log_data(f'Attchment data : {attachments}')
    
    
  #   with open(xml_file, 'r') as file:
  #       data1 = file.read()
  #       arr1 = bytes(data1, "utf-8")
  #       base64_encoded_data1 = base64.b64encode(arr1)
  #       base64_message1 = base64_encoded_data1.decode('utf-8')
  #       data = base64_message1.replace("\n","")
  
  #       data = base64_message1.replace("\r","")
  #   with open(r'base64xml.txt', 'w') as file:
  
  #       # Writing the replaced data in our
  #       # text file
  #       file.write(data)
  #       print(type(data))
  #   hash_doc = frappe.get_doc('Hash')
  #   hash_val = hash_doc.pih
  #   body ={
  #       "invoiceHash": hash_val,
  #       "uuid": str(uuid.uuid4()),
  #       "invoice": data}

  #   url3 ='https://gw-fatoora.zatca.gov.sa/e-invoicing/developer-portal/invoices/reporting/single'
  #   # https://gw-apic-gov.gazt.gov.sa/e-invoicing/core/reporting/single

  #   x = requests.post(url3, json = body, headers = headerr2)
  #   response2= x.text
  #   with open(r'responseapi.txt', 'w') as file:
  
  #       # Writing the replaced data in our
  #       # text file
  #       file.write(response2)
  #   Path(cwd).chdir()
  #   # frappe.msgprint("<pre>{}</pre>".format(frappe.as_json(response2)))
  #   frappe.msgprint("Response: {}".format(response2))
  #   return response2 

    

def generateCertificateHash(main_cert):
    hash_2 = hashlib.sha256(main_cert).hexdigest()
    return base64.b64encode(hash_2.encode('utf8')).decode('utf-8')

def generaetHash2(time, cert, main_cert, bs64cert):
    signature = {
        "xades": '''xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" ''',
        "digestMethod": ''' xmlns:ds="http://www.w3.org/2000/09/xmldsig#"''',
        "time": time,
        "cert_serial_no": str(cert.serial_number),
        "issuer_name": cert.issuer.rfc4514_string().replace(',', ', '),
        "cert_hash": bs64cert,
        "certificate": main_cert
    }
    #print(signature)
    hash_2_main = SIGNATURE_TEMPLATE % signature
    # digest = hashes.Hash(hashes.SHA256())
    # digest.update(hash_2_main.encode('utf-8'))
    hash_2 = hashlib.sha256(hash_2_main.encode('utf-8')).hexdigest()
    # print(hash_2, hash_2_main)
    return base64.b64encode(hash_2.encode('utf8'))
    # result = digest.finalize()
    # hexResult = ""
    # for x in result:
    #     hexResult += "{:02x}".format(x)
    # print(hexResult)
    # return base64.b64encode(hexResult.encode('utf8'))


def generateSinatureProps(time, cert, main_cert, bs64cert):
    signature = {
        "xades": '',
        "digestMethod": '',
        "time": time,
        "cert_serial_no": str(cert.serial_number),
        "issuer_name": cert.issuer.rfc4514_string().replace(',', ', '),
        "cert_hash": bs64cert,
        "certificate": main_cert
    }
    hash_2_main = SIGNATURE_TEMPLATE % signature
    return hash_2_main
    # result = digest.finalize()
    # hexResult = ""
    # for x in result:
    #     hexResult += "{:02x}".format(x)
    # print(hexResult)
    # return base64.b64encode(hexResult.encode('utf8'))

def qrcodeGenerator(companyID, companyName, registrationDate, payedAmount, vatValue, hash, signature, publicKey='', certSignature=''):
    out = b''
    out = out+ b''.join([(1).to_bytes(1, 'big'), len(companyName).to_bytes(1, 'big'), companyName.encode('utf-8')])
    out = out+ b''.join([(2).to_bytes(1, 'big'), len(companyID).to_bytes(1, 'big'), companyID.encode('utf-8')])
    out = out+ b''.join([(3).to_bytes(1, 'big'), len(registrationDate).to_bytes(1, 'big'), registrationDate.encode('utf-8')])
    out = out+ b''.join([(4).to_bytes(1, 'big'), len(payedAmount).to_bytes(1, 'big'), payedAmount.encode('utf-8')])
    out = out+ b''.join([(5).to_bytes(1, 'big'), len(vatValue).to_bytes(1, 'big'), vatValue.encode('utf-8')])
    out = out+ b''.join([(6).to_bytes(1, 'big'), len(hash).to_bytes(1, 'big'), hash.encode('utf-8')])
    out = out+ b''.join([(7).to_bytes(1, 'big'), len(signature).to_bytes(1, 'big'), signature.encode('utf-8')])
    #struct.pack(">BBBB", 1, 2, 3, 4)
    if len(publicKey):
        out = out+ b''.join([(8).to_bytes(1, 'big'), len(publicKey).to_bytes(1, 'big'), publicKey])
    if len(certSignature):
      out = out+ b''.join([(9).to_bytes(1, 'big'), len(certSignature).to_bytes(1, 'big'), certSignature])
    qr_code = base64.b64encode(out).decode('utf-8')
    return qr_code

invices_types = {
    'simple': '''<cbc:InvoiceTypeCode name="0200000">388</cbc:InvoiceTypeCode>''',
    'standard': '''<cbc:InvoiceTypeCode name="0100000">388</cbc:InvoiceTypeCode>''',
    'simple_credit_note': '''<cbc:InvoiceTypeCode name="0200000">381</cbc:InvoiceTypeCode>''',
    'simple_debit_note': '''<cbc:InvoiceTypeCode name="0200000">383</cbc:InvoiceTypeCode>''',
    'standard_credit_note': '''<cbc:InvoiceTypeCode name="0100000">381</cbc:InvoiceTypeCode>''',
    'standard_debit_note': '''<cbc:InvoiceTypeCode name="0100000">383</cbc:InvoiceTypeCode>''',
}
def building_invoice(invoice, setting, type='simple'):
    new_invoice = invoice.copy()
    new_invoice['seller_info'] = SELLER_TEMPLATE % invoice
    customer = invoice['customer'].copy()
    customer['customer_id'] = ''
    if customer['id'] and not customer['id'].startswith("1"):
        customer['customer_id'] = CUSTOMER_ID_TEMPLATE % customer
    new_invoice['customer_info'] = CUSTOMER_INFO_TEMPLATE % customer
    payment = invoice['payment'].copy()
    if payment.get('notes'):
        payment['notes'] = INSTRUCTION_NOTES_TEMPLATE % payment
    else:
        payment['notes'] = ''
    new_invoice['invoice_type'] = invices_types.get(type)
    new_invoice['payment_mean'] = PAYMENT_TEMPLATE % payment
    new_invoice['ubl_extensions'] = ''
    if new_invoice.get('billing_reference', False):
        new_invoice['billing_reference'] = BILLING_REFRENCE_TEMPLATE % new_invoice['billing_reference']
    else:
        new_invoice['billing_reference'] = ''
    new_invoice['qr'] = ''
    new_invoice['signature'] = ''
    new_invoice['delivary'] = ''
    items_details = ''
    for item in invoice['items']:
        items_details += INVOICE_LINE_ITEM_TEMPLATE % item
    new_invoice['invoice_lines'] = items_details
    subtotal = new_invoice['subtotal'].copy()
    subtotal['no_tax_reason'] = ''
    if new_invoice['total_tax']==0 or new_invoice['total_tax']=='0.00':
        subtotal['no_tax_reason'] = NO_TAX_TEMPLATE % new_invoice['no_tax']
    new_invoice['tax_details'] = TAX_SUBTOTAL_TEMPLATE % subtotal
    new_invoice['PIH'] = PIH_TEMPLATE % {'PIH': new_invoice['pih']}
    new_invoice['xml_version'] = ''
    root_invoice = MAIN_TEMPLATE % new_invoice
    private_key_data = setting['private_key'].encode('utf-8')
    cert_file = setting['certificate'].encode('utf-8')
    # cert_file = b'MIIE2TCCBH6gAwIBAgITGQAADp060yVMqeGCOwAAAAAOnTAKBggqhkjOPQQDAjBiMRUwEwYKCZImiZPyLGQBGRYFbG9jYWwxEzARBgoJkiaJk/IsZAEZFgNnb3YxFzAVBgoJkiaJk/IsZAEZFgdleHRnYXp0MRswGQYDVQQDExJQRVpFSU5WT0lDRVNDQTMtQ0EwHhcNMjMwNzE3MDg0NzU1WhcNMjMwODA4MTIyNzAxWjBHMQswCQYDVQQGEwJTQTEPMA0GA1UEChMGbWVzd2FrMRMwEQYDVQQLEwozMTA3NTYxNzgzMRIwEAYDVQQDEwltZXN3YWstQjEwVjAQBgcqhkjOPQIBBgUrgQQACgNCAASFBTAWG9N1WrJ0KBj5XWbddG2YycnjzdmeSDFj+R0nWpKhqIHlK5UNDXXQvcHVJ8TYt+WOQcpS34zzjah1Ps4Bo4IDLzCCAyswJwYJKwYBBAGCNxUKBBowGDAKBggrBgEFBQcDAjAKBggrBgEFBQcDAzA8BgkrBgEEAYI3FQcELzAtBiUrBgEEAYI3FQiBhqgdhND7EobtnSSHzvsZ08BVZoGc2C2D5cVdAgFkAgETMIHNBggrBgEFBQcBAQSBwDCBvTCBugYIKwYBBQUHMAKGga1sZGFwOi8vL0NOPVBFWkVJTlZPSUNFU0NBMy1DQSxDTj1BSUEsQ049UHVibGljJTIwS2V5JTIwU2VydmljZXMsQ049U2VydmljZXMsQ049Q29uZmlndXJhdGlvbixEQz1leHRnYXp0LERDPWdvdixEQz1sb2NhbD9jQUNlcnRpZmljYXRlP2Jhc2U/b2JqZWN0Q2xhc3M9Y2VydGlmaWNhdGlvbkF1dGhvcml0eTAdBgNVHQ4EFgQUuWSd0qIJgL5hu/jDsiXJnwP5KtowDgYDVR0PAQH/BAQDAgeAMIGeBgNVHREEgZYwgZOkgZAwgY0xMzAxBgNVBAQMKjEtbWVzd2FrfDItbWVzd2FrfDMtMTExOC05YjU4LWQ5YThmMTFlNDQ1ZjEfMB0GCgmSJomT8ixkAQEMDzMxMDQ2OTg5MjExMDAwMzENMAsGA1UEDAwEMTEwMDEUMBIGA1UEGgwLUnlpYWQgT2xheWExEDAOBgNVBA8MB01lZGljYWwwgeEGA1UdHwSB2TCB1jCB06CB0KCBzYaBymxkYXA6Ly8vQ049UEVaRUlOVk9JQ0VTQ0EzLUNBLENOPVBFWkVpbnZvaWNlc2NhMyxDTj1DRFAsQ049UHVibGljJTIwS2V5JTIwU2VydmljZXMsQ049U2VydmljZXMsQ049Q29uZmlndXJhdGlvbixEQz1leHRnYXp0LERDPWdvdixEQz1sb2NhbD9jZXJ0aWZpY2F0ZVJldm9jYXRpb25MaXN0P2Jhc2U/b2JqZWN0Q2xhc3M9Y1JMRGlzdHJpYnV0aW9uUG9pbnQwHwYDVR0jBBgwFoAUBPcGVSzJVo6t7h63943uhUOTOtswHQYDVR0lBBYwFAYIKwYBBQUHAwIGCCsGAQUFBwMDMAoGCCqGSM49BAMCA0kAMEYCIQD7e8ZUarblSYLo9yP3IFVB0nViLB/Kk0s3obbs98rOMgIhANLAL91WhUZpoIJVwfWSP+Mf+kxVxFDvmlGvdZzSgL82'
    # cert_file = cert_file.encode('utf-8')
    invoice_hash = hashlib.sha256(root_invoice.encode('utf-8')).digest()
    b64_hash = base64.b64encode(invoice_hash).decode('utf-8')
    new_invoice['xml_version'] = xml_version
    # signed = b64encode(signed)
    cert_data = base64.b64decode(cert_file)
    cert = load_der_x509_certificate(cert_data, default_backend)
    time = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    
    hash_certificate = generateCertificateHash(cert_file)
    hash2 = generaetHash2(time, cert, cert_file.decode('utf-8'), hash_certificate)
    
    
    private_key = load_pem_private_key(private_key_data, None)
    signed = private_key.sign(invoice_hash, ec.ECDSA(hashes.SHA256()))
    doc_signature = base64.b64encode(signed).decode('utf-8')
    ubl_data = {
        "signature_properties": generateSinatureProps(time, cert, cert_file.decode('utf-8'), hash_certificate),
        "hash1": b64_hash,
        "hash2": hash2.decode('utf-8'),
        "signature": doc_signature,
        "certificate": cert_file.decode('utf-8'),
    }
    new_invoice['ubl_extensions'] = UBL_TEMPLATE % ubl_data
    byte_cert = cert.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    qr = qrcodeGenerator(new_invoice['company_id'], new_invoice['company_name'], new_invoice['issue_date']+'T'+new_invoice['issue_time']+'Z', 
                         new_invoice['payed'], new_invoice['total_tax'], b64_hash, doc_signature, byte_cert, cert.signature)
    new_invoice['qr'] = QR_TEMPLATE % {'qr': qr}
    new_invoice['signature'] = '''<cac:Signature>
      <cbc:ID>urn:oasis:names:specification:ubl:signature:Invoice</cbc:ID>
      <cbc:SignatureMethod>urn:oasis:names:specification:ubl:dsig:enveloped:xades</cbc:SignatureMethod>
    </cac:Signature>'''
    final_template = MAIN_TEMPLATE % new_invoice
    return {'xml': final_template, 'hash': b64_hash, 'uuid': new_invoice['uuid'], 'qr': qr}
    # print(b64_hash)

def send(xml, invoice_hash, id, setting={}, Compliance=False):
    binarySecurityToken = setting['username']
    secret = setting['secret']
    INVOICE_REPORTING_URL = INVOICE_REPORTING_URL = 'https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/invoices/reporting/single'
    if Compliance:
        INVOICE_REPORTING_URL='https://gw-fatoora.zatca.gov.sa/e-invoicing/simulation/compliance/invoices' 
    invoicehash = invoice_hash.decode('utf-8').strip()
    
    invoice = base64.b64encode(xml).decode('utf-8').strip()
    
    # Prepare request
    auth = binarySecurityToken
    auth_str = f'{auth}:{secret}'
    auth2 = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
    headers = {
        'accept': 'application/json',
        'accept-language': 'en',
        'Clearance-Status': '0',
        'Accept-Version': 'V2',
        'Content-Type': 'application/json',
        'Authorization': f'Basic {auth2}',
    }
    
    json_data = {
        'invoiceHash': invoicehash,
        'uuid': id,
        'invoice': invoice,
    }
    # print(json_data) 
    # Send request
    try:
        response = requests.post(
            INVOICE_REPORTING_URL,
            headers=headers,
            json=json_data,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print(f'Error 401: Invalid credentials')
        else:
            print(f'Error {e.response.status_code}: {e.response.text}')
    except requests.exceptions.RequestException as e:
        print(f'Error: {e}')
    
