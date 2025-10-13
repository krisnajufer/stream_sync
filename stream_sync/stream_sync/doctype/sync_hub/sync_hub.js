// Copyright (c) 2025, Jufer and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sync Hub", {
    onload(frm){
        frm.get_field('sync_hub_document').grid.cannot_add_rows = true;
        // change the filter method by passing a custom method
        frm.set_query('ref_doctype', () => {
            return {
                query: 'stream_sync.stream_sync.doctype.sync_hub.sync_hub.get_doctype_sync',
            }
        })
    },
	refresh(frm) {
        frm.disable_save();
        frm.get_field('sync_hub_document').grid.cannot_add_rows = true;
	},
    get_data(frm){
        frm.doc.sync_hub_document = []
        frm.refresh_field('sync_hub_document');
        frm.call('get_data').then(r => {
            if (r.message) {
                let result = r.message;
                frm.doc.sync_hub_document = []
                if (result.length > 0) {
                    result.forEach(row => {
                        frm.add_child('sync_hub_document', row)
                    });
                    frm.refresh_field('sync_hub_document');
                    frm.add_custom_button('Sync', () => {
                        sync(frm);
                    });
                }else{
                    frappe.msgprint(`Data document ${frm.doc.ref_doctype} is up-to-date`)
                }
            }
        })
    }
});

function sync(frm) {
    const doc = frm.doc 
    frappe.call({
        method: 'stream_sync.stream_sync.doctype.sync_hub.sync_hub.sync',
        args: {
            data: JSON.stringify(doc)
        },
        // freeze the screen until the request is completed
        freeze: true,
        callback: (r) => {
        // on success
            if (r.message == "Success") {
                frappe.msgprint(`Sync ${doc.ref_doctype} Success`);
                frm.doc.sync_hub_document = [];
                frm.refresh_field('sync_hub_document');
            }
        },
        error: (r) => {
        // on error
            frappe.throw(`Sync ${doc.ref_doctype} Error`)
        }
    })
}
