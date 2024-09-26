erpnext.setup_e_invoice_button = (doctype) => {
	frappe.ui.form.on(doctype, {
		refresh: (frm) => {
      console.log('frm.doc.docstatus', frm.doc.docstatus)
			// if(frm.doc.docstatus == 1) {
				frm.add_custom_button('send Invoice', () => {
					frm.call({
						method: "saudi_einvoice.saudi_einvoice.utils.prepare_send_attach_invoice",
						args: {
							docname: frm.doc.name
						},
						callback: function(r) {
							frm.reload_doc();
						}
					});
				});
			// }
		}
	});
};