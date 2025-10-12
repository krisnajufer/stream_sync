// Copyright (c) 2025, Jufer and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sync Hub", {
    onload(frm){
        frm.get_field('sync_hub_document').grid.cannot_add_rows = true;
    },
	refresh(frm) {
        frm.disable_save();
        frm.get_field('sync_hub_document').grid.cannot_add_rows = true;
        if (frm.doc.sync_hub_document.length > 1) {
            frm.add_custom_button('Sync', () => {
                frm.doc.status = 'Closed'
            });
        }
	},
    get_data(frm){
        frm.call('get_data')
        .then(r => {
            if (r.message) {
                let linked_doc = r.message;
                // do something with linked_doc
            }
        })
    }
});
