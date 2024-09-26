INVOICE_LINE_ITEM_TEMPLATE = '''    <cac:InvoiceLine>
        <cbc:ID>%(item_id)s</cbc:ID>
        <cbc:InvoicedQuantity unitCode="PCE">%(item_qty)s</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="SAR">%(qty_price)s</cbc:LineExtensionAmount>
        <cac:TaxTotal>
             <cbc:TaxAmount currencyID="SAR">%(vat)s</cbc:TaxAmount>
             <cbc:RoundingAmount currencyID="SAR">%(total_price)s</cbc:RoundingAmount>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Name>%(item_name)s</cbc:Name>
            <cac:ClassifiedTaxCategory>
                <cbc:ID>%(category_id)s</cbc:ID>
                <cbc:Percent>%(vat_percent)s</cbc:Percent>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:ClassifiedTaxCategory>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="SAR">%(item_net_price)s</cbc:PriceAmount>
            <cac:AllowanceCharge>
               <cbc:ChargeIndicator>true</cbc:ChargeIndicator>
               <cbc:AllowanceChargeReason>discount</cbc:AllowanceChargeReason>
               <cbc:Amount currencyID="SAR">%(discount)s</cbc:Amount>
               <cbc:BaseAmount currencyID="SAR">%(item_price)s</cbc:BaseAmount>
            </cac:AllowanceCharge>
        </cac:Price>
    </cac:InvoiceLine>'''
SIGNATURE_TEMPLATE = '''<xades:SignedProperties %(xades)sId="xadesSignedProperties">
                                    <xades:SignedSignatureProperties>
                                        <xades:SigningTime>%(time)sZ</xades:SigningTime>
                                        <xades:SigningCertificate>
                                            <xades:Cert>
                                                <xades:CertDigest>
                                                    <ds:DigestMethod%(digestMethod)s Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                                    <ds:DigestValue%(digestMethod)s>%(cert_hash)s</ds:DigestValue>
                                                </xades:CertDigest>
                                                <xades:IssuerSerial>
                                                    <ds:X509IssuerName%(digestMethod)s>%(issuer_name)s</ds:X509IssuerName>
                                                    <ds:X509SerialNumber%(digestMethod)s>%(cert_serial_no)s</ds:X509SerialNumber>
                                                </xades:IssuerSerial>
                                            </xades:Cert>
                                        </xades:SigningCertificate>
                                    </xades:SignedSignatureProperties>
                                </xades:SignedProperties>'''
SELLER_TEMPLATE = '''<cac:AccountingSupplierParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="CRN"></cbc:ID>
            </cac:PartyIdentification>
            <cac:PostalAddress>
                <cbc:StreetName>%(street_name)s</cbc:StreetName>
                <cbc:BuildingNumber>%(building_number)s</cbc:BuildingNumber>
                <cbc:PlotIdentification></cbc:PlotIdentification>
                <cbc:CitySubdivisionName>%(district)s</cbc:CitySubdivisionName>
                <cbc:CityName>%(city_name)s</cbc:CityName>
                <cbc:PostalZone>%(postal_code)s</cbc:PostalZone>
                <cac:Country>
                    <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                    <cbc:CompanyID>%(company_id)s</cbc:CompanyID>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>%(company_name)s</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingSupplierParty>'''
CUSTOMER_ID_TEMPLATE = '''<cac:PartyIdentification>
                <cbc:ID schemeID="NAT">%(id)s</cbc:ID>
            </cac:PartyIdentification>
            '''
CUSTOMER_INFO_TEMPLATE = '''<cac:AccountingCustomerParty>
        <cac:Party>
            %(customer_id)s<cac:PostalAddress>
                <cbc:StreetName>%(street_name)s</cbc:StreetName>
                <cbc:BuildingNumber>%(building_number)s</cbc:BuildingNumber>
                <cbc:PlotIdentification></cbc:PlotIdentification>
                <cbc:CitySubdivisionName>%(district)s</cbc:CitySubdivisionName>
                <cbc:CityName>%(city_name)s</cbc:CityName>
                <cbc:PostalZone>%(postal_code)s</cbc:PostalZone>
                <cac:Country>
                    <cbc:IdentificationCode>SA</cbc:IdentificationCode>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cac:TaxScheme>
                    <cbc:ID>VAT</cbc:ID>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:PartyLegalEntity>
                <cbc:RegistrationName>%(customer_name)s</cbc:RegistrationName>
            </cac:PartyLegalEntity>
        </cac:Party>
    </cac:AccountingCustomerParty>'''
INSTRUCTION_NOTES_TEMPLATE = '''<cbc:InstructionNote>%(notes)s</cbc:InstructionNote>'''
DELIVERY_TEMPLATE = '''<cac:Delivery>
        <cbc:ActualDeliveryDate>%(actual_date)s</cbc:ActualDeliveryDate>
    </cac:Delivery>'''
PAYMENT_TEMPLATE = '''<cac:PaymentMeans>
        <cbc:PaymentMeansCode>%(payment_type)s</cbc:PaymentMeansCode>
        %(notes)s
    </cac:PaymentMeans>'''
BILLING_REFRENCE_TEMPLATE = '''<cac:BillingReference>
      <cac:InvoiceDocumentReference>
         <cbc:ID>%(invoice_id)s</cbc:ID>
      </cac:InvoiceDocumentReference>
   </cac:BillingReference>'''
NO_TAX_TEMPLATE = '''<cbc:TaxExemptionReasonCode>%(no_tax_reason_code)s</cbc:TaxExemptionReasonCode>
                <cbc:TaxExemptionReason>%(no_tax_reason)s</cbc:TaxExemptionReason>
                '''
TAX_SUBTOTAL_TEMPLATE = '''        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="SAR">%(taxable_amount)s</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="SAR">%(tax_amount)s</cbc:TaxAmount>
             <cac:TaxCategory>
                <cbc:ID schemeAgencyID="6" schemeID="UN/ECE 5305">%(category_id)s</cbc:ID>
                <cbc:Percent>%(tax_percent)s</cbc:Percent>
                %(no_tax_reason)s<cac:TaxScheme>
                    <cbc:ID schemeAgencyID="6" schemeID="UN/ECE 5153">VAT</cbc:ID>
                </cac:TaxScheme>
             </cac:TaxCategory>
        </cac:TaxSubtotal>'''
PIH_TEMPLATE = '''<cac:AdditionalDocumentReference>
        <cbc:ID>PIH</cbc:ID>
        <cac:Attachment>
            <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">%(PIH)s</cbc:EmbeddedDocumentBinaryObject>
        </cac:Attachment>
    </cac:AdditionalDocumentReference>'''
UBL_TEMPLATE = '''<ext:UBLExtensions>
    <ext:UBLExtension>
        <ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:enveloped:xades</ext:ExtensionURI>
        <ext:ExtensionContent>
            <sig:UBLDocumentSignatures xmlns:sig="urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2" xmlns:sac="urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2" xmlns:sbc="urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2">
                <sac:SignatureInformation> 
                    <cbc:ID>urn:oasis:names:specification:ubl:signature:1</cbc:ID>
                    <sbc:ReferencedSignatureID>urn:oasis:names:specification:ubl:signature:Invoice</sbc:ReferencedSignatureID>
                    <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="signature">
                        <ds:SignedInfo>
                            <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2006/12/xml-c14n11"/>
                            <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"/>
                            <ds:Reference Id="invoiceSignedData" URI="">
                                <ds:Transforms>
                                    <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                        <ds:XPath>not(//ancestor-or-self::ext:UBLExtensions)</ds:XPath>
                                    </ds:Transform>
                                    <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                        <ds:XPath>not(//ancestor-or-self::cac:Signature)</ds:XPath>
                                    </ds:Transform>
                                    <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                        <ds:XPath>not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])</ds:XPath>
                                    </ds:Transform>
                                    <ds:Transform Algorithm="http://www.w3.org/2006/12/xml-c14n11"/>
                                </ds:Transforms>
                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                <ds:DigestValue>%(hash1)s</ds:DigestValue>
                            </ds:Reference>
                            <ds:Reference Type="http://www.w3.org/2000/09/xmldsig#SignatureProperties" URI="#xadesSignedProperties">
                                <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                <ds:DigestValue>%(hash2)s</ds:DigestValue>
                            </ds:Reference>
                        </ds:SignedInfo>
                        <ds:SignatureValue>%(signature)s</ds:SignatureValue>
                        <ds:KeyInfo>
                            <ds:X509Data>
                                <ds:X509Certificate>%(certificate)s</ds:X509Certificate>
                            </ds:X509Data>
                        </ds:KeyInfo>
                        <ds:Object>
                            <xades:QualifyingProperties xmlns:xades="http://uri.etsi.org/01903/v1.3.2#" Target="signature">
                                %(signature_properties)s
                            </xades:QualifyingProperties>
                        </ds:Object>
                    </ds:Signature>
                </sac:SignatureInformation>
            </sig:UBLDocumentSignatures>
        </ext:ExtensionContent>
    </ext:UBLExtension>
</ext:UBLExtensions>'''
QR_TEMPLATE = '''<cac:AdditionalDocumentReference>
        <cbc:ID>QR</cbc:ID>
        <cac:Attachment>
            <cbc:EmbeddedDocumentBinaryObject mimeCode="text/plain">%(qr)s</cbc:EmbeddedDocumentBinaryObject>
        </cac:Attachment>
    </cac:AdditionalDocumentReference>'''
MAIN_TEMPLATE = '''%(xml_version)s<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2">
%(ubl_extensions)s
    <cbc:ProfileID>reporting:1.0</cbc:ProfileID>
    <cbc:ID>%(invoice_id)s</cbc:ID>
    <cbc:UUID>%(uuid)s</cbc:UUID>
    <cbc:IssueDate>%(issue_date)s</cbc:IssueDate>
    <cbc:IssueTime>%(issue_time)s</cbc:IssueTime>
    %(invoice_type)s
    <cbc:Note languageID="ar"></cbc:Note>
    <cbc:DocumentCurrencyCode>SAR</cbc:DocumentCurrencyCode>
    <cbc:TaxCurrencyCode>SAR</cbc:TaxCurrencyCode>
    %(billing_reference)s
    <cac:AdditionalDocumentReference>
        <cbc:ID>ICV</cbc:ID>
        <cbc:UUID>%(invoice_counter)s</cbc:UUID>
    </cac:AdditionalDocumentReference>
    %(PIH)s
    %(qr)s
    %(signature)s
    %(seller_info)s
    %(customer_info)s
    %(delivary)s
    %(payment_mean)s
    <cac:AllowanceCharge>
        <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
        <cbc:AllowanceChargeReason>discount</cbc:AllowanceChargeReason>
        <cbc:Amount currencyID="SAR">%(doc_discount)s</cbc:Amount>
        <cac:TaxCategory>
            <cbc:ID schemeAgencyID="6" schemeID="UN/ECE 5305">S</cbc:ID>
            <cbc:Percent>15</cbc:Percent>
            <cac:TaxScheme>
                <cbc:ID schemeAgencyID="6" schemeID="UN/ECE 5153">VAT</cbc:ID>
            </cac:TaxScheme>
        </cac:TaxCategory>
    </cac:AllowanceCharge>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">%(total_tax)s</cbc:TaxAmount>
    </cac:TaxTotal>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="SAR">%(total_tax)s</cbc:TaxAmount>
%(tax_details)s
    </cac:TaxTotal>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="SAR">%(total_without_tax)s</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="SAR">%(total_without_tax_after_doc_discount)s</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="SAR">%(total_with_tax)s</cbc:TaxInclusiveAmount>
        <cbc:AllowanceTotalAmount currencyID="SAR">%(doc_discount)s</cbc:AllowanceTotalAmount>
        <cbc:PrepaidAmount currencyID="SAR">%(pre_pay)s</cbc:PrepaidAmount>
        <cbc:PayableAmount currencyID="SAR">%(payed)s</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
%(invoice_lines)s
</Invoice>'''